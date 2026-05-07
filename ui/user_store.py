"""Persistance des scénarios par utilisateur.

Stockage :
- Si ``MONGODB_URI`` est défini -> collection MongoDB ``scenarios``
  (un document par utilisateur, ``_id = email_lower``).
- Sinon -> fichiers JSON locaux dans ``USER_DATA_DIR`` (ou
  ``ui/user_data/`` par défaut).  Utile en dev ; sur la plupart des
  PaaS le filesystem est éphémère, on recommande Mongo en prod.
"""
from __future__ import annotations
import datetime as _dt
import hashlib
import json
import os
import tempfile

import mongo_store

_DEFAULT_DIR = os.path.join(os.path.dirname(__file__), "user_data")


# --------------------------------------------------------------------- #
# Helpers communs
# --------------------------------------------------------------------- #
def _norm(email: str | None) -> str:
    return (email or "").strip().lower()


def _is_valid(scn: dict | None) -> bool:
    return bool(
        isinstance(scn, dict)
        and isinstance(scn.get("scenarios"), dict)
        and scn["scenarios"]
    )


def _build_payload(scn: dict) -> dict:
    return {
        "active": scn.get("active") or next(iter(scn["scenarios"])),
        "scenarios": {k: _sanitize_dict(dict(v)) for k, v in scn["scenarios"].items()},
    }


def _sanitize_dict(d: dict) -> dict:
    """Nettoie un dict pour être compatible BSON (pas de NaN/Inf,
    pas de clés avec '.' ou '$')."""
    import math
    out = {}
    for k, v in d.items():
        # MongoDB n'accepte pas les '.' dans les clés
        safe_key = str(k).replace(".", "_").replace("$", "_")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            v = 0.0
        elif isinstance(v, dict):
            v = _sanitize_dict(v)
        elif isinstance(v, list):
            v = _sanitize_list(v)
        out[safe_key] = v
    return out


def _sanitize_list(lst: list) -> list:
    import math
    out = []
    for v in lst:
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            out.append(0.0)
        elif isinstance(v, dict):
            out.append(_sanitize_dict(v))
        elif isinstance(v, list):
            out.append(_sanitize_list(v))
        else:
            out.append(v)
    return out


# --------------------------------------------------------------------- #
# Backend fichier JSON (fallback / dev)
# --------------------------------------------------------------------- #
def _data_dir() -> str:
    return os.environ.get("USER_DATA_DIR") or _DEFAULT_DIR


def _ensure_dir() -> None:
    os.makedirs(_data_dir(), exist_ok=True)


def _path_for(email: str) -> str:
    h = hashlib.sha256(_norm(email).encode("utf-8")).hexdigest()
    return os.path.join(_data_dir(), f"{h}.json")


def _load_from_file(email: str) -> dict | None:
    p = _path_for(email)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    return data if _is_valid(data) else None


def _save_to_file(email: str, payload: dict) -> None:
    _ensure_dir()
    p = _path_for(email)
    fd, tmp = tempfile.mkstemp(prefix=".scn_", dir=_data_dir())
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------- #
# Backend MongoDB
# --------------------------------------------------------------------- #
def _load_from_mongo(email: str) -> dict | None:
    col = mongo_store.scenarios_collection()
    if col is None:
        print(f"[user_store] Mongo NOT enabled — cannot load for {email}")
        return None
    try:
        doc = col.find_one({"_id": email})
    except Exception as exc:  # pragma: no cover
        print(f"[user_store] Mongo load error: {exc}")
        return None
    if not doc:
        print(f"[user_store] Mongo: aucun document trouvé pour {email}")
        return None
    data = {"active": doc.get("active"),
            "scenarios": doc.get("scenarios") or {}}
    if _is_valid(data):
        print(f"[user_store] Mongo load OK for {email} "
              f"(active={data['active']}, "
              f"scenarios={list(data['scenarios'].keys())})")
        return data
    print(f"[user_store] Mongo: document invalide pour {email}")
    return None


def _save_to_mongo(email: str, payload: dict) -> bool:
    col = mongo_store.scenarios_collection()
    if col is None:
        print(f"[user_store] Mongo NOT enabled — cannot save for {email}")
        return False
    try:
        now = _dt.datetime.utcnow()
        col.update_one(
            {"_id": email},
            {
                "$set": {
                    "email": email,
                    "active": payload["active"],
                    "scenarios": payload["scenarios"],
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
                "$inc": {"save_count": 1},
            },
            upsert=True,
        )
        print(f"[user_store] Mongo save OK for {email} "
              f"(active={payload['active']}, "
              f"scenarios={list(payload['scenarios'].keys())})")
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[user_store] Mongo save error: {exc}")
        return False


# --------------------------------------------------------------------- #
# Préférences utilisateur (langue, dernier onglet, etc.)
# --------------------------------------------------------------------- #
def load_preferences(email: str | None) -> dict:
    """Retourne les préférences UI (``{"lang": "fr", ...}``)."""
    email = _norm(email)
    if not email or not mongo_store.is_enabled():
        return {}
    col = mongo_store.get_db()
    if col is None:
        return {}
    try:
        doc = col["preferences"].find_one({"_id": email}) or {}
        doc.pop("_id", None)
        return doc
    except Exception as exc:  # pragma: no cover
        print(f"[user_store] prefs load error: {exc}")
        return {}


def save_preferences(email: str | None, prefs: dict) -> None:
    email = _norm(email)
    if not email or not isinstance(prefs, dict) or not prefs:
        return
    if not mongo_store.is_enabled():
        return
    db = mongo_store.get_db()
    if db is None:
        return
    try:
        db["preferences"].update_one(
            {"_id": email},
            {"$set": {**prefs, "updated_at": _dt.datetime.utcnow()}},
            upsert=True,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[user_store] prefs save error: {exc}")


# --------------------------------------------------------------------- #
# API publique
# --------------------------------------------------------------------- #
def load_scenarios(email: str | None) -> dict | None:
    """Retourne la structure ``{"active": ..., "scenarios": {...}}`` ou
    ``None`` si l'utilisateur n'a encore rien sauvegardé."""
    email = _norm(email)
    if not email:
        return None
    if mongo_store.is_enabled():
        return _load_from_mongo(email)
    return _load_from_file(email)


def save_scenarios(email: str | None, scn: dict | None) -> None:
    """Persiste la structure scénarios pour l'utilisateur."""
    email = _norm(email)
    if not email:
        print("[user_store] save_scenarios: pas d'email — ignoré.")
        return
    if not _is_valid(scn):
        print(f"[user_store] save_scenarios: données invalides pour {email} — ignoré.")
        return
    payload = _build_payload(scn)
    if mongo_store.is_enabled():
        if _save_to_mongo(email, payload):
            return
        # En cas d'erreur Mongo, repli sur fichier pour ne rien perdre.
    _save_to_file(email, payload)
