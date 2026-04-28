# Interface Dash — Analyse immobilière

Interface web qui **réutilise** les modules Python (`inputs.py`,
`down_payment.py`, `mortgage.py`, `cashflow.py`, `study_20y.py`) du
dossier parent. Aucune formule n'est redéfinie ici : toute modification
dans les modules de calcul se répercute automatiquement.

## Installation

```powershell
cd e:\rea_est\ui
pip install -r requirements.txt
```

## Lancement

```powershell
cd e:\rea_est\ui
python app.py
```

Puis ouvrir http://127.0.0.1:8050 dans un navigateur.

## Onglets

1. **Inputs** — tous les paramètres modifiables (prix, hypothèque,
   location, taux d'indexation, frais de vente, impôts, jalons d'étude).
2. **Mise de fond** — récapitulatif total + par personne.
3. **Cashflow an 1** — ventilation détaillée (revenus / charges /
   résultats) pour l'année 1.
4. **Cashflow an X** — même ventilation avec sélecteur d'année.
5. **Étude pluriannuelle** — tableau par jalon + graphique
   (cashflow cumulatif / gain global).
6. **Amortissement** — détail mensuel, résumé annuel, graphique
   du capital restant / remboursé cumulé.

