"""Les « questions du jour » de MIZAN AI.

Règles fixes (pas d'IA externe). 1 à 2 questions par jour maximum, réponse
en un geste : oui / non / un montant. Une question déjà vue aujourd'hui
n'est pas reposée.
"""
from datetime import datetime, timedelta

from .engine import _detail, _tiers

# Règles dans l'ordre de priorité. Chaque règle renvoie (regle_id, texte, genre)
# ou None. genre : 'oui' (oui/non) ou 'montant'.


def _regle_ecart_caisse(events, today):
    """1) La caisse comptée ne correspond pas au calcul."""
    clotures = [e for e in events if e.get("type") == "cloture_jour"]
    if not clotures:
        return None
    derniere = sorted(clotures, key=lambda e: (e["date"], e["id"]))[-1]
    comptee = _detail(derniere).get("caisse_comptee")
    if comptee is None:
        return None
    # on recalcule la caisse théorique jusqu'à cette clôture
    from .engine import compute
    sous = [e for e in events if (e["date"], e["id"]) <= (derniere["date"], derniere["id"])]
    theorique = compute(sous)["caisse"]
    ecart = comptee - theorique
    if abs(ecart) < 1:
        return None
    return (
        "ecart_caisse",
        f"La caisse comptée ({comptee:,.0f} dh) ne correspond pas au calcul "
        f"({theorique:,.0f} dh). Écart de {ecart:+,.0f} dh. Est-ce normal ?",
        "oui",
    )


def _regle_jour_sans_cloture(events, today, type_profil):
    """2) Pas de clôture enregistrée hier."""
    if type_profil != "epicerie":
        return None
    hier = (today - timedelta(days=1)).isoformat()
    clotures = [e for e in events if e.get("type") == "cloture_jour" and e["date"] == hier]
    if clotures:
        return None
    # est-ce qu'il y a eu au moins une clôture un jour quelconque ?
    if not any(e.get("type") == "cloture_jour" for e in events):
        return None
    return (
        "jour_sans_cloture",
        f"Aucune clôture enregistrée pour le {hier}. L'épicerie a-t-elle été fermée ?",
        "oui",
    )


def _regle_loyer_absent(events, today):
    """3) Le loyer du mois n'est pas enregistré."""
    mois = today.strftime("%Y-%m")
    loyers = [e for e in events
              if e.get("type") == "depense"
              and (e.get("categorie") or "") == "loyer"
              and (e.get("date") or "").startswith(mois)]
    if loyers:
        return None
    # seulement si on a déjà enregistré un loyer par le passé
    if not any(e.get("type") == "depense" and (e.get("categorie") or "") == "loyer" for e in events):
        return None
    return (
        "loyer_absent",
        "Le loyer de ce mois n'est pas enregistré. L'avez-vous payé ?",
        "oui",
    )


def _regle_prix_achat(events, today):
    """4) Un prix d'achat très différent du dernier achat du même type."""
    achats = [e for e in events if e.get("type") == "achat" and e.get("montant")]
    achats.sort(key=lambda e: (e["date"], e["id"]))
    for i in range(1, len(achats)):
        a, b = achats[i - 1], achats[i]
        if (a.get("categorie") or "") != (b.get("categorie") or ""):
            continue
        if not a.get("montant"):
            continue
        ratio = (b.get("montant") or 0) / a["montant"]
        if ratio >= 1.5:
            return (
                "prix_achat",
                f"« {b.get('categorie') or 'ce produit'} » a coûté {b['montant']:,.0f} dh, "
                f"bien plus que le dernier achat ({a['montant']:,.0f} dh). Confirmez-vous le prix ?",
                "oui",
            )
    return None


def _regle_client_sans_paiement(events, today, creances):
    """5) Un client n'a pas payé depuis au moins 15 jours."""
    if not creances:
        return None
    from .engine import compute
    paiements = [e for e in events if e.get("type") == "paiement_client"]
    for client, montant in creances.items():
        derniers = [p for p in paiements if (_tiers(p) or "Client") == client]
        if derniers:
            dernier = max(derniers, key=lambda e: e["date"])
            if (today - datetime.strptime(dernier["date"], "%Y-%m-%d").date()).days <= 15:
                continue
        return (
            "client_sans_paiement",
            f"{client} vous doit {montant:,.0f} dh et n'a pas payé depuis plus de 15 jours. "
            f"Combien a-t-il réglé ?",
            "montant",
        )
    return None


REGLES = [
    _regle_ecart_caisse,
    _regle_jour_sans_cloture,
    _regle_loyer_absent,
    _regle_prix_achat,
    _regle_client_sans_paiement,
]


def questions_du_jour(conn, profile, events, today=None, creances=None, max_questions=2):
    """
    Construit la liste des questions du jour (1 à max_questions).
    Une question déjà répondue aujourd'hui est reprise telle quelle.
    """
    today = today or datetime.now().date()
    creances = creances if creances is not None else {}

    # règles qui ne dépendent pas du profil
    regles = list(REGLES)
    # _regle_jour_sans_cloture a besoin du type de profil
    regles = [
        (f.__name__, lambda f=f: _appeler_regle(f, events, today, profile.get("type"), creances))
        for f in REGLES
    ]

    resultat = []
    for nom, appel in regles:
        q = appel()
        if q is None:
            continue
        regle_id, texte, genre = q
        existante = conn is not None and _existe(conn, profile["id"], today, regle_id)
        if existante:
            resultat.append({
                "id": existante["id"], "regle": regle_id, "texte": texte,
                "genre": genre, "reponse": existante.get("reponse"),
            })
        elif len(resultat) < max_questions:
            resultat.append({
                "id": None, "regle": regle_id, "texte": texte,
                "genre": genre, "reponse": None,
            })
        if len(resultat) >= max_questions:
            break
    return resultat


def _appeler_regle(fonction, events, today, type_profil, creances):
    """Appelle une règle avec les bons arguments selon sa signature."""
    import inspect
    params = inspect.signature(fonction).parameters
    args = {"events": events, "today": today}
    if "type_profil" in params:
        args["type_profil"] = type_profil
    if "creances" in params:
        args["creances"] = creances
    return fonction(**args)


def _existe(conn, profil_id, today, regle):
    from .db import question_existe
    return question_existe(conn, profil_id, today.isoformat(), regle)
