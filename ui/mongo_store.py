"""Connecteur MongoDB partagé.

Activé uniquement si la variable d'environnement ``MONGODB_URI`` est
définie (par ex. sur Render / Plotly Cloud).  Sinon ``get_db()``
retourne ``None`` et les modules appelants retombent sur le stockage
JSON local.

Variables d'environnement reconnues
-----------------------------------
- ``MONGODB_URI``      : chaîne de connexion (obligatoire pour activer)
- ``MONGODB_DB``       : nom de la base (défaut ``rea_est``)
- ``MONGODB_USERS``    : nom de la collection users    (défaut ``users``)
- ``MONGODB_SCENARIOS``: nom de la collection scenarios (défaut ``scenarios``)
"""
from __future__ import annotations
import os
import threading

_lock = threading.Lock()
_client = None
_db = None
_init_done = False


def _init() -> None:
    global _client, _db, _init_done
    if _init_done:
        return
    with _lock:
        if _init_done:
            return
        _init_done = True
        uri = os.environ.get("MONGODB_URI")
        if not uri:
            return
        try:
            from pymongo import MongoClient  # type: ignore
        except ImportError:
            print("[mongo_store] pymongo non installé — fallback JSON.")
            return
        try:
            _client = MongoClient(uri, serverSelectionTimeoutMS=5000,
                                  appname="rea_est_ui")
            # Force la résolution pour échouer vite si l'URI est mauvaise.
            _client.admin.command("ping")
            _db = _client[os.environ.get("MONGODB_DB", "rea_est")]
            print("[mongo_store] connecté à MongoDB.")
        except Exception as exc:  # pragma: no cover
            print(f"[mongo_store] connexion MongoDB échouée: {exc}")
            _client = None
            _db = None


def get_db():
    """Retourne l'objet ``Database`` pymongo, ou ``None`` si Mongo
    n'est pas configuré / accessible."""
    _init()
    return _db


def users_collection():
    db = get_db()
    if db is None:
        return None
    return db[os.environ.get("MONGODB_USERS", "users")]


def scenarios_collection():
    db = get_db()
    if db is None:
        return None
    return db[os.environ.get("MONGODB_SCENARIOS", "scenarios")]


def is_enabled() -> bool:
    return get_db() is not None

