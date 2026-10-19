# MIZAN AI 🧮

Copilote financier pour les **épiceries** et les **coopératives** marocaines.

L'utilisateur raconte ce qui s'est passé en quelques mots (« vendu 5000 hier
dont 800 à crédit, caisse comptée 4100 ») ou l'enregistre à la voix. L'IA range
l'information, pose une question si besoin, et le moteur de calcul produit tous
les chiffres : chiffre d'affaires, caisse, créances, dettes, résultat.

> Rien n'est saisi à la main. Tout est recalculé à partir du journal d'événements.

## Les 4 écrans

1. **Mon profil** — créer / choisir une épicerie ou une coopérative. L'interface
   s'adapte automatiquement au type choisi.
2. **Je dis ce qui s'est passé** — saisie en un message court (écrit ou **vocal**),
   confirmation par l'IA, historique complet avec filtres, suppression d'une
   entrée à tout moment et réécoute des notes audio.
3. **Mes chiffres** — tableau de bord : cartes de chiffres, alertes colorées
   (vert / orange / rouge), graphiques (ventes par jour, caisse calculée vs
   comptée, dépenses par catégorie), créances et dettes par tiers.
4. **Questions du jour** — 1 à 2 questions maximum, réponse en un geste
   (Oui / Non / un montant).

## Règles métier

- Épicerie : clôture du jour, achat, dépense, crédit client, remboursement,
  retrait du patron.
- Coopérative : apport adhérent, paiement adhérent, transformation, vente,
  dépense, subvention, cotisation. **Subventions et cotisations ne comptent
  jamais dans le chiffre d'affaires.**
- Rien n'est bloqué : une information incomplète est enregistrée avec le statut
  « à confirmer » et reste comptée, mais signalée.

## Technique

- **Streamlit** (interface) + **SQLite** (base locale `mizan.db`).
- Aucune API externe : la compréhension des messages et les questions du jour
  sont simulées par des règles fixes (`mizan/parse.py`, `mizan/questions.py`).
- Tous les calculs sont dans `mizan/engine.py`.

```
app.py                 interface (4 écrans)
mizan/db.py            accès SQLite (profils, événements, questions, audios)
mizan/engine.py        types d'événements et calculs
mizan/parse.py         IA simulée : message -> événement
mizan/questions.py     règles des questions du jour
mizan/seed.py          données de démonstration
```

## Lancer en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Déployer sur Streamlit Cloud

1. Pousser ce dossier sur GitHub.
2. Aller sur <https://share.streamlit.io> → **New app**.
3. Choisir le dépôt, la branche `main`, et le fichier `app.py`.
4. Déployer.

La base `mizan.db` n'est pas versionnée : elle est créée automatiquement au
premier lancement, avec des données de démonstration.
