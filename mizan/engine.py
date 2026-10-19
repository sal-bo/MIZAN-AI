"""Moteur de calcul de MIZAN AI.

Tous les chiffres (chiffre d'affaires, caisse, créances, dettes, résultat)
sont calculés ici à partir du journal d'événements. Rien n'est saisi à la main.
"""
import json

# ----------------------------------------------------------------------------
# Définition des types d'événements.
#   ca      : True  -> compte dans le chiffre d'affaires
#   charge  : True  -> compte dans les dépenses / coûts
#   cash    : 'vente' (encaissé = montant - part à crédit), 'entree', 'sortie', 0
#   creance : +1 crée une créance, -1 la réduit
#   dette   : +1 crée une dette, -1 la réduit
# ----------------------------------------------------------------------------
EVENT_TYPES = {
    "cloture_jour":          {"label": "Clôture du jour",       "ca": True,  "charge": False, "cash": "vente",   "creance": 0,  "dette": 0},
    "vente":                 {"label": "Vente",                 "ca": True,  "charge": False, "cash": "vente",   "creance": 0,  "dette": 0},
    "achat":                 {"label": "Achat",                 "ca": False, "charge": True,  "cash": "achat",   "creance": 0,  "dette": 0},
    "depense":               {"label": "Dépense",               "ca": False, "charge": True,  "cash": "sortie",  "creance": 0,  "dette": 0},
    "transformation":        {"label": "Transformation",        "ca": False, "charge": True,  "cash": 0,        "creance": 0,  "dette": 0},
    "credit_client":         {"label": "Crédit client",         "ca": False, "charge": False, "cash": 0,        "creance": 1,  "dette": 0},
    "paiement_client":       {"label": "Remboursement client",  "ca": False, "charge": False, "cash": "entree",  "creance": -1, "dette": 0},
    "retrait_patron":        {"label": "Retrait du patron",     "ca": False, "charge": False, "cash": "sortie",  "creance": 0,  "dette": 0},
    "apport_adherent":       {"label": "Apport d'un adhérent",  "ca": False, "charge": False, "cash": "entree",  "creance": 0,  "dette": 0},
    "paiement_adherent":     {"label": "Paiement adhérent",     "ca": False, "charge": False, "cash": "entree",  "creance": 0,  "dette": 0},
    "cotisation":            {"label": "Cotisation",            "ca": False, "charge": False, "cash": "entree",  "creance": 0,  "dette": 0},
    "subvention":            {"label": "Subvention",            "ca": False, "charge": False, "cash": "entree",  "creance": 0,  "dette": 0},
    "versement_fournisseur": {"label": "Paiement fournisseur",  "ca": False, "charge": False, "cash": "sortie",  "creance": 0,  "dette": -1},
    # une note audio ne touche à aucun chiffre : elle est juste conservée
    "note":                  {"label": "Note audio",             "ca": False, "charge": False, "cash": 0,        "creance": 0,  "dette": 0},
}

# Types autorisés selon le type de profil
TYPES_PAR_PROFIL = {
    "epicerie": [
        "cloture_jour", "achat", "depense",
        "credit_client", "paiement_client", "retrait_patron",
    ],
    "cooperative": [
        "apport_adherent", "paiement_adherent", "transformation",
        "vente", "depense", "subvention", "cotisation",
    ],
}

# Types qui rentrent dans le chiffre d'affaires (pour ne jamais y mettre
# subventions, cotisations, apports...)
def est_dans_le_ca(type_evt):
    return bool(EVENT_TYPES.get(type_evt, {}).get("ca"))


def _detail(ev):
    """Lit le champ JSON 'detail' d'un événement."""
    if not ev.get("detail"):
        return {}
    try:
        return json.loads(ev["detail"])
    except (ValueError, TypeError):
        return {}


def _tiers(ev):
    return (ev.get("tiers") or "").strip() or None


def _appliquer_caisse(d, ev, montant, caisse):
    """Fait bouger la caisse selon le type d'événement. Retourne la nouvelle caisse."""
    det = _detail(ev)
    if d["ca"]:
        return caisse + montant - (det.get("credit") or 0.0)   # vente : on ne encaisse que le comptant
    if d["cash"] == "entree":
        return caisse + montant
    if d["cash"] == "sortie":
        return caisse - montant
    if d["cash"] == "achat":
        if ev.get("mode") == "credit" or det.get("credit"):
            return caisse                                   # payé plus tard : la caisse ne bouge pas
        return caisse - montant
    return caisse                                           # transformation, crédit client...


def compute(events):
    """Calcule tous les indicateurs à partir de la liste d'événements."""
    ca = ca_confirme = ca_a_confirmer = 0.0
    caisse = 0.0
    charges = 0.0
    hors_ca = 0.0
    creances = {}
    dettes = {}
    derniere_cloture = None

    for ev in events:
        typ = ev.get("type")
        if typ not in EVENT_TYPES:
            continue
        d = EVENT_TYPES[typ]
        montant = ev.get("montant") or 0.0
        confirme = ev.get("statut") == "confirme"
        nom = _tiers(ev)
        det = _detail(ev)

        if d["ca"]:
            ca += montant
            if confirme:
                ca_confirme += montant
            else:
                ca_a_confirmer += montant
            credit = det.get("credit") or 0.0
            if credit:
                cle = nom or "Ventes à crédit"
                creances[cle] = creances.get(cle, 0.0) + credit
            if typ == "cloture_jour":
                derniere_cloture = ev
        elif d["charge"]:
            charges += montant
        else:
            # événements qui créent / réduisent une créance ou une dette
            if d["creance"] == 1:
                cle = nom or "Client"
                creances[cle] = creances.get(cle, 0.0) + montant
            elif d["creance"] == -1:
                cle = nom or "Client"
                creances[cle] = creances.get(cle, 0.0) - montant
            if d["dette"] == -1:
                cle = nom or "Fournisseur"
                dettes[cle] = dettes.get(cle, 0.0) - montant
            if typ in ("apport_adherent", "paiement_adherent", "cotisation", "subvention"):
                hors_ca += montant

        caisse = _appliquer_caisse(d, ev, montant, caisse)

        # une dette d'achat (payé plus tard)
        if typ == "achat" and (ev.get("mode") == "credit" or det.get("credit")):
            cle = nom or "Fournisseur"
            dettes[cle] = dettes.get(cle, 0.0) + montant

    # on retire les montants quasi nuls
    creances = {k: v for k, v in creances.items() if abs(v) >= 0.01}
    dettes = {k: v for k, v in dettes.items() if abs(v) >= 0.01}

    comptage = None
    if derniere_cloture is not None:
        comptage = _detail(derniere_cloture).get("caisse_comptee")

    return {
        "ca": ca,
        "ca_confirme": ca_confirme,
        "ca_a_confirmer": ca_a_confirmer,
        "caisse": caisse,
        "charges": charges,
        "resultat": ca - charges,
        "creances": creances,
        "dettes": dettes,
        "total_creances": sum(creances.values()),
        "total_dettes": sum(dettes.values()),
        "comptage": comptage,
        "ecart": (comptage - caisse) if comptage is not None else None,
        "derniere_cloture": derniere_cloture,
        "hors_ca": hors_ca,
    }


def daily_caisse(events):
    """Historique jour par jour : caisse théorique et caisse comptée."""
    evs = sorted(events, key=lambda e: (e.get("date", ""), e.get("id", 0)))
    caisse = 0.0
    lignes = []
    for ev in evs:
        typ = ev.get("type")
        if typ not in EVENT_TYPES:
            continue
        montant = ev.get("montant") or 0.0
        caisse = _appliquer_caisse(EVENT_TYPES[typ], ev, montant, caisse)
        if typ == "cloture_jour":
            comptee = _detail(ev).get("caisse_comptee")
            lignes.append({
                "date": ev.get("date"),
                "theorique": round(caisse, 2),
                "comptee": comptee,
                "ecart": round(comptee - caisse, 2) if comptee is not None else None,
            })
    return lignes


def formater(montant):
    """Affiche un montant à la marocaine : 12 500 dh."""
    if montant is None:
        return "—"
    return f"{montant:,.0f}".replace(",", " ") + " dh"


# ---------------------------------------------------------------------------
# Agrégats pour les graphiques
# ---------------------------------------------------------------------------
def ca_par_jour(events):
    """Retourne {date: chiffre d'affaires} trié par date."""
    resultat = {}
    for ev in events:
        if EVENT_TYPES.get(ev.get("type"), {}).get("ca") and ev.get("montant"):
            jour = ev.get("date")
            resultat[jour] = resultat.get(jour, 0.0) + ev["montant"]
    return dict(sorted(resultat.items()))


LABELS_CATEGORIES = {
    "loyer": "Loyer",
    "electricite": "Électricité",
    "eau": "Eau",
    "salaire": "Salaires",
    "transport": "Transport",
    "farine": "Farine",
    "sucre": "Sucre",
    "huile": "Huile",
    "the": "Thé",
    "lait": "Lait",
    "divers": "Divers",
}


def charges_par_categorie(events):
    """Retourne {catégorie: montant} des dépenses et achats, du plus grand au plus petit."""
    resultat = {}
    for ev in events:
        if EVENT_TYPES.get(ev.get("type"), {}).get("charge") and ev.get("montant"):
            cat = (ev.get("categorie") or "divers").lower()
            label = LABELS_CATEGORIES.get(cat, cat.capitalize())
            resultat[label] = resultat.get(label, 0.0) + ev["montant"]
    return dict(sorted(resultat.items(), key=lambda x: -x[1]))
