import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui"))
from dotenv import load_dotenv
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
print("Chemin du fichier .env:", env_path)
print("Existence du fichier .env:", os.path.exists(env_path))

loaded = load_dotenv(env_path)

print("Fichier .env chargé:", loaded)
print("mongo_uri lu:", bool(os.getenv("MONGODB_URI")))
print("Valeur (début):", os.getenv("MONGODB_URI")[:10] if os.getenv("MONGODB_URI") else "None")

import mongo_store

if not mongo_store.is_enabled():
    print("Mongo non configuré"); sys.exit(1)

with open(os.path.join(os.path.dirname(__file__), "..", "ui", "users.json"),
          encoding="utf-8") as f:
    users = json.load(f).get("users", [])

col = mongo_store.users_collection()
col.create_index("email", unique=True)
n = 0
for u in users:
    email = str(u.get("email","")).strip().lower()
    pwd = str(u.get("password",""))
    is_admin = bool(u.get("is_admin"))
    if email and pwd:
        col.update_one({"_id": email},
                       {"$set": {"_id": email, "email": email, "password": pwd,
                                 "is_admin": is_admin}},
                       upsert=True)
        n += 1
print(f"{n} utilisateur(s) importé(s).")