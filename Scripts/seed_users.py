import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
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