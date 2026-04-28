# Déploiement — Analyse immobilière (Dash)

Application Dash/Plotly déployable sur **Plotly Cloud / Dash Enterprise**,
**Render**, **Railway**, **Heroku**, ou tout hébergeur compatible WSGI.

## Architecture

```
rea_est/
├── wsgi.py             # ← point d'entrée WSGI (gunicorn wsgi:server)
├── Procfile            # web: gunicorn wsgi:server …
├── runtime.txt         # version Python
├── requirements.txt    # dépendances
├── inputs.py
├── down_payment.py
├── mortgage.py
├── cashflow.py
├── study_20y.py
├── sensitivity.py
└── ui/
    ├── app.py          # crée l'application Dash + expose `server`
    ├── theme.py        ├── state.py        ├── components.py
    ├── layout.py       └── tabs/…
```

## Lancement local

```powershell
pip install -r requirements.txt
python ui/app.py
# ou en mode WSGI :
gunicorn wsgi:server --bind 0.0.0.0:8050
```

Ouvrir http://127.0.0.1:8050.

## Déploiement Plotly Cloud / Dash Enterprise

1. **Initialiser un dépôt Git** à la racine du projet :
   ```powershell
   cd e:\rea_est
   git init
   git add .
   git commit -m "Initial commit"
   ```

2. **Créer une App** dans le portail Dash Enterprise (ou Plotly Cloud).

3. **Ajouter le remote Git** fourni par la plateforme et pousser :
   ```powershell
   git remote add plotly <URL fournie>
   git push plotly main
   ```

4. La plateforme détecte automatiquement :
   - `requirements.txt` → installe les dépendances
   - `runtime.txt` → utilise Python 3.11.9
   - `Procfile` → démarre `gunicorn wsgi:server`

L'app sera disponible à l'URL fournie par la plateforme.

## Déploiement Render / Railway

Même principe — pointer le service Web sur ce dépôt :
- **Build Command** : `pip install -r requirements.txt`
- **Start Command** : `gunicorn wsgi:server --bind 0.0.0.0:$PORT`

## Variables d'environnement utiles

| Variable      | Défaut | Rôle                                     |
|---------------|--------|------------------------------------------|
| `PORT`        | 8050   | Port d'écoute (injecté par l'hébergeur)  |
| `DASH_DEBUG`  | true   | Mettre à `false` en production           |

## Notes

- `wsgi.py` ajoute `ui/` au `sys.path` pour que les imports relatifs
  (`theme`, `state`, `components`, `tabs.*`) fonctionnent sans modification.
- `app.server` est l'instance Flask sous-jacente exposée comme `server`
  dans `wsgi.py` et `ui/app.py`.

