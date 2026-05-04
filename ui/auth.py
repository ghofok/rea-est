"""Authentification simple par email + mot de passe.

- La liste des comptes autorisés est dans ``ui/users.json``.
- Une page ``/login`` (servie par le Flask sous-jacent à Dash) affiche
  un formulaire ; à la validation, l'email est stocké en session.
- Toute requête non authentifiée est redirigée vers ``/login``
  (les requêtes AJAX Dash reçoivent un 401, ce qui force le rechargement).
- ``/logout`` purge la session.

Utilisation : ``auth.init_auth(app)`` après la création de l'app Dash.
"""
from __future__ import annotations
import json
import os
import secrets

from flask import (request, session, redirect, url_for, render_template_string,
                   jsonify)

import mongo_store


# --------------------------------------------------------------------- #
# Chargement des utilisateurs
# --------------------------------------------------------------------- #
_USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")


def _load_users_from_file() -> dict[str, str]:
    try:
        with open(_USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    out: dict[str, str] = {}
    for u in data.get("users", []):
        email = str(u.get("email", "")).strip().lower()
        pwd = str(u.get("password", ""))
        if email and pwd:
            out[email] = pwd
    return out


def _load_users() -> dict[str, str]:
    """Retourne ``{email_lower: password}``.

    Si MongoDB est configuré, lit la collection ``users`` (documents au
    format ``{"_id"|"email": "...", "password": "..."}``).  Sinon, lit
    ``users.json`` (rechargé à chaque appel pour qu'une modif soit prise
    en compte sans redémarrer).
    """
    if mongo_store.is_enabled():
        col = mongo_store.users_collection()
        if col is not None:
            try:
                out: dict[str, str] = {}
                for doc in col.find({}, {"_id": 1, "email": 1, "password": 1}):
                    email = str(doc.get("email") or doc.get("_id") or "") \
                        .strip().lower()
                    pwd = str(doc.get("password", ""))
                    if email and pwd:
                        out[email] = pwd
                return out
            except Exception as exc:  # pragma: no cover
                print(f"[auth] Mongo users load error: {exc}")
    return _load_users_from_file()


def _check_credentials(email: str, password: str) -> bool:
    email_n = (email or "").strip().lower()
    if not email_n or not password:
        return False
    # Si Mongo actif, on interroge directement le doc utilisateur
    # (évite de tout charger en mémoire et permet d'éventuels hash plus tard).
    if mongo_store.is_enabled():
        col = mongo_store.users_collection()
        if col is not None:
            try:
                doc = col.find_one({"$or": [{"_id": email_n},
                                            {"email": email_n}]})
                if doc and str(doc.get("password", "")) == password:
                    return True
                # Mongo accessible mais identifiants invalides -> refus
                # (pas de repli fichier pour éviter une double source de vérité).
                return False
            except Exception as exc:  # pragma: no cover
                print(f"[auth] Mongo auth error: {exc}")
                # En cas d'erreur de connexion, on tente le fichier local.
    return _load_users_from_file().get(email_n) == password


# --------------------------------------------------------------------- #
# Page /login (HTML autonome)
# --------------------------------------------------------------------- #
_LOGIN_HTML = """
<!doctype html>
<html lang="{{ lang }}">
<head>
<meta charset="utf-8">
<title>{{ T['login_title'] }}</title>
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
<style>
  body { background: linear-gradient(180deg, #eef3fb 0%, #f7f9fc 100%);
         min-height: 100vh; font-family: Inter, 'Segoe UI', Arial, sans-serif; }
  .login-card { max-width: 420px; margin: 8vh auto; border: none;
                border-radius: 16px;
                box-shadow: 0 6px 24px rgba(44,62,80,0.12); }
  .login-card .card-body { padding: 2rem; }
  .brand { color: #2c6ecb; font-weight: 600; }
  .lang-switch { position: absolute; top: 1rem; right: 1rem; }
  .lang-switch a { margin-left: .5rem; color: #6c757d; text-decoration: none;
                    font-size: .9rem; }
  .lang-switch a.active { color: #2c6ecb; font-weight: 600; }
</style>
</head>
<body>
  <div class="lang-switch">
    <a href="?lang=fr{% if next_url %}&next={{ next_url }}{% endif %}"
       class="{% if lang == 'fr' %}active{% endif %}">🇫🇷 FR</a>
    <a href="?lang=en{% if next_url %}&next={{ next_url }}{% endif %}"
       class="{% if lang == 'en' %}active{% endif %}">🇬🇧 EN</a>
  </div>
  <div class="card login-card">
    <div class="card-body">
      <h4 class="brand mb-1">
        <i class="bi bi-building me-2"></i>{{ T['app_title'] }}
      </h4>
      <p class="text-muted mb-4">{{ T['login_intro'] }}</p>
      {% if error %}
        <div class="alert alert-danger py-2">
          <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
        </div>
      {% endif %}
      <form method="post" action="{{ url_for('login') }}">
        <div class="mb-3">
          <label class="form-label">{{ T['email'] }}</label>
          <input type="email" name="email" class="form-control"
                 value="{{ email or '' }}" required autofocus>
        </div>
        <div class="mb-3">
          <label class="form-label">{{ T['password'] }}</label>
          <input type="password" name="password" class="form-control" required>
        </div>
        <input type="hidden" name="next" value="{{ next_url }}">
        <button type="submit" class="btn btn-primary w-100">
          <i class="bi bi-box-arrow-in-right me-2"></i>{{ T['sign_in'] }}
        </button>
      </form>
    </div>
  </div>
</body>
</html>
"""


# --------------------------------------------------------------------- #
# Init
# --------------------------------------------------------------------- #
# Endpoints / chemins toujours accessibles sans connexion.
_PUBLIC_PREFIXES = ("/login", "/logout", "/assets/", "/_favicon", "/favicon")


def init_auth(app) -> None:
    """Branche les routes d'authentification sur le serveur Flask de Dash."""
    server = app.server

    # Clé de session : variable d'env si dispo, sinon clé éphémère.
    server.secret_key = os.environ.get(
        "DASH_SECRET_KEY") or server.secret_key or secrets.token_hex(32)

    # ----- Routes ------------------------------------------------------
    @server.route("/login", methods=["GET", "POST"])
    def login():
        from i18n import TRANSLATIONS, SUPPORTED, DEFAULT_LANG

        # Langue : ?lang=… > cookie > défaut
        lang = (request.args.get("lang")
                or request.cookies.get("lang") or DEFAULT_LANG)
        if lang not in SUPPORTED:
            lang = DEFAULT_LANG
        T = {k: v.get(lang, v.get(DEFAULT_LANG, k))
             for k, v in TRANSLATIONS.items()}

        next_url = (request.values.get("next")
                    or request.args.get("next") or "/")

        def _render(error: str | None, email: str = ""):
            resp = server.make_response(render_template_string(
                _LOGIN_HTML, error=error, email=email,
                next_url=next_url, lang=lang, T=T))
            # Mémorise la langue dans un cookie, comme dans l'app.
            resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365,
                            samesite="Lax")
            return resp

        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            if _check_credentials(email, password):
                session.clear()
                session["user"] = email.lower()
                try:
                    mongo_store.log_activity(email, "login",
                                             ip=request.remote_addr)
                except Exception:
                    pass
                if not next_url.startswith("/"):
                    next_url = "/"
                return redirect(next_url)
            return _render(T["invalid_credentials"], email)
        return _render(None, "")

    @server.route("/_debug/mongo")
    def _debug_mongo():
        """Diagnostic en direct : à ouvrir sur l'URL Render pour vérifier
        connexion Mongo, users, scénarios sauvegardés.
        Sécurisé via la variable d'env DEBUG_TOKEN si définie."""
        token = os.environ.get("DEBUG_TOKEN", "")
        if token and request.args.get("token") != token:
            return jsonify(error="forbidden"), 403
        info = {
            "mongo_uri_set": bool(os.environ.get("MONGODB_URI")),
            "mongo_db_env": os.environ.get("MONGODB_DB"),
            "mongo_users_env": os.environ.get("MONGODB_USERS"),
            "mongo_scenarios_env": os.environ.get("MONGODB_SCENARIOS"),
            "is_enabled": False,
            "db_name": None,
            "users_count": None,
            "users_emails_preview": [],
            "scenarios_count": None,
            "scenarios_emails_preview": [],
            "current_session_user": session.get("user"),
            "current_user_scenarios": None,
            "error": None,
        }
        try:
            db = mongo_store.get_db()
            info["is_enabled"] = db is not None
            if db is not None:
                info["db_name"] = db.name
                col = mongo_store.users_collection()
                info["users_count"] = col.count_documents({})
                info["users_emails_preview"] = [
                    str(d.get("email") or d.get("_id"))
                    for d in col.find({}, {"_id": 1, "email": 1}).limit(20)
                ]
                scol = mongo_store.scenarios_collection()
                if scol is not None:
                    info["scenarios_count"] = scol.count_documents({})
                    info["scenarios_emails_preview"] = [
                        str(d.get("_id"))
                        for d in scol.find({}, {"_id": 1}).limit(20)
                    ]
                    cur = (session.get("user") or "").strip().lower()
                    if cur:
                        doc = scol.find_one({"_id": cur})
                        if doc:
                            info["current_user_scenarios"] = {
                                "active": doc.get("active"),
                                "names": list((doc.get("scenarios")
                                               or {}).keys()),
                                "save_count": doc.get("save_count"),
                                "updated_at": str(doc.get("updated_at")),
                            }
        except Exception as exc:
            info["error"] = repr(exc)
        return jsonify(info)

    @server.route("/logout")
    def logout():
        try:
            mongo_store.log_activity(session.get("user"), "logout")
        except Exception:
            pass
        session.clear()
        return redirect(url_for("login"))

    # ----- Garde globale ----------------------------------------------
    @server.before_request
    def _require_login():
        path = request.path or "/"
        if any(path == p or path.startswith(p) for p in _PUBLIC_PREFIXES):
            return None
        if session.get("user"):
            return None
        # Requêtes AJAX Dash : renvoyer 401 plutôt qu'une redirection HTML.
        if path.startswith("/_dash-") or request.is_json \
                or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(error="Authentication required"), 401
        return redirect(url_for("login", next=path))


