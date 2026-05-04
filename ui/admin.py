"""Page d'administration des utilisateurs (web).

Accessible uniquement aux comptes admin :
- soit listés dans la variable d'env ``ADMIN_EMAILS`` (séparés par ``,``),
- soit possédant ``is_admin: true`` dans leur document Mongo.

Routes (toutes protégées par l'auth standard + check admin) :
    GET  /admin                -> liste des utilisateurs + formulaires
    POST /admin/add            -> ajout d'un utilisateur
    POST /admin/passwd         -> changement de mot de passe
    POST /admin/delete         -> suppression (option purge des scénarios)
    POST /admin/rename         -> renommage (migre les scénarios)
    POST /admin/toggle_admin   -> bascule du flag is_admin (Mongo seulement)

Réutilise les mêmes opérations que ``Scripts/manage_users.py`` afin
d'avoir une seule source de vérité.
"""
from __future__ import annotations
import datetime as _dt
import json
import os

from flask import (request, session, redirect, url_for,
                   render_template_string, flash, abort)

import mongo_store

_USERS_PATH = os.path.join(os.path.dirname(__file__), "users.json")


# --------------------------------------------------------------------- #
# Admin detection
# --------------------------------------------------------------------- #
def _admin_emails_env() -> set[str]:
    raw = os.environ.get("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_admin(email: str | None) -> bool:
    if not email:
        return False
    em = email.strip().lower()
    if em in _admin_emails_env():
        return True
    if mongo_store.is_enabled():
        col = mongo_store.users_collection()
        if col is not None:
            try:
                doc = col.find_one(
                    {"$or": [{"_id": em}, {"email": em}]},
                    {"is_admin": 1},
                )
                if doc and bool(doc.get("is_admin")):
                    return True
            except Exception:
                pass
    # Fallback : flag is_admin dans users.json
    try:
        with open(_USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for u in data.get("users", []):
            if str(u.get("email", "")).strip().lower() == em \
                    and bool(u.get("is_admin")):
                return True
    except Exception:
        pass
    return False


# --------------------------------------------------------------------- #
# Storage helpers (Mongo prioritaire, fallback users.json)
# --------------------------------------------------------------------- #
def _norm(email: str) -> str:
    return (email or "").strip().lower()


def _users_col():
    if not mongo_store.is_enabled():
        return None
    col = mongo_store.users_collection()
    if col is None:
        return None
    try:
        from pymongo import WriteConcern  # type: ignore
        col = col.with_options(write_concern=WriteConcern(w="majority"))
    except Exception:
        pass
    try:
        col.create_index("email", unique=True, sparse=True)
    except Exception:
        pass
    return col


def _scn_col():
    if not mongo_store.is_enabled():
        return None
    col = mongo_store.scenarios_collection()
    if col is None:
        return None
    try:
        from pymongo import WriteConcern  # type: ignore
        col = col.with_options(write_concern=WriteConcern(w="majority"))
    except Exception:
        pass
    return col


def _list_users() -> list[dict]:
    """Liste normalisée : ``[{email, updated_at, is_admin, source}]``."""
    out: list[dict] = []
    col = _users_col()
    if col is not None:
        try:
            for d in col.find({}, {"_id": 1, "email": 1, "updated_at": 1,
                                   "created_at": 1, "is_admin": 1}):
                em = str(d.get("email") or d.get("_id") or "").lower()
                if not em:
                    continue
                out.append({
                    "email": em,
                    "updated_at": d.get("updated_at") or d.get("created_at"),
                    "is_admin": bool(d.get("is_admin"))
                                or em in _admin_emails_env(),
                    "source": "mongo",
                })
            return sorted(out, key=lambda x: x["email"])
        except Exception as exc:
            print(f"[admin] mongo list error: {exc}")
    # fallback fichier
    try:
        with open(_USERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        admins = _admin_emails_env()
        for u in data.get("users", []):
            em = _norm(u.get("email", ""))
            if em:
                out.append({"email": em, "updated_at": None,
                            "is_admin": em in admins, "source": "file"})
    except Exception:
        pass
    return sorted(out, key=lambda x: x["email"])


def _file_load() -> dict:
    try:
        with open(_USERS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": []}


def _file_save(data: dict) -> None:
    with open(_USERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _file_find(email: str) -> dict | None:
    data = _file_load()
    for u in data.get("users", []):
        if _norm(u.get("email", "")) == email:
            return u
    return None


# --------------------------------------------------------------------- #
# Operations
# --------------------------------------------------------------------- #
def _audit(action: str, **extra) -> None:
    try:
        mongo_store.log_activity(session.get("user"),
                                 f"admin_ui:{action}", **extra)
    except Exception:
        pass


def _op_add(email: str, password: str) -> tuple[bool, str]:
    email = _norm(email)
    if not email or not password:
        return False, "Email et mot de passe requis."
    col = _users_col()
    now = _dt.datetime.utcnow()
    if col is not None:
        if col.find_one({"$or": [{"_id": email}, {"email": email}]}):
            return False, f"'{email}' existe déjà."
        col.update_one(
            {"_id": email},
            {"$set": {"_id": email, "email": email, "password": password,
                      "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        _audit("add_user", target=email)
        return True, f"Utilisateur '{email}' ajouté."
    # fichier
    data = _file_load()
    if any(_norm(u.get("email")) == email for u in data.get("users", [])):
        return False, f"'{email}' existe déjà."
    data.setdefault("users", []).append({"email": email, "password": password})
    _file_save(data)
    return True, f"Utilisateur '{email}' ajouté (users.json)."


def _op_passwd(email: str, password: str) -> tuple[bool, str]:
    email = _norm(email)
    if not email or not password:
        return False, "Email et mot de passe requis."
    col = _users_col()
    if col is not None:
        doc = col.find_one({"$or": [{"_id": email}, {"email": email}]})
        if not doc:
            return False, f"'{email}' introuvable."
        col.update_one(
            {"_id": doc["_id"]},
            {"$set": {"password": password,
                      "updated_at": _dt.datetime.utcnow()}},
        )
        _audit("change_password", target=email)
        return True, f"Mot de passe mis à jour pour '{email}'."
    # fichier
    data = _file_load()
    found = False
    for u in data.get("users", []):
        if _norm(u.get("email")) == email:
            u["password"] = password
            found = True
            break
    if not found:
        return False, f"'{email}' introuvable."
    _file_save(data)
    return True, f"Mot de passe mis à jour pour '{email}' (users.json)."


def _op_delete(email: str, purge_scenarios: bool) -> tuple[bool, str]:
    email = _norm(email)
    if not email:
        return False, "Email requis."
    if email == _norm(session.get("user") or ""):
        return False, "Impossible de supprimer votre propre compte."
    col = _users_col()
    if col is not None:
        res = col.delete_one({"$or": [{"_id": email}, {"email": email}]})
        if res.deleted_count == 0:
            return False, f"'{email}' introuvable."
        msg = f"Utilisateur '{email}' supprimé."
        if purge_scenarios:
            scol = _scn_col()
            if scol is not None:
                r = scol.delete_one({"_id": email})
                msg += f" Scénarios supprimés: {r.deleted_count}."
        _audit("delete_user", target=email, purge=purge_scenarios)
        return True, msg
    # fichier
    data = _file_load()
    before = len(data.get("users", []))
    data["users"] = [u for u in data.get("users", [])
                     if _norm(u.get("email")) != email]
    if len(data["users"]) == before:
        return False, f"'{email}' introuvable."
    _file_save(data)
    return True, f"Utilisateur '{email}' supprimé (users.json)."


def _op_rename(old_email: str, new_email: str) -> tuple[bool, str]:
    old, new = _norm(old_email), _norm(new_email)
    if not old or not new:
        return False, "Email source et cible requis."
    if old == new:
        return False, "Emails identiques."
    col = _users_col()
    if col is not None:
        src = col.find_one({"$or": [{"_id": old}, {"email": old}]})
        if not src:
            return False, f"'{old}' introuvable."
        if col.find_one({"$or": [{"_id": new}, {"email": new}]}):
            return False, f"'{new}' existe déjà."
        now = _dt.datetime.utcnow()
        new_doc = {**src, "_id": new, "email": new, "updated_at": now}
        col.insert_one(new_doc)
        scol = _scn_col()
        migrated = 0
        if scol is not None:
            scn = scol.find_one({"_id": old})
            if scn:
                new_scn = {**scn, "_id": new, "email": new,
                           "updated_at": now}
                scol.insert_one(new_scn)
                scol.delete_one({"_id": old})
                migrated = 1
        col.delete_one({"_id": src["_id"]})
        _audit("rename_user", old=old, new=new, scenarios_migrated=migrated)
        return True, (f"'{old}' → '{new}' "
                      f"(scénarios migrés: {migrated}).")
    # fichier
    data = _file_load()
    src = _file_find(old)
    if not src:
        return False, f"'{old}' introuvable."
    if _file_find(new):
        return False, f"'{new}' existe déjà."
    src["email"] = new
    _file_save(data)
    return True, f"'{old}' → '{new}' (users.json)."


def _op_toggle_admin(email: str, make_admin: bool) -> tuple[bool, str]:
    email = _norm(email)
    if not email:
        return False, "Email requis."
    col = _users_col()
    if col is None:
        return False, ("Bascule admin disponible uniquement avec MongoDB "
                       "(sinon utiliser ADMIN_EMAILS).")
    doc = col.find_one({"$or": [{"_id": email}, {"email": email}]})
    if not doc:
        return False, f"'{email}' introuvable."
    col.update_one({"_id": doc["_id"]},
                   {"$set": {"is_admin": bool(make_admin),
                             "updated_at": _dt.datetime.utcnow()}})
    _audit("toggle_admin", target=email, is_admin=bool(make_admin))
    return True, (f"'{email}' est désormais "
                  f"{'admin' if make_admin else 'utilisateur standard'}.")


# --------------------------------------------------------------------- #
# Template
# --------------------------------------------------------------------- #
_ADMIN_HTML = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Administration — Utilisateurs</title>
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
<style>
  body { background:#f7f9fc; font-family:Inter,'Segoe UI',Arial,sans-serif; }
  .navbar-admin { background:linear-gradient(90deg,#2c6ecb,#1f4e8c); }
  .navbar-admin .navbar-brand,.navbar-admin a { color:#fff !important; }
  .card { border:none; border-radius:14px;
          box-shadow:0 4px 14px rgba(44,62,80,.08); }
  .card-header { background:#fff; border-bottom:1px solid #eef0f4;
                 font-weight:600; }
  table.users td,table.users th { vertical-align:middle; }
  .badge-admin { background:#ffc107; color:#000; }
  .badge-source { font-size:.7rem; }
  form.inline { display:inline; }
</style>
</head>
<body>
<nav class="navbar navbar-dark navbar-admin shadow-sm">
  <div class="container-fluid">
    <span class="navbar-brand">
      <i class="bi bi-shield-lock me-2"></i>Administration
    </span>
    <div>
      <a href="/" class="me-3">
        <i class="bi bi-arrow-left"></i> Retour à l'application
      </a>
      <a href="/logout">
        <i class="bi bi-box-arrow-right"></i> Déconnexion
      </a>
    </div>
  </div>
</nav>

<div class="container py-4">
  <p class="text-muted">
    Connecté : <strong>{{ current_user }}</strong>
    {% if mongo_enabled %}
      <span class="badge bg-success ms-2">MongoDB actif</span>
    {% else %}
      <span class="badge bg-secondary ms-2">users.json (local)</span>
    {% endif %}
  </p>

  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% for cat, msg in msgs %}
      <div class="alert alert-{{ 'danger' if cat=='error' else 'success' }}
                  alert-dismissible fade show py-2">
        {{ msg }}
        <button class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    {% endfor %}
  {% endwith %}

  <div class="card mb-4">
    <div class="card-header">
      <i class="bi bi-people me-2"></i>Utilisateurs ({{ users|length }})
    </div>
    <div class="card-body p-0">
      <table class="table table-hover users mb-0">
        <thead class="table-light">
          <tr><th>Email</th><th>Mis à jour</th><th>Source</th>
              <th>Rôle</th><th class="text-end">Actions</th></tr>
        </thead>
        <tbody>
        {% for u in users %}
          <tr>
            <td><i class="bi bi-person-circle me-2"></i>{{ u.email }}</td>
            <td class="text-muted">
              {{ u.updated_at.strftime('%Y-%m-%d %H:%M') if u.updated_at else '—' }}
            </td>
            <td><span class="badge bg-light text-dark badge-source">
              {{ u.source }}</span></td>
            <td>
              {% if u.is_admin %}
                <span class="badge badge-admin">
                  <i class="bi bi-shield-check"></i> admin</span>
              {% else %}
                <span class="text-muted">user</span>
              {% endif %}
            </td>
            <td class="text-end">
              <button class="btn btn-sm btn-outline-primary"
                      data-bs-toggle="modal"
                      data-bs-target="#pwdModal"
                      data-email="{{ u.email }}">
                <i class="bi bi-key"></i> Mot de passe
              </button>
              <button class="btn btn-sm btn-outline-secondary"
                      data-bs-toggle="modal"
                      data-bs-target="#renameModal"
                      data-email="{{ u.email }}">
                <i class="bi bi-pencil"></i> Renommer
              </button>
              {% if mongo_enabled %}
                <form class="inline" method="post" action="{{ url_for('admin_toggle_admin') }}">
                  <input type="hidden" name="email" value="{{ u.email }}">
                  <input type="hidden" name="make_admin"
                         value="{{ '0' if u.is_admin else '1' }}">
                  <button class="btn btn-sm btn-outline-warning"
                          {% if u.email == current_user and u.is_admin %}disabled
                          title="Vous ne pouvez pas vous retirer le rôle admin"{% endif %}>
                    <i class="bi bi-shield"></i>
                    {{ 'Retirer admin' if u.is_admin else 'Promouvoir admin' }}
                  </button>
                </form>
              {% endif %}
              {% if u.email != current_user %}
                <form class="inline" method="post" action="{{ url_for('admin_delete') }}"
                      onsubmit="return confirm('Supprimer {{ u.email }} ?');">
                  <input type="hidden" name="email" value="{{ u.email }}">
                  <label class="form-check-label small text-muted ms-2">
                    <input type="checkbox" name="purge" value="1"
                           class="form-check-input"> purger scénarios
                  </label>
                  <button class="btn btn-sm btn-outline-danger ms-1">
                    <i class="bi bi-trash"></i>
                  </button>
                </form>
              {% endif %}
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <i class="bi bi-person-plus me-2"></i>Ajouter un utilisateur
    </div>
    <div class="card-body">
      <form method="post" action="{{ url_for('admin_add') }}" class="row g-2">
        <div class="col-md-5">
          <input type="email" name="email" class="form-control"
                 placeholder="email@exemple.com" required>
        </div>
        <div class="col-md-5">
          <input type="text" name="password" class="form-control"
                 placeholder="Mot de passe" required>
        </div>
        <div class="col-md-2 d-grid">
          <button class="btn btn-primary">
            <i class="bi bi-plus-lg"></i> Ajouter
          </button>
        </div>
      </form>
    </div>
  </div>
</div>

<!-- Modal mot de passe -->
<div class="modal fade" id="pwdModal" tabindex="-1">
  <div class="modal-dialog">
    <form class="modal-content" method="post"
          action="{{ url_for('admin_passwd') }}">
      <div class="modal-header">
        <h5 class="modal-title">Changer le mot de passe</h5>
        <button class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <label class="form-label">Email</label>
        <input type="email" name="email" id="pwdEmail"
               class="form-control mb-3" readonly>
        <label class="form-label">Nouveau mot de passe</label>
        <input type="text" name="password" class="form-control" required>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal"
                type="button">Annuler</button>
        <button class="btn btn-primary">Mettre à jour</button>
      </div>
    </form>
  </div>
</div>

<!-- Modal rename -->
<div class="modal fade" id="renameModal" tabindex="-1">
  <div class="modal-dialog">
    <form class="modal-content" method="post"
          action="{{ url_for('admin_rename') }}">
      <div class="modal-header">
        <h5 class="modal-title">Renommer un utilisateur</h5>
        <button class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <p class="text-muted small">
          Les scénarios sont migrés sous le nouvel email.
        </p>
        <label class="form-label">Email actuel</label>
        <input type="email" name="old_email" id="rnEmail"
               class="form-control mb-3" readonly>
        <label class="form-label">Nouvel email</label>
        <input type="email" name="new_email" class="form-control" required>
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary" data-bs-dismiss="modal"
                type="button">Annuler</button>
        <button class="btn btn-primary">Renommer</button>
      </div>
    </form>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
  document.getElementById('pwdModal').addEventListener('show.bs.modal', e => {
    document.getElementById('pwdEmail').value =
      e.relatedTarget.getAttribute('data-email');
  });
  document.getElementById('renameModal').addEventListener('show.bs.modal', e => {
    document.getElementById('rnEmail').value =
      e.relatedTarget.getAttribute('data-email');
  });
</script>
</body>
</html>
"""


# --------------------------------------------------------------------- #
# Init
# --------------------------------------------------------------------- #
def init_admin(app) -> None:
    server = app.server

    def _require_admin():
        cur = session.get("user")
        if not cur:
            return redirect(url_for("login", next=request.path))
        if not is_admin(cur):
            abort(403)
        return None

    @server.route("/admin", methods=["GET"])
    def admin_home():
        guard = _require_admin()
        if guard is not None:
            return guard
        return render_template_string(
            _ADMIN_HTML,
            users=_list_users(),
            current_user=session.get("user"),
            mongo_enabled=mongo_store.is_enabled(),
        )

    @server.route("/admin/add", methods=["POST"])
    def admin_add():
        guard = _require_admin()
        if guard is not None:
            return guard
        ok, msg = _op_add(request.form.get("email", ""),
                          request.form.get("password", ""))
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_home"))

    @server.route("/admin/passwd", methods=["POST"])
    def admin_passwd():
        guard = _require_admin()
        if guard is not None:
            return guard
        ok, msg = _op_passwd(request.form.get("email", ""),
                             request.form.get("password", ""))
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_home"))

    @server.route("/admin/delete", methods=["POST"])
    def admin_delete():
        guard = _require_admin()
        if guard is not None:
            return guard
        purge = request.form.get("purge") == "1"
        ok, msg = _op_delete(request.form.get("email", ""), purge)
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_home"))

    @server.route("/admin/rename", methods=["POST"])
    def admin_rename():
        guard = _require_admin()
        if guard is not None:
            return guard
        ok, msg = _op_rename(request.form.get("old_email", ""),
                             request.form.get("new_email", ""))
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_home"))

    @server.route("/admin/toggle_admin", methods=["POST"])
    def admin_toggle_admin():
        guard = _require_admin()
        if guard is not None:
            return guard
        email = _norm(request.form.get("email", ""))
        make = request.form.get("make_admin") == "1"
        # Empêche de se retirer soi-même le rôle si dernier admin.
        if (not make) and email == _norm(session.get("user") or ""):
            flash("Impossible de vous retirer vous-même le rôle admin.",
                  "error")
            return redirect(url_for("admin_home"))
        ok, msg = _op_toggle_admin(email, make)
        flash(msg, "success" if ok else "error")
        return redirect(url_for("admin_home"))

