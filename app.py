"""MIZAN AI — copilote financier pour épiceries et coopératives marocaines.

Prototype Streamlit : 4 écrans simples, gros boutons, français courant,
sans jargon comptable. Tout est calculé à partir du journal d'événements.

Lancez avec :  streamlit run app.py
"""
import hashlib
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import streamlit as st

from mizan import db, engine, parse, questions
from mizan.seed import generer_donnees_demo

# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="MIZAN AI",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Style général : fond doux, cartes, alertes colorées, gros boutons
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    }
    .stApp { background: #f4f7fc; }
    .block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1180px; }
    #MainMenu, footer { visibility: hidden; }

    /* ---------- Barre latérale ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1a3a 0%, #12306a 100%);
    }
    section[data-testid="stSidebar"] * { color: #e9effb !important; }
    section[data-testid="stSidebar"] .stRadio [role="radiogroup"] { gap: 7px; }
    section[data-testid="stSidebar"] .stRadio label {
        background: rgba(255,255,255,.07);
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 12px;
        padding: 9px 12px;
        transition: background .15s ease;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,.15);
    }
    .brand { font-size: 1.55rem; font-weight: 800; letter-spacing: .02em; }
    .brand-sub { font-size: .82rem; opacity: .75; margin: 2px 0 16px; }

    /* ---------- Hero ---------- */
    .hero {
        background: linear-gradient(120deg, #0d47a1 0%, #1565c0 55%, #1e88e5 100%);
        color: #fff;
        border-radius: 22px;
        padding: 24px 28px;
        margin-bottom: 20px;
        box-shadow: 0 12px 28px rgba(13,71,161,.18);
    }
    .hero-top { display: flex; align-items: center; gap: 16px; }
    .hero-ico { font-size: 2.2rem; line-height: 1; }
    .hero h1 { color: #fff; font-size: 1.85rem; margin: 0; font-weight: 800; }
    .hero p { margin: 4px 0 0; opacity: .9; font-size: 1rem; }
    .pill {
        display: inline-block; margin-top: 14px;
        background: rgba(255,255,255,.16);
        border: 1px solid rgba(255,255,255,.28);
        border-radius: 999px; padding: 5px 13px; font-size: .8rem;
    }

    /* ---------- Cartes de chiffres ---------- */
    .kpi {
        background: #fff; border-radius: 18px; padding: 16px 18px;
        border: 1px solid #e7edf7;
        box-shadow: 0 4px 16px rgba(16,42,86,.06);
        position: relative; overflow: hidden; height: 100%;
        margin-bottom: 12px;
    }
    .kpi::before {
        content: ""; position: absolute; left: 0; top: 0; bottom: 0;
        width: 5px; background: var(--accent, #1565c0);
    }
    .kpi .k-label {
        font-size: .72rem; text-transform: uppercase; letter-spacing: .07em;
        color: #6b7a90; font-weight: 700;
    }
    .kpi .k-value {
        font-size: 1.65rem; font-weight: 800; color: #102a56; margin: 6px 0 2px;
        line-height: 1.15;
    }
    .kpi .k-note { font-size: .78rem; color: #7b8aa0; }
    .kpi.bleu   { --accent: #1565c0; }
    .kpi.vert   { --accent: #2e7d32; }
    .kpi.orange { --accent: #ef6c00; }
    .kpi.rouge  { --accent: #c62828; }
    .kpi.violet { --accent: #6a1b9a; }
    .kpi.gris   { --accent: #78909c; }

    /* ---------- Alertes ---------- */
    .alert {
        display: flex; gap: 13px; align-items: flex-start;
        border-radius: 15px; padding: 14px 17px; margin-bottom: 10px;
        border: 1px solid transparent;
    }
    .alert .a-ico { font-size: 1.3rem; line-height: 1.1; }
    .alert .a-title { font-weight: 700; margin-bottom: 2px; }
    .alert .a-text { font-size: .86rem; opacity: .92; }
    .alert.rouge  { background: #fdecea; border-color: #f5c6c2; color: #8e1c16; }
    .alert.orange { background: #fff8e1; border-color: #f7dd9a; color: #8a5300; }
    .alert.vert   { background: #e8f5e9; border-color: #bfe3c2; color: #1b5e20; }

    .badges { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
    .badge {
        display: inline-block; border-radius: 999px; padding: 5px 12px;
        font-size: .78rem; font-weight: 700;
    }
    .b-rouge  { background: #fdecea; color: #8e1c16; border: 1px solid #f5c6c2; }
    .b-orange { background: #fff8e1; color: #8a5300; border: 1px solid #f7dd9a; }
    .b-vert   { background: #e8f5e9; color: #1b5e20; border: 1px solid #bfe3c2; }

    /* ---------- Exemples / chips ---------- */
    .chip {
        display: inline-block; background: #eef4fd; color: #154a9a;
        border: 1px solid #d8e5fa; border-radius: 999px;
        padding: 7px 13px; margin: 0 7px 7px 0; font-size: .82rem;
    }

    /* ---------- Profil ---------- */
    .profile-card {
        display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
        background: #fff; border: 1px solid #e7edf7; border-radius: 20px;
        padding: 20px 24px; box-shadow: 0 4px 16px rgba(16,42,86,.06);
    }
    .avatar {
        width: 62px; height: 62px; border-radius: 18px;
        background: linear-gradient(135deg, #1565c0, #42a5f5);
        color: #fff; font-size: 1.7rem; font-weight: 800;
        display: flex; align-items: center; justify-content: center;
    }
    .pc-main { flex: 1; min-width: 200px; }
    .pc-name { font-size: 1.35rem; font-weight: 800; color: #102a56; }
    .pc-sub { font-size: .88rem; color: #6b7a90; }
    .pc-stats { display: flex; gap: 26px; flex-wrap: wrap; }
    .pc-stats div { text-align: right; }
    .pc-stats b { display: block; font-size: 1.05rem; color: #102a56; }
    .pc-stats span { font-size: .72rem; color: #7b8aa0; text-transform: uppercase; letter-spacing: .05em; }

    /* ---------- Audio ---------- */
    .audio-card {
        display: flex; gap: 14px; align-items: center;
        background: #eef4fd; border: 1px dashed #b9d0f2;
        border-radius: 16px; padding: 16px 18px; margin-bottom: 14px;
    }
    .audio-card .a-ico { font-size: 1.7rem; }
    .audio-card .a-title { font-weight: 700; color: #102a56; }
    .audio-card .a-text { font-size: .84rem; color: #5b6b82; }

    /* ---------- Question ---------- */
    .q-card {
        background: #fff; border: 1px solid #e7edf7; border-radius: 18px;
        padding: 18px 20px; margin-bottom: 12px;
        box-shadow: 0 4px 16px rgba(16,42,86,.06);
    }
    .q-top { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
    .q-ico { font-size: 1.35rem; }
    .q-badge {
        background: #eef4fd; color: #154a9a; border: 1px solid #d8e5fa;
        border-radius: 999px; padding: 3px 10px; font-size: .7rem;
        text-transform: uppercase; letter-spacing: .05em; font-weight: 700;
    }
    .q-text { font-size: 1.06rem; color: #102a56; font-weight: 600; }

    /* ---------- Boutons ---------- */
    .stButton > button {
        min-height: 48px; font-size: 1rem; font-weight: 600;
        border-radius: 12px; border: 1px solid #d8e2f3;
    }
    .stButton > button[kind="primary"] {
        background: #1565c0; border-color: #1565c0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Petites fonctions d'affichage
# ---------------------------------------------------------------------------
def fmt(montant):
    return engine.formater(montant)


def hero(icone, titre, sous_titre, pill=None):
    pill_html = f"<span class='pill'>{pill}</span>" if pill else ""
    st.markdown(
        f"<div class='hero'><div class='hero-top'>"
        f"<div class='hero-ico'>{icone}</div>"
        f"<div><h1>{titre}</h1><p>{sous_titre}</p></div>"
        f"</div>{pill_html}</div>",
        unsafe_allow_html=True,
    )


def kpi(label, valeur, note="", ton="bleu", icone=""):
    st.markdown(
        f"<div class='kpi {ton}'>"
        f"<div class='k-label'>{icone} {label}</div>"
        f"<div class='k-value'>{valeur}</div>"
        f"<div class='k-note'>{note}</div></div>",
        unsafe_allow_html=True,
    )


def afficher_alerte(niveau, titre, texte):
    icone = {"rouge": "🚨", "orange": "⚠️", "vert": "✅"}.get(niveau, "ℹ️")
    st.markdown(
        f"<div class='alert {niveau}'>"
        f"<div class='a-ico'>{icone}</div>"
        f"<div><div class='a-title'>{titre}</div>"
        f"<div class='a-text'>{texte}</div></div></div>",
        unsafe_allow_html=True,
    )


def badges_alertes(alertes):
    nb = {"rouge": 0, "orange": 0, "vert": 0}
    for niveau, _, _ in alertes:
        nb[niveau] = nb.get(niveau, 0) + 1
    html = "<div class='badges'>"
    if nb["rouge"]:
        html += f"<span class='badge b-rouge'>🚨 {nb['rouge']} critique(s)</span>"
    if nb["orange"]:
        html += f"<span class='badge b-orange'>⚠️ {nb['orange']} à surveiller</span>"
    if nb["vert"]:
        html += f"<span class='badge b-vert'>✅ {nb['vert']} point(s) OK</span>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Connexion et profil
# ---------------------------------------------------------------------------
conn = db.init_db()
generer_donnees_demo(conn)


def get_profil():
    profil_id = st.session_state.get("profil_id")
    if profil_id:
        return db.profil_par_id(conn, profil_id)
    profils = db.lister_profils(conn)
    return profils[0] if profils else None


def set_profil(profil_id):
    st.session_state["profil_id"] = profil_id


def label_type(type_evt):
    return parse.label_type(type_evt)


profil = get_profil()
if profil:
    set_profil(profil["id"])


# ---------------------------------------------------------------------------
# Calcul des alertes du tableau de bord
# ---------------------------------------------------------------------------
def calculer_alertes(m, events, profil):
    alertes = []

    # 1) caisse négative
    if m["caisse"] < 0:
        alertes.append((
            "rouge", "Caisse négative",
            f"Votre caisse est à {fmt(m['caisse'])}. Vérifiez les retraits et les dépenses.",
        ))

    # 2) écart de caisse
    if m["ecart"] is not None:
        if abs(m["ecart"]) > 500:
            alertes.append((
                "rouge", "Écart de caisse important",
                f"Écart de {fmt(m['ecart'])} entre la caisse comptée et la caisse calculée.",
            ))
        elif abs(m["ecart"]) > 100:
            alertes.append((
                "orange", "Écart de caisse",
                f"Écart de {fmt(m['ecart'])} à vérifier.",
            ))

    # 3) résultat négatif
    if m["resultat"] < 0:
        alertes.append((
            "rouge", "Résultat négatif",
            f"Vous avez dépensé plus que vous n'avez vendu ({fmt(m['resultat'])}).",
        ))

    # 4) clôture manquante (épicerie)
    if profil["type"] == "epicerie":
        clotures = [e for e in events if e["type"] == "cloture_jour"]
        if clotures:
            derniere = max(e["date"] for e in clotures)
            jours = (date.today() - datetime.strptime(derniere, "%Y-%m-%d").date()).days
            if jours > 1:
                alertes.append((
                    "orange", "Pas de clôture récente",
                    f"Dernière clôture enregistrée le {derniere}.",
                ))

    # 5) loyer du mois absent
    mois = date.today().strftime("%Y-%m")
    loyers = [e for e in events if e["type"] == "depense"
              and (e.get("categorie") or "") == "loyer"
              and (e.get("date") or "").startswith(mois)]
    if not loyers and any(e["type"] == "depense" and (e.get("categorie") or "") == "loyer"
                          for e in events):
        alertes.append((
            "orange", "Loyer du mois non enregistré",
            "Le loyer de ce mois n'apparaît pas dans le journal.",
        ))

    # 6) créances importantes
    if m["total_creances"] > 0:
        alertes.append((
            "orange", "Les clients vous doivent",
            f"{fmt(m['total_creances'])} à récupérer auprès de "
            f"{len(m['creances'])} client(s).",
        ))

    # 7) saisies à confirmer
    a_confirmer = [e for e in events if e["statut"] == "a_confirmer"]
    if a_confirmer:
        alertes.append((
            "orange", "Informations à confirmer",
            f"{len(a_confirmer)} saisie(s) incomplète(s) à vérifier.",
        ))

    if not alertes:
        alertes.append((
            "vert", "Tout va bien",
            "Aucune alerte : votre caisse, vos ventes et vos dettes sont cohérentes.",
        ))
    return alertes


def sante(alertes):
    if any(niveau == "rouge" for niveau, _, _ in alertes):
        return "🔴 À corriger"
    if any(niveau == "orange" for niveau, _, _ in alertes):
        return "🟠 À surveiller"
    return "🟢 Bonne santé"


# ---------------------------------------------------------------------------
# Barre latérale
# ---------------------------------------------------------------------------
st.sidebar.markdown("<div class='brand'>🧮 MIZAN AI</div>", unsafe_allow_html=True)
st.sidebar.markdown("<div class='brand-sub'>Votre argent, en mots simples.</div>",
                    unsafe_allow_html=True)

if profil:
    st.sidebar.markdown(
        f"<div style='background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);"
        f"border-radius:14px;padding:12px 14px;margin-bottom:16px;'>"
        f"<div style='font-weight:800;font-size:1.02rem;'>{profil['nom']}</div>"
        f"<div style='font-size:.78rem;opacity:.8;'>{profil['ville']} · "
        + ("Épicerie" if profil["type"] == "epicerie" else "Coopérative")
        + "</div></div>",
        unsafe_allow_html=True,
    )

NAV = [
    "🏠  Mon profil",
    "✍️  Je dis ce qui s'est passé",
    "📊  Mes chiffres",
    "❓  Questions du jour",
]
choix = st.sidebar.radio("Navigation", NAV, label_visibility="collapsed")

st.sidebar.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
st.sidebar.caption("Prototype local · aucune donnée ne quitte votre machine.")

# ===========================================================================
# ÉCRAN 1 — Mon profil
# ===========================================================================
if choix == NAV[0]:
    hero("🏠", "Mon profil", "Qui êtes-vous ? C'est tout ce qu'il faut pour commencer.")

    if profil:
        events = db.lister_evenements(conn, profil["id"])
        m = engine.compute(events)
        initiale = (profil["nom"] or "?").strip()[0].upper()
        st.markdown(
            f"<div class='profile-card'>"
            f"<div class='avatar'>{initiale}</div>"
            f"<div class='pc-main'>"
            f"<div class='pc-name'>{profil['nom']}</div>"
            f"<div class='pc-sub'>{profil['ville'] or 'Ville non renseignée'} · "
            + ("Épicerie" if profil["type"] == "epicerie" else "Coopérative")
            + "</div></div>"
            f"<div class='pc-stats'>"
            f"<div><b>{len(events)}</b><span>événements</span></div>"
            f"<div><b>{fmt(m['ca'])}</b><span>vendu</span></div>"
            f"<div><b>{fmt(m['caisse'])}</b><span>encaissé</span></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.write("")
    with st.container(border=True):
        st.subheader("➕ Créer un nouveau profil")
        st.caption("Choisissez le type : l'interface s'adapte ensuite automatiquement.")
        with st.form("nouveau_profil"):
            nom = st.text_input("Nom de l'épicerie ou de la coopérative")
            type_profil = st.radio("C'est une…", ["Épicerie", "Coopérative"], horizontal=True)
            ville = st.text_input("Ville")
            valider = st.form_submit_button("Enregistrer ce profil", type="primary",
                                            use_container_width=True)
        if valider:
            if nom.strip():
                pid = db.creer_profil(
                    conn, nom.strip(),
                    "epicerie" if type_profil == "Épicerie" else "cooperative",
                    ville.strip(),
                )
                set_profil(pid)
                st.success(f"Profil « {nom} » créé !")
                st.rerun()
            else:
                st.warning("Donnez au moins un nom.")

    profils = db.lister_profils(conn)
    if len(profils) > 1:
        st.write("")
        st.subheader("🔄 Changer de profil")
        cols = st.columns(min(3, len(profils)))
        for i, p in enumerate(profils):
            with cols[i % len(cols)]:
                with st.container(border=True):
                    st.markdown(f"**{p['nom']}**")
                    st.caption(f"{p['ville']} · "
                               + ("Épicerie" if p["type"] == "epicerie" else "Coopérative"))
                    actif = p["id"] == profil["id"] if profil else False
                    if st.button("Profil actif" if actif else "Utiliser",
                                 key=f"profil_{p['id']}", use_container_width=True,
                                 disabled=actif):
                        set_profil(p["id"])
                        st.rerun()

# ===========================================================================
# ÉCRAN 2 — Je dis ce qui s'est passé
# ===========================================================================
elif choix == NAV[1]:
    hero("✍️", "Je dis ce qui s'est passé",
         "Un message court, et l'IA range tout. Ou parlez avec le micro.")

    if not profil:
        st.info("Créez d'abord un profil dans l'écran 1.")
    else:
        type_profil = profil["type"]

        onglet_ecrire, onglet_parler = st.tabs(["✍️  Écrire", "🎤  Parler"])

        # ------------------------------------------------------------- Écrire
        with onglet_ecrire:
            exemples = (
                [
                    "vendu 5000 hier dont 800 à crédit, caisse comptée 4100",
                    "acheté 1200 de farine à crédit",
                    "payé loyer 1500",
                    "client Ahmed a remboursé 300",
                    "retrait 500",
                ]
                if type_profil == "epicerie"
                else [
                    "apport de Mohamed 1000",
                    "transformation 800",
                    "vendu 3000 d'huile",
                    "subvention 5000",
                    "cotisation 100",
                    "payé transport 200",
                ]
            )
            st.markdown("**Exemples rapides**")
            st.markdown("".join(f"<span class='chip'>{ex}</span>" for ex in exemples),
                        unsafe_allow_html=True)

            with st.form("saisie_texte"):
                message = st.text_area(
                    "Qu'est-ce qui s'est passé ?",
                    height=120,
                    placeholder="Écrivez comme vous parlez…",
                )
                envoyer = st.form_submit_button(
                    "✅ Enregistrer", type="primary", use_container_width=True
                )

            if envoyer and message.strip():
                evt = parse.parse_message(message, type_profil, date.today())
                db.ajouter_evenement(
                    conn, profil["id"], evt["date"], evt["type"], evt["montant"],
                    evt["tiers"], evt["categorie"], evt["mode"], evt["statut"],
                    evt["detail"] or None, message[:80],
                )
                st.success("C'est noté !")

                ton = "orange" if evt["statut"] == "a_confirmer" else "vert"
                statut = "À confirmer" if evt["statut"] == "a_confirmer" else "Confirmé"
                montant_txt = fmt(evt["montant"]) if evt["montant"] else "montant à préciser"
                tiers_txt = f" · {evt['tiers']}" if evt["tiers"] else ""
                st.markdown(
                    f"<div class='alert {ton}'>"
                    f"<div class='a-ico'>🤖</div>"
                    f"<div><div class='a-title'>{label_type(evt['type'])}</div>"
                    f"<div class='a-text'>{evt['date']} · {montant_txt}{tiers_txt} · {statut}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                if evt["question"]:
                    st.warning(f"❓ {evt['question']}")

        # ------------------------------------------------------------- Parler
        with onglet_parler:
            st.markdown(
                "<div class='audio-card'>"
                "<div class='a-ico'>🎤</div>"
                "<div><div class='a-title'>Parler au lieu d'écrire</div>"
                "<div class='a-text'>Appuyez sur le micro, parlez, puis arrêtez. "
                "L'audio est conservé dans votre historique.</div></div></div>",
                unsafe_allow_html=True,
            )

            if st.session_state.pop("audio_ok", False):
                st.success("✅ Audio gardé dans l'historique.")

            try:
                audio = st.audio_input("Appuyez sur le micro pour enregistrer",
                                       key="audio_input")
            except Exception:
                audio = None
                st.info("L'enregistrement audio nécessite un navigateur récent "
                        "(Chrome, Edge ou Firefox).")

            if audio is not None:
                donnees = audio.getvalue()
                empreinte = hashlib.md5(donnees).hexdigest()
                st.audio(donnees)
                deja_garde = st.session_state.get("audio_hash") == empreinte

                col_info, col_btn = st.columns([2, 1])
                with col_info:
                    st.caption(f"{len(donnees) / 1024:.0f} Ko · "
                               + ("déjà dans l'historique" if deja_garde
                                  else "prêt à être gardé"))
                with col_btn:
                    if st.button("💾 Garder cet audio", key="garder_audio",
                                 type="primary", use_container_width=True,
                                 disabled=deja_garde):
                        nom = f"note_{datetime.now():%Y%m%d_%H%M%S}.wav"
                        aid = db.ajouter_audio(conn, profil["id"], nom, donnees)
                        db.ajouter_evenement(
                            conn, profil["id"], date.today().isoformat(), "note",
                            None, "", "", "comptant", "confirme", None,
                            f"🎤 Note audio #{aid} · {nom}",
                        )
                        st.session_state["audio_hash"] = empreinte
                        st.session_state["audio_ok"] = True
                        st.rerun()
            else:
                st.caption("Votre voix reste sur votre machine, rien n'est envoyé.")

        # --------------------------------------------------------- Historique
        st.write("")
        st.subheader("🗂️ Historique complet")
        events = db.lister_evenements(conn, profil["id"])

        if not events:
            st.info("Aucun événement enregistré pour le moment.")
        else:
            col_f1, col_f2 = st.columns([1, 2])
            types_dispo = sorted({label_type(e["type"]) for e in events})
            with col_f1:
                filtre_type = st.selectbox("Filtrer par type",
                                           ["Tous"] + types_dispo, key="filtre_type")
            with col_f2:
                recherche = st.text_input("Chercher un nom, une note…", key="recherche")

            filtres = []
            for ev in events:
                if filtre_type != "Tous" and label_type(ev["type"]) != filtre_type:
                    continue
                if recherche:
                    bloc = " ".join(str(ev.get(k) or "") for k in
                                    ("tiers", "note", "categorie", "type")).lower()
                    if recherche.lower() not in bloc:
                        continue
                filtres.append(ev)

            lignes = []
            for ev in reversed(filtres):
                lignes.append({
                    "ID": ev["id"],
                    "Date": ev["date"],
                    "Type": label_type(ev["type"]),
                    "Montant (dh)": ev["montant"],
                    "Tiers": ev["tiers"] or "",
                    "Catégorie": ev["categorie"] or "",
                    "Statut": "✅ Confirmé" if ev["statut"] == "confirme"
                              else "⚠️ À confirmer",
                    "Note": ev["note"] or "",
                })
            st.dataframe(pd.DataFrame(lignes), use_container_width=True,
                         hide_index=True)

            with st.expander("🎤 Notes audio enregistrées"):
                audios = db.lister_audios(conn, profil["id"])
                if not audios:
                    st.caption("Aucune note audio pour le moment.")
                for a in audios[:10]:
                    st.markdown(f"**#{a['id']}** · {a['cree_le'][:16].replace('T', ' ')} "
                                f"· {a['taille'] / 1024:.0f} Ko")
                    complet = db.obtenir_audio(conn, a["id"])
                    if complet:
                        st.audio(complet["donnees"])
                    if st.button("🗑️ Supprimer cette note", key=f"del_audio_{a['id']}"):
                        db.supprimer_audio(conn, a["id"])
                        st.rerun()

            st.write("")
            st.subheader("🗑️ Supprimer une entrée")
            col_id, col_btn = st.columns([3, 1])
            with col_id:
                id_a_supprimer = st.number_input("Numéro (ID) de la ligne :",
                                                 min_value=1, step=1, key="id_suppr")
            with col_btn:
                st.write("")
                st.write("")
                if st.button("Supprimer", key="btn_suppr", use_container_width=True):
                    existe = conn.execute("SELECT id FROM events WHERE id = ?",
                                          (int(id_a_supprimer),)).fetchone()
                    if existe:
                        conn.execute("DELETE FROM events WHERE id = ?",
                                     (int(id_a_supprimer),))
                        conn.commit()
                        st.rerun()
                    else:
                        st.error("Aucune entrée avec ce numéro.")

# ===========================================================================
# ÉCRAN 3 — Mes chiffres (dashboard + alertes)
# ===========================================================================
elif choix == NAV[2]:
    if not profil:
        hero("📊", "Mes chiffres", "Créez d'abord un profil.")
        st.info("Créez d'abord un profil dans l'écran 1.")
    else:
        events = db.lister_evenements(conn, profil["id"])
        m = engine.compute(events)
        alertes = calculer_alertes(m, events, profil)

        hero(
            "📊", "Mes chiffres",
            f"{profil['nom']} · {date.today():%d/%m/%Y}",
            pill=f"État général : {sante(alertes)}",
        )

        # ---- bandeau d'alertes ----
        badges_alertes(alertes)
        for niveau, titre, texte in alertes:
            afficher_alerte(niveau, titre, texte)

        st.write("")

        # ---- cartes de chiffres ----
        if profil["type"] == "epicerie":
            ecart = m["ecart"]
            ton_ecart = "vert"
            if ecart is not None and abs(ecart) >= 500:
                ton_ecart = "rouge"
            elif ecart is not None and abs(ecart) >= 100:
                ton_ecart = "orange"

            c1, c2, c3, c4 = st.columns(4, gap="medium")
            with c1:
                kpi("Vendu", fmt(m["ca"]),
                    f"dont {fmt(m['ca_a_confirmer'])} à confirmer", "bleu", "🛒")
            with c2:
                kpi("Encaissé", fmt(m["caisse"]),
                    "ce que la caisse devrait contenir", "vert", "💰")
            with c3:
                kpi("Compté", fmt(m["comptage"]),
                    "dernier comptage de caisse", "bleu", "🧾")
            with c4:
                kpi("Écart de caisse", fmt(ecart),
                    "compté − calculé", ton_ecart, "⚖️")

            c5, c6, c7, c8 = st.columns(4, gap="medium")
            with c5:
                kpi("Les clients me doivent", fmt(m["total_creances"]),
                    f"{len(m['creances'])} client(s)", "orange", "👥")
            with c6:
                kpi("Je dois aux fournisseurs", fmt(m["total_dettes"]),
                    f"{len(m['dettes'])} fournisseur(s)", "violet", "🚚")
            with c7:
                kpi("Dépensé", fmt(m["charges"]),
                    "achats + dépenses", "gris", "📤")
            with c8:
                kpi("Résultat", fmt(m["resultat"]),
                    "vendu − dépensé", "vert" if m["resultat"] >= 0 else "rouge", "📈")
        else:
            # coopérative
            marge = (m["resultat"] / m["ca"] * 100) if m["ca"] else 0.0
            c1, c2, c3, c4 = st.columns(4, gap="medium")
            with c1:
                kpi("Vendu", fmt(m["ca"]),
                    "hors subventions et cotisations", "bleu", "🫒")
            with c2:
                kpi("Encaissé", fmt(m["caisse"]),
                    "tous les encaissements", "vert", "💰")
            with c3:
                kpi("Hors chiffre d'affaires", fmt(m["hors_ca"]),
                    "apports, cotisations, subventions", "violet", "🤝")
            with c4:
                kpi("Dépensé", fmt(m["charges"]),
                    "transformations + dépenses", "gris", "📤")

            c5, c6, c7, c8 = st.columns(4, gap="medium")
            with c5:
                kpi("Résultat", fmt(m["resultat"]),
                    "vendu − dépensé", "vert" if m["resultat"] >= 0 else "rouge", "📈")
            with c6:
                kpi("Marge", f"{marge:.0f} %",
                    "part du résultat dans les ventes",
                    "vert" if marge >= 0 else "rouge", "📊")
            with c7:
                kpi("Les clients me doivent", fmt(m["total_creances"]),
                    "créances", "orange", "👥")
            with c8:
                kpi("Je dois aux fournisseurs", fmt(m["total_dettes"]),
                    "dettes", "violet", "🚚")

        # ---- graphiques ----
        st.write("")
        col_g1, col_g2 = st.columns(2, gap="medium")

        with col_g1:
            st.subheader("📈 Vendu par jour")
            serie = engine.ca_par_jour(events)
            if serie:
                df_ca = pd.DataFrame({
                    "Date": list(serie.keys()),
                    "Vendu": list(serie.values()),
                })
                st.bar_chart(df_ca, x="Date", y="Vendu", color="#1565c0", height=260)
            else:
                st.caption("Pas encore de vente enregistrée.")

        with col_g2:
            if profil["type"] == "epicerie":
                st.subheader("💰 Caisse : calculée vs comptée")
                lignes = engine.daily_caisse(events)
                lignes = [l for l in lignes if l["comptee"] is not None]
                if lignes:
                    df_caisse = pd.DataFrame([{
                        "Date": l["date"],
                        "Calculée": l["theorique"],
                        "Comptée": l["comptee"],
                    } for l in lignes])
                    st.line_chart(df_caisse, x="Date",
                                  y=["Calculée", "Comptée"], height=260)
                else:
                    st.caption("Pas encore de comptage de caisse.")
            else:
                st.subheader("📤 Où va l'argent")
                serie = engine.charges_par_categorie(events)
                if serie:
                    df_ch = pd.DataFrame({
                        "Catégorie": list(serie.keys()),
                        "Montant": list(serie.values()),
                    })
                    st.bar_chart(df_ch, x="Catégorie", y="Montant",
                                 color="#ef6c00", height=260)
                else:
                    st.caption("Pas encore de dépense enregistrée.")

        # ---- créances et dettes ----
        st.write("")
        col_t1, col_t2 = st.columns(2, gap="medium")

        with col_t1:
            st.subheader("👥 Les clients me doivent")
            if m["creances"]:
                df_cr = pd.DataFrame([
                    {"Client": k, "Montant": v}
                    for k, v in sorted(m["creances"].items(), key=lambda x: -x[1])
                ])
                st.dataframe(
                    df_cr,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Montant": st.column_config.ProgressColumn(
                            "Montant (dh)", format="%.0f dh",
                            min_value=0.0,
                            max_value=float(max(df_cr["Montant"].max(), 1)),
                        )
                    },
                )
            else:
                st.success("Personne ne vous doit rien. 👍")

        with col_t2:
            st.subheader("🚚 Je dois aux fournisseurs")
            if m["dettes"]:
                df_dt = pd.DataFrame([
                    {"Fournisseur": k, "Montant": v}
                    for k, v in sorted(m["dettes"].items(), key=lambda x: -x[1])
                ])
                st.dataframe(
                    df_dt,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Montant": st.column_config.ProgressColumn(
                            "Montant (dh)", format="%.0f dh",
                            min_value=0.0,
                            max_value=float(max(df_dt["Montant"].max(), 1)),
                        )
                    },
                )
            else:
                st.success("Vous ne devez rien aux fournisseurs. 👍")

        # ---- derniers mouvements ----
        st.write("")
        st.subheader("🕒 Derniers mouvements")
        if events:
            recents = list(reversed(events[-8:]))
            df_rec = pd.DataFrame([{
                "Date": e["date"],
                "Type": label_type(e["type"]),
                "Montant (dh)": e["montant"],
                "Tiers": e["tiers"] or "",
                "Statut": "✅" if e["statut"] == "confirme" else "⚠️ À confirmer",
            } for e in recents])
            st.dataframe(df_rec, use_container_width=True, hide_index=True)
        else:
            st.caption("Aucun mouvement pour le moment.")

        n = db.compter_a_confirmer(conn, profil["id"])
        if n:
            st.warning(f"⚠️ {n} saisie(s) à confirmer. Elles comptent dans les chiffres "
                       "mais restent marquées « à confirmer ».")

# ===========================================================================
# ÉCRAN 4 — Questions du jour
# ===========================================================================
elif choix == NAV[3]:
    hero("❓", "Questions du jour",
         "L'IA regarde vos chiffres et vous pose 1 ou 2 questions. Réponse en un geste.")

    if not profil:
        st.info("Créez d'abord un profil dans l'écran 1.")
    else:
        events = db.lister_evenements(conn, profil["id"])
        m = engine.compute(events)

        liste = questions.questions_du_jour(
            conn, profil, events, date.today(),
            creances=m["creances"], max_questions=2,
        )

        if not liste:
            st.markdown(
                "<div class='alert vert'><div class='a-ico'>✅</div>"
                "<div><div class='a-title'>Rien à signaler aujourd'hui</div>"
                "<div class='a-text'>Vos chiffres sont cohérents. Profitez-en !</div>"
                "</div></div>",
                unsafe_allow_html=True,
            )

        for i, q in enumerate(liste):
            regle = q["regle"].replace("_", " ")
            st.markdown(
                f"<div class='q-card'>"
                f"<div class='q-top'><span class='q-ico'>❓</span>"
                f"<span class='q-badge'>{regle}</span></div>"
                f"<div class='q-text'>{q['texte']}</div></div>",
                unsafe_allow_html=True,
            )

            if q["reponse"]:
                st.success(f"Réponse enregistrée : {q['reponse']}")
            else:
                col1, col2, col3 = st.columns([1, 1, 2], gap="medium")
                with col1:
                    if st.button("👍 Oui", key=f"o{i}", type="primary",
                                 use_container_width=True):
                        if q.get("id"):
                            db.repondre_question(conn, q["id"], "oui")
                        else:
                            qid = db.ajouter_question(
                                conn, profil["id"], date.today().isoformat(),
                                q["regle"], q["texte"],
                            )
                            db.repondre_question(conn, qid, "oui")
                        st.rerun()
                with col2:
                    if st.button("👎 Non", key=f"n{i}", use_container_width=True):
                        if q.get("id"):
                            db.repondre_question(conn, q["id"], "non")
                        else:
                            qid = db.ajouter_question(
                                conn, profil["id"], date.today().isoformat(),
                                q["regle"], q["texte"],
                            )
                            db.repondre_question(conn, qid, "non")
                        st.rerun()
                with col3:
                    montant = st.number_input(
                        "Ou un montant en dh :", min_value=0.0, step=50.0, key=f"m{i}"
                    )
                    if st.button("Valider le montant", key=f"v{i}",
                                 use_container_width=True):
                        if q.get("id"):
                            db.repondre_question(conn, q["id"], montant)
                        else:
                            qid = db.ajouter_question(
                                conn, profil["id"], date.today().isoformat(),
                                q["regle"], q["texte"],
                            )
                            db.repondre_question(conn, qid, montant)
                        st.rerun()

        # ---- réponses déjà données aujourd'hui ----
        reponses = conn.execute(
            "SELECT regle, reponse, cree_le FROM questions "
            "WHERE profile_id = ? AND date = ? AND reponse IS NOT NULL "
            "ORDER BY id DESC",
            (profil["id"], date.today().isoformat()),
        ).fetchall()
        if reponses:
            st.write("")
            st.subheader("Aujourd'hui, vous avez répondu")
            for r in reponses:
                st.markdown(
                    f"<div class='alert vert'><div class='a-ico'>✔️</div>"
                    f"<div><div class='a-title'>{r['regle'].replace('_', ' ')}</div>"
                    f"<div class='a-text'>Réponse : {r['reponse']}</div></div></div>",
                    unsafe_allow_html=True,
                )
