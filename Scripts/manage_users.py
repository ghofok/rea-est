"""Routine d'administration des utilisateurs (MongoDB).

Permet d'ajouter, supprimer, modifier le mot de passe ou lister les
comptes autorisés.  Utilise la collection définie par ``mongo_store``
(par défaut ``users``).

Lancement
---------
    python Scripts/manage_users.py                 # menu interactif
    python Scripts/manage_users.py list
    python Scripts/manage_users.py add    <email> [password]
    python Scripts/manage_users.py passwd <email> [password]
    python Scripts/manage_users.py delete <email>

Si le mot de passe n'est pas fourni en argument, il est demandé en
saisie masquée.

Le ``.env`` à la racine du projet doit définir ``MONGODB_URI`` (et
optionnellement ``MONGODB_DB``, ``MONGODB_USERS``).
"""
from __future__ import annotations
import getpass
import os
import sys

# --- Path setup --------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "ui"))

# --- .env --------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

import mongo_store  # noqa: E402


# ---------------------------------------------------------------------- #
# Helpers
# ---------------------------------------------------------------------- #
def _norm(email: str) -> str:
    return (email or "").strip().lower()


def _col():
    if not mongo_store.is_enabled():
        print("❌ MongoDB non configuré (MONGODB_URI absent).")
        sys.exit(1)
    col = mongo_store.users_collection()
    if col is None:
        print("❌ Collection users indisponible.")
        sys.exit(1)
    # Écriture confirmée par la majorité des nœuds (durabilité maximale).
    try:
        from pymongo import WriteConcern  # type: ignore
        col = col.with_options(write_concern=WriteConcern(w="majority"))
    except Exception:
        pass
    # Index unique sur l'email (idempotent).
    try:
        col.create_index("email", unique=True, sparse=True)
    except Exception:
        pass
    return col


def _scn_col():
    """Collection scénarios avec writeConcern majority."""
    col = mongo_store.scenarios_collection()
    if col is None:
        return None
    try:
        from pymongo import WriteConcern  # type: ignore
        col = col.with_options(write_concern=WriteConcern(w="majority"))
    except Exception:
        pass
    return col


def _audit(action: str, email: str, **extra) -> None:
    try:
        mongo_store.log_activity(email, f"admin:{action}",
                                 source="manage_users.py", **extra)
    except Exception:
        pass


def _check_ack(res, kind: str = "write") -> None:
    """Vérifie que l'écriture a été reconnue par le serveur."""
    ack = getattr(res, "acknowledged", True)
    if not ack:
        print(f"⚠️ {kind} non confirmé par MongoDB (writeConcern).")
        sys.exit(1)


def _ask_password(prompt: str = "Mot de passe : ") -> str:
    pwd = getpass.getpass(prompt)
    if not pwd:
        print("❌ Mot de passe vide.")
        sys.exit(1)
    pwd2 = getpass.getpass("Confirme le mot de passe : ")
    if pwd != pwd2:
        print("❌ Les mots de passe ne correspondent pas.")
        sys.exit(1)
    return pwd


# ---------------------------------------------------------------------- #
# Commandes
# ---------------------------------------------------------------------- #
def cmd_list() -> None:
    col = _col()
    docs = list(col.find({}, {"_id": 1, "email": 1, "created_at": 1,
                              "updated_at": 1}))
    if not docs:
        print("(aucun utilisateur)")
        return
    print(f"{len(docs)} utilisateur(s) :")
    for d in docs:
        email = d.get("email") or d.get("_id")
        upd = d.get("updated_at") or d.get("created_at") or ""
        print(f"  - {email}    {upd}")


def cmd_add(email: str, password: str | None = None) -> None:
    email = _norm(email)
    if not email:
        print("❌ Email manquant.")
        sys.exit(1)
    col = _col()
    if col.find_one({"$or": [{"_id": email}, {"email": email}]}):
        print(f"❌ '{email}' existe déjà. Utilise 'passwd' pour changer le "
              f"mot de passe.")
        sys.exit(1)
    if not password:
        password = _ask_password()
    import datetime as _dt
    now = _dt.datetime.utcnow()
    res = col.update_one(
        {"_id": email},
        {"$set": {"_id": email, "email": email, "password": password,
                  "updated_at": now},
         "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    _check_ack(res, "insert user")
    _audit("add_user", email)
    print(f"✅ Utilisateur '{email}' ajouté (acknowledged=True).")


def cmd_passwd(email: str, password: str | None = None) -> None:
    email = _norm(email)
    if not email:
        print("❌ Email manquant.")
        sys.exit(1)
    col = _col()
    doc = col.find_one({"$or": [{"_id": email}, {"email": email}]})
    if not doc:
        print(f"❌ Utilisateur '{email}' introuvable.")
        sys.exit(1)
    if not password:
        password = _ask_password("Nouveau mot de passe : ")
    import datetime as _dt
    res = col.update_one(
        {"_id": doc["_id"]},
        {"$set": {"password": password,
                  "updated_at": _dt.datetime.utcnow()}},
    )
    _check_ack(res, "update password")
    if res.modified_count == 0:
        print("⚠️ Aucun document modifié (mdp identique ?).")
    _audit("change_password", email)
    print(f"✅ Mot de passe mis à jour pour '{email}'. "
          f"(Les scénarios de l'utilisateur sont conservés.)")


def cmd_delete(email: str, drop_scenarios: bool = False) -> None:
    email = _norm(email)
    if not email:
        print("❌ Email manquant.")
        sys.exit(1)
    col = _col()
    res = col.delete_one({"$or": [{"_id": email}, {"email": email}]})
    _check_ack(res, "delete user")
    if res.deleted_count == 0:
        print(f"❌ Utilisateur '{email}' introuvable.")
        sys.exit(1)
    _audit("delete_user", email, purge=drop_scenarios)
    print(f"✅ Utilisateur '{email}' supprimé.")
    if drop_scenarios:
        scol = _scn_col()
        if scol is not None:
            r = scol.delete_one({"_id": email})
            _check_ack(r, "delete scenarios")
            print(f"   Scénarios supprimés : {r.deleted_count}")
    else:
        print("   (Scénarios conservés ; relance avec --purge pour les "
              "supprimer aussi.)")


def cmd_rename(old_email: str, new_email: str) -> None:
    """Renomme un utilisateur ET migre ses scénarios sous le nouvel email."""
    old = _norm(old_email)
    new = _norm(new_email)
    if not old or not new:
        print("❌ Email source ou cible manquant.")
        sys.exit(1)
    if old == new:
        print("❌ Email identique.")
        sys.exit(1)
    col = _col()
    src = col.find_one({"$or": [{"_id": old}, {"email": old}]})
    if not src:
        print(f"❌ '{old}' introuvable.")
        sys.exit(1)
    if col.find_one({"$or": [{"_id": new}, {"email": new}]}):
        print(f"❌ '{new}' existe déjà.")
        sys.exit(1)

    import datetime as _dt
    now = _dt.datetime.utcnow()
    new_doc = {**src, "_id": new, "email": new, "updated_at": now}

    # 1) crée le nouveau user
    r1 = col.insert_one(new_doc)
    _check_ack(r1, "insert renamed user")
    # 2) migre le doc scénarios
    scol = _scn_col()
    migrated = 0
    if scol is not None:
        scn = scol.find_one({"_id": old})
        if scn:
            new_scn = {**scn, "_id": new, "email": new, "updated_at": now}
            r2 = scol.insert_one(new_scn)
            _check_ack(r2, "insert renamed scenarios")
            r3 = scol.delete_one({"_id": old})
            _check_ack(r3, "delete old scenarios")
            migrated = 1
    # 3) supprime l'ancien user
    r4 = col.delete_one({"_id": src["_id"]})
    _check_ack(r4, "delete old user")

    _audit("rename_user", new, old=old, scenarios_migrated=migrated)
    print(f"✅ '{old}' → '{new}' (scénarios migrés: {migrated}).")


# ---------------------------------------------------------------------- #
# Mode interactif
# ---------------------------------------------------------------------- #
_MENU = """
=== Gestion des utilisateurs ===
  1) Lister
  2) Ajouter
  3) Changer le mot de passe
  4) Supprimer
  5) Supprimer + purger ses scénarios
  6) Renommer (migre les scénarios)
  0) Quitter
Choix : """


def interactive() -> None:
    while True:
        try:
            choice = input(_MENU).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if choice == "0" or choice.lower() in ("q", "quit", "exit"):
            return
        try:
            if choice == "1":
                cmd_list()
            elif choice == "2":
                email = input("Email : ").strip()
                cmd_add(email)
            elif choice == "3":
                email = input("Email : ").strip()
                cmd_passwd(email)
            elif choice == "4":
                email = input("Email : ").strip()
                cmd_delete(email, drop_scenarios=False)
            elif choice == "5":
                email = input("Email : ").strip()
                confirm = input(
                    f"Confirmer la suppression de '{email}' ET de "
                    f"ses scénarios ? (oui/non) : ").strip().lower()
                if confirm in ("oui", "o", "yes", "y"):
                    cmd_delete(email, drop_scenarios=True)
                else:
                    print("Annulé.")
            elif choice == "6":
                old = input("Ancien email : ").strip()
                new = input("Nouvel email : ").strip()
                cmd_rename(old, new)
            else:
                print("Choix invalide.")
        except SystemExit:
            # Les cmd_* font sys.exit en cas d'erreur ; on reste dans
            # le menu interactif.
            continue


# ---------------------------------------------------------------------- #
# CLI
# ---------------------------------------------------------------------- #
def main(argv: list[str]) -> None:
    if not argv:
        interactive()
        return
    cmd, *rest = argv
    cmd = cmd.lower()
    if cmd in ("list", "ls"):
        cmd_list()
    elif cmd == "add":
        if not rest:
            print("Usage: add <email> [password]"); sys.exit(2)
        cmd_add(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd in ("passwd", "password", "chpasswd"):
        if not rest:
            print("Usage: passwd <email> [password]"); sys.exit(2)
        cmd_passwd(rest[0], rest[1] if len(rest) > 1 else None)
    elif cmd in ("delete", "del", "rm"):
        if not rest:
            print("Usage: delete <email> [--purge]"); sys.exit(2)
        purge = "--purge" in rest
        cmd_delete(rest[0], drop_scenarios=purge)
    elif cmd in ("rename", "mv"):
        if len(rest) < 2:
            print("Usage: rename <old_email> <new_email>"); sys.exit(2)
        cmd_rename(rest[0], rest[1])
    elif cmd in ("-h", "--help", "help"):
        print(__doc__)
    else:
        print(f"Commande inconnue: {cmd}")
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv[1:])

