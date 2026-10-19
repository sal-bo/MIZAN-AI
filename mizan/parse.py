"""« IA » de MIZAN AI : transforme un message court en événement structuré.

Aucune API externe, aucune bibliothèque : des règles fixes et simples.
L'IA propose un type, un montant, une date, et pose une question quand il
manque une information. Rien n'est bloqué : une saisie incomplète est
enregistrée « à confirmer ».
"""
import re
from datetime import datetime, timedelta

from .engine import EVENT_TYPES

# Mots-clés -> type d'événement.
# IMPORTANT : l'ordre compte. On teste d'abord « vendu » et « clôture » car
# une phrase comme « vendu 5000 dont 800 à crédit » est une VENTE avec une
# part à crédit, pas un simple crédit client.
REGLES = [
    ("subvention",         ["subvention"]),
    ("cotisation",         ["cotisation"]),
    ("transformation",    ["transformation", "transformé", "transforme", "production", "produit"]),
    ("apport_adherent",   ["apport"]),
    ("paiement_adherent", ["paiement adhérent", "paiement adherent", "adhérent a payé", "adherent a paye"]),
    ("retrait_patron",    ["retrait", "retiré", "retire", "pris dans la caisse"]),
    ("paiement_client",   ["remboursé", "rembourse", "reglement", "règlement", "reçu", "recu"]),
    ("achat",             ["acheté", "achete", "achat", "achetee", "stock", "fournisseur", "marchandise", "marchandises"]),
    ("depense",           ["dépensé", "depense", "dépense", "loyer", "electricité", "electricite", "salaire", "facture", "charge", "transport"]),
    ("cloture_jour",      ["clôture", "cloture", "fermé", "ferme", "recette", "ventes du jour", "cloture du jour", "fermeture"]),
    ("vente",             ["vendu", "vendue", "vente"]),
    ("credit_client",     ["crédit", "credit", "a credit", "à crédit", "plus tard", "différé", "differe"]),
]

# Catégories reconnues pour les dépenses / achats
CATEGORIES = {
    "loyer": ["loyer", "location"],
    "electricite": ["electricité", "electricite", "energie", "bmoce", "lydec"],
    "eau": ["eau", "redevance eau"],
    "salaire": ["salaire", "salaires", "employé", "employe"],
    "transport": ["transport", "livraison", "essence", "carburant"],
    "farine": ["farine"],
    "sucre": ["sucre"],
    "huile": ["huile"],
    "the": ["thé", "the"],
    "lait": ["lait"],
    "divers": ["divers", "autre", "autres"],
}


def _aujourd_hui():
    return datetime.now().date()


def _parse_date(texte, aujourd_hui=None):
    """Reconnaît 'hier', 'aujourd'hui', 'ce matin', '12/05' ou '12-05-2025'."""
    ajd = aujourd_hui or _aujourd_hui()
    t = texte.lower()
    if "avant-hier" in t or "avant hier" in t:
        return ajd - timedelta(days=2)
    if "hier" in t:
        return ajd - timedelta(days=1)
    if "aujourd" in t or "ce matin" in t or "ce soir" in t:
        return ajd
    # date du type 12/05, 12-05, 12.05 ou 12/05/2025
    m = re.search(r"\b(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?\b", t)
    if m:
        jour, mois = int(m.group(1)), int(m.group(2))
        annee = int(m.group(3)) if m.group(3) else ajd.year
        if 1 <= jour <= 31 and 1 <= mois <= 12:
            return datetime(annee, mois, jour).date()
    return ajd


def _parse_montant(texte):
    """Trouve le plus grand nombre du texte (le montant). Ignore la date."""
    t = texte
    # retire la date pour éviter de la prendre pour un montant
    t = re.sub(r"\b\d{1,2}[/\-.]\d{1,2}(?:[/\-.]\d{2,4})?\b", " ", t)
    # normalise les séparateurs décimaux
    t = t.replace(",", ".")
    nombres = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
    if not nombres:
        return None
    return max(nombres)  # le montant est en général le plus grand nombre


def _parse_caisse_comptee(texte, date_trouvee):
    """Extrait le montant de la caisse comptée si présent ('caisse comptée 4100')."""
    m = re.search(r"caisse\s+compt[ée]e?\s+(\d+(?:[.,]\d+)?)", texte.lower())
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _parse_credit(texte):
    """Extrait la part à crédit si présente ('dont 800 à crédit' / 'dont 800 credit')."""
    m = re.search(r"dont\s+(\d+(?:[.,]\d+)?)\s*(?:a\s*)?(?:crédit|credit)", texte.lower())
    if m:
        return float(m.group(1).replace(",", "."))
    return 0.0


def _parse_tiers(texte):
    """Essaie de récupérer un nom de client / fournisseur / adhérent."""
    m = re.search(r"(?:client|fournisseur|fournisseuse|adhérent|adherent)\s+([A-ZÀ-Ý][\wà-ÿ\- ]+)", texte, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""


def _parse_categorie(texte):
    t = texte.lower()
    for cat, mots in CATEGORIES.items():
        for mot in mots:
            if mot in t:
                return cat
    return ""


def _detecter_type(texte, type_profil):
    t = texte.lower()
    for type_evt, mots in REGLES:
        for mot in mots:
            if mot in t:
                return type_evt
    return None


def _detecter_mode(texte):
    t = texte.lower()
    if any(m in t for m in ["crédit", "credit", "a credit", "à crédit", "plus tard", "différé", "differe"]):
        return "credit"
    if any(m in t for m in ["espèces", "especes", "comptant", "cash", "espece"]):
        return "comptant"
    return "comptant"


def parse_message(texte, type_profil, aujourd_hui=None):
    """
    Transforme un message libre en un dictionnaire d'événement.

    Retourne :
        {
          "type": ..., "montant": ..., "date": ..., "tiers": ...,
          "categorie": ..., "mode": ..., "statut": ..., "detail": ...,
          "question": "texte à poser à l'utilisateur" ou None
        }
    """
    texte = (texte or "").strip()
    date = _parse_date(texte, aujourd_hui)
    montant = _parse_montant(texte)
    caisse_comptee = _parse_caisse_comptee(texte, date)
    credit = _parse_credit(texte)
    tiers = _parse_tiers(texte)
    categorie = _parse_categorie(texte)
    mode = _detecter_mode(texte)
    type_evt = _detecter_type(texte, type_profil)

    # Si c'est une épicerie et qu'on parle de vente, on enregistre une clôture
    if type_profil == "epicerie" and type_evt == "vente":
        type_evt = "cloture_jour"

    # Si c'est une épicerie et qu'on dit « vendu » sans crédit explicite,
    # c'est une clôture du jour
    if type_profil == "epicerie" and type_evt == "vente":
        type_evt = "cloture_jour"

    detail = {}
    question = None

    if montant is None:
        statut = "a_confirmer"
        question = "Quel est le montant en dirhams ?"
    elif type_evt is None:
        statut = "a_confirmer"
        question = ("Qu'est-ce qui s'est passé ? Par exemple : "
                    "« vendu 500 », « acheté 1200 », « payé loyer 1500 ».")
    else:
        statut = "confirme"

    if type_evt in ("cloture_jour", "vente"):
        # pour une vente, la part à crédit vient du message (« dont 800 à crédit »)
        # sauf si TOUT est à crédit
        if mode == "credit" and credit == 0.0:
            credit = montant
        detail["credit"] = credit
        if caisse_comptee is not None:
            detail["caisse_comptee"] = caisse_comptee

    if type_evt == "credit_client" and mode == "credit":
        # un crédit client est entièrement à crédit
        pass  # credit reste 0.0, le montant est déjà celui de la créance

    if type_evt == "achat" and mode == "credit":
        detail["credit"] = montant

    return {
        "type": type_evt,
        "montant": montant,
        "date": date.isoformat(),
        "tiers": tiers,
        "categorie": categorie,
        "mode": mode,
        "statut": statut,
        "detail": detail,
        "question": question,
    }


def label_type(type_evt):
    return EVENT_TYPES.get(type_evt, {}).get("label", type_evt or "?")
