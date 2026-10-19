"""Données fictives pré-remplies pour MIZAN AI.

Deux profils de démonstration avec ~30 jours d'événements, pour que le
tableau de bord montre des chiffres dès le premier lancement.
"""
import json
import random
from datetime import datetime, timedelta


def _d(date, jours=0):
    return (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=jours)).strftime("%Y-%m-%d")


def _maintenant():
    return datetime.now().isoformat(timespec="seconds")


def generer_donnees_demo(conn):
    """Crée les profils de démo et leurs événements, si la base est vide."""
    cur = conn.execute("SELECT COUNT(*) AS n FROM profiles")
    if cur.fetchone()["n"] > 0:
        return

    # ------------------------------------------------------------------ #
    # Profil 1 : une épicerie à Casablanca
    # ------------------------------------------------------------------ #
    cur = conn.execute(
        "INSERT INTO profiles (nom, type, ville, cree_le) VALUES (?, ?, ?, ?)",
        ("Épicerie Al Amal", "epicerie", "Casablanca", _maintenant()),
    )
    epicerie_id = cur.lastrowid

    fournisseurs = ["Salam Distribution", "Mega Cash", "Société Générale d'Alimentation"]
    clients = ["Ahmed", "Fatima", "Yassine", "Mme Khadija", "M. Omar"]

    # cumul de la caisse pour que le comptage soit cohérent
    cumul_caisse = 0.0

    # on part du 19 septembre (un mois avant le 19 octobre 2026)
    base = datetime(2026, 9, 19)
    for i in range(31):
        jour = base + timedelta(days=i)
        date = jour.strftime("%Y-%m-%d")

        # 1) la clôture du jour : ventes, dont un peu de crédit, caisse comptée
        ventes = random.randint(3800, 6200)
        credit = random.randint(200, 1400)
        cumul_caisse += ventes - credit
        comptee = cumul_caisse + random.randint(-60, 60)  # petit écart de temps en temps
        detail = {"credit": credit, "caisse_comptee": comptee}
        conn.execute(
            "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (epicerie_id, date, "cloture_jour", ventes, "Clients du jour", "", "comptant",
             "confirme", json.dumps(detail), "Clôture du jour", _maintenant()),
        )

        # 2) un achat fournisseur de temps en temps
        if i % 3 == 0:
            montant = random.randint(900, 3200)
            a_credit = random.random() < 0.3
            if a_credit:
                cumul_caisse += 0  # payé plus tard : la caisse ne bouge pas
            else:
                cumul_caisse -= montant
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (epicerie_id, date, "achat", montant,
                 random.choice(fournisseurs), random.choice(["farine", "huile", "sucre"]),
                 "credit" if a_credit else "comptant", "confirme",
                 json.dumps({"credit": montant} if a_credit else {}),
                 "Achat stock", _maintenant()),
            )

        # 3) des dépenses
        if i % 7 == 3:
            cumul_caisse -= 1500
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (epicerie_id, date, "depense", 1500, "", "loyer", "comptant",
                 "confirme", json.dumps({}), "Loyer du mois", _maintenant()),
            )
        if i % 7 == 5:
            montant_elec = random.randint(150, 450)
            cumul_caisse -= montant_elec
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (epicerie_id, date, "depense", montant_elec, "", "electricite", "comptant",
                 "confirme", json.dumps({}), "Facture d'électricité", _maintenant()),
            )

        # 4) un crédit client et son remboursement
        if i % 4 == 1:
            client = random.choice(clients)
            montant = random.randint(150, 800)
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (epicerie_id, date, "credit_client", montant, client, "", "credit",
                 "confirme", json.dumps({}), f"Crédit accordé à {client}", _maintenant()),
            )
            if random.random() < 0.6 and i + 2 <= 30:
                cumul_caisse += montant
                conn.execute(
                    "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (epicerie_id, _d(date, 2), "paiement_client", montant, client, "", "comptant",
                     "confirme", json.dumps({}), f"Remboursement de {client}", _maintenant()),
                )

        # 5) le patron retire de la caisse de temps en temps
        if i % 10 == 7:
            montant_retrait = random.randint(200, 800)
            cumul_caisse -= montant_retrait
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (epicerie_id, date, "retrait_patron", montant_retrait, "Patron", "", "comptant",
                 "confirme", json.dumps({}), "Retrait du patron", _maintenant()),
            )

    # ------------------------------------------------------------------ #
    # Profil 2 : une coopérative à Taza
    # ------------------------------------------------------------------ #
    cur = conn.execute(
        "INSERT INTO profiles (nom, type, ville, cree_le) VALUES (?, ?, ?, ?)",
        ("Coopérative Tifawt", "cooperative", "Taza", _maintenant()),
    )
    coop_id = cur.lastrowid

    adherents = ["Mohamed", "Amina", "Rachid", "Zahra", "Nabil"]
    cumul_caisse = 0.0
    for i in range(31):
        jour = base + timedelta(days=i)
        date = jour.strftime("%Y-%m-%d")

        # 1) transformation (coût de production)
        montant_transfo = random.randint(400, 1200)
        cumul_caisse -= montant_transfo
        conn.execute(
            "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (coop_id, date, "transformation", montant_transfo, "", "divers",
             "comptant", "confirme", json.dumps({}), "Transformation des olives", _maintenant()),
        )

        # 2) vente du produit transformé
        ventes = random.randint(1500, 4000)
        cumul_caisse += ventes
        conn.execute(
            "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (coop_id, date, "vente", ventes, "Clients", "huile", "comptant",
             "confirme", json.dumps({"credit": 0}), "Vente d'huile", _maintenant()),
        )

        # 3) apports et paiements d'adhérents (jamais dans le CA)
        if i % 5 == 0:
            montant = random.randint(500, 2000)
            cumul_caisse += montant
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (coop_id, date, "apport_adherent", montant,
                 random.choice(adherents), "", "comptant", "confirme", json.dumps({}),
                 "Apport d'un adhérent", _maintenant()),
            )
        if i % 5 == 2:
            montant = random.randint(200, 900)
            cumul_caisse += montant
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (coop_id, date, "paiement_adherent", montant,
                 random.choice(adherents), "", "comptant", "confirme", json.dumps({}),
                 "Paiement adhérent", _maintenant()),
            )

        # 4) cotisations (jamais dans le CA)
        if i % 6 == 4:
            montant = random.choice([50, 100, 200])
            cumul_caisse += montant
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (coop_id, date, "cotisation", montant,
                 random.choice(adherents), "", "comptant", "confirme", json.dumps({}),
                 "Cotisation", _maintenant()),
            )

        # 5) subvention (jamais dans le CA)
        if i == 15:
            cumul_caisse += 5000
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (coop_id, date, "subvention", 5000, "Ministère", "", "comptant",
                 "confirme", json.dumps({}), "Subvention d'équipement", _maintenant()),
            )

        # 6) dépenses de fonctionnement
        if i % 7 == 2:
            montant = random.randint(100, 600)
            cumul_caisse -= montant
            conn.execute(
                "INSERT INTO events (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (coop_id, date, "depense", montant, "", "transport",
                 "comptant", "confirme", json.dumps({}), "Transport", _maintenant()),
            )

    conn.commit()
