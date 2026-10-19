"""MIZAN AI — copilote financier pour épiceries et coopératives marocaines.

Prototype Streamlit. 4 écrans simples, gros boutons, français courant,
sans jargon comptable. Interfaces séparées : épiceries d'un côté,
coopératives de l'autre. Tableau de bord avec alertes visuelles.

Lancez avec :  streamlit run app.py
"""
import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd

from mizan import db, engine, parse, questions
from mizan.seed import generer_donnees_demo

# ---------------------------------------------------------------------------
# Réglages de la page et style « gros boutons, gros textes »
# ---------------------------------------------------------------------------
st.set_page_config(page_title="MIZAN AI", page_icon="🧮", layout="wide")

st.markdown(
    """
    <style>
    .stButton > button {
        min-height: 56px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 12px;
    }
    textarea, input { font-size: 18px !important; }
    .carte {
        background: #f4f6f8;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 12px;
    }
    .carte .titre { font-size: 15px; color: #555; }
    .carte .chiffre { font-size: 34px; font-weight: bold; color: #123; }
    .carte .note { font-size: 13px; color: #888; }
    h1, h2 { color: #0d47a1; }
    /* indicateurs d'alerte */
    .alerte-rouge  { background:#ffebee; border-left:6px solid #c62828; border-radius:8px; padding:14px 18px; margin-bottom:10px; }
    .alerte-orange { background:#fff8e1; border-left:6px solid #ef6c00; border-radius:8px; padding:14px 18px; margin-bottom:10px; }
    .alerte-vert   { background:#e8f5e9; border-left:6px solid #2e7d32; border-radius:8px; padding:14px 18px; margin-bottom:10px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt(montant):
    return engine.formater(montant)


# ---------------------------------------------------------------------------
# Base de données + données de démarrage
# ---------------------------------------------------------------------------
conn = db.init_db()
generer_donnees_demo(conn)

# dossier pour les enregistrements audio
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "audio"), exist_ok=True)


# ---------------------------------------------------------------------------
# Fonctions utilitaires
# ---------------------------------------------------------------------------
def get_profil():
    profil_id = st.session_state.get("profil_id")
    if profil_id:
        return db.profil_par_id(conn, profil_id)
    profils = db.lister_profils(conn)
    return profils[0] if profils else None


def set_profil(profil_id):
    st.session_state["profil_id"] = profil_id


def supprimer_evenement(event_id):
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    st.rerun()


def _repondre(profil, q, reponse):
    """Enregistre la réponse à une question du jour."""
    if q.get("id"):
        db.repondre_question(conn, q["id"], reponse)
    else:
        qid = db.ajouter_question(conn, profil["id"], date.today().isoformat(),
                                  q["regle"], q["texte"])
        db.repondre_question(conn, qid, reponse)
    st.rerun()


def enregistrer_audio():
    """Permet d'enregistrer un message vocal via le micro du navigateur."""
    try:
        audio = st.audio_input("🎤 Enregistrer un message vocal")
    except Exception:
        st.info("L'enregistrement audio nécessite un navigateur récent (Chrome, Edge).")
        return None
    if audio is None:
        return None
    racine = os.path.dirname(os.path.abspath(__file__))
    nom = os.path.join(racine, "audio", datetime.now().strftime("%Y%m%d_%H%M%S") + ".wav")
    with open(nom, "wb") as f:
        f.write(audio.getvalue())
    return nom


def calculer_alertes(m, events, profil):
    """Calcule les alertes du tableau de bord (rouge / orange / vert)."""
    alertes = []

    # caisse négative -> rouge
    if m["caisse"] < 0:
        alertes.append(("rouge", "🚨 Caisse négative",
                        f"Votre caisse est à {fmt(m['caisse'])}. Vérifiez les retraits."))

    # écart de caisse
    if m["ecart"] is not None:
        if abs(m["ecart"]) > 500:
            alertes.append(("rouge", "🚨 Écart de caisse important",
                            f"Écart de {fmt(m['ecart'])} entre le compté et le calculé."))
        elif abs(m["ecart"]) > 100:
            alertes.append(("orange", "⚠️ Écart de caisse",
                            f"Écart de {fmt(m['ecart'])} à vérifier."))

    # pas de clôture récente (épicerie)
    if profil["type"] == "epicerie":
        clotures = [e for e in events if e["type"] == "cloture_jour"]
        if clotures:
            derniere = max(e["date"] for e in clotures)
            jours = (date.today() - datetime.strptime(derniere, "%Y-%m-%d").date()).days
            if jours > 1:
                alertes.append(("orange", "⚠️ Pas de clôture récente",
                                f"Dernière clôture : {derniere}."))

    # créances importantes
    if m["total_creances"] > 5000:
        alertes.append(("orange", "⚠️ Créances clients",
                        f"Total : {fmt(m['total_creances'])}"))

    if not alertes:
        alertes.append(("vert", "✅ Tout va bien", "Aucune alerte à signaler."))

    return alertes


def afficher_alerte(niveau, titre, texte):
    st.markdown(f"<div class='alerte-{niveau}'><b>{titre}</b><br>{texte}</div>",
                unsafe_allow_html=True)


def exemples_profil(type_profil):
    """Exemples de messages adaptés au type de profil."""
    if type_profil == "epicerie":
        return [
            "vendu 5000 hier dont 800 à crédit, caisse comptée 4100",
            "acheté 1200 de farine à crédit",
            "payé loyer 1500",
            "client Ahmed a remboursé 300",
            "retrait 500",
        ]
    else:
        return [
            "apport de Mohamed 1000",
            "transformation 800",
            "vendu 3000 d'huile",
            "subvention 5000",
            "cotisation 100",
            "payé transport 200",
        ]


def label_type(type_evt):
    return parse.label_type(type_evt)


# ---------------------------------------------------------------------------
# Profil actif
# ---------------------------------------------------------------------------
profil = get_profil()
if profil:
    set_profil(profil["id"])

# ---------------------------------------------------------------------------
# Barre latérale : navigation (adaptée au profil)
# ---------------------------------------------------------------------------
st.sidebar.title("🧮 MIZAN AI")
st.sidebar.caption("Votre argent, en mots simples.")

if profil:
    st.sidebar.success(
        f"**{profil['nom']}**\n\n{profil['ville']} — "
        + ("Épicerie" if profil["type"] == "epicerie" else "Coopérative")
    )

# 4 écrans identiques pour les deux types, mais le contenu change
ecrans = ["1. Mon profil", "2. Je dis ce qui s'est passé", "3. Mes chiffres", "4. Questions du jour"]
choix = st.sidebar.radio("Aller à :", ecrans)

# ===========================================================================
# ÉCRAN 1 — Mon profil
# ===========================================================================
if choix == ecrans[0]:
    st.title("1. Mon profil")
    st.write("Qui êtes-vous ? C'est tout ce qu'il faut savoir pour commencer.")

    if profil:
        st.markdown(
            f"<div class='carte'>"
            f"<div class='titre'>Profil actuel</div>"
            f"<div class='chiffre'>{profil['nom']}</div>"
            f"<div class='note'>{profil['ville']} — "
            + ("Épicerie" if profil["type"] == "epicerie" else "Coopérative")
            + "</div></div>",
            unsafe_allow_html=True,
        )
        st.write("")

    with st.form("nouveau_profil"):
        st.subheader("Créer un profil")
        nom = st.text_input("Nom de l'épicerie ou de la coopérative")
        type_profil = st.radio("C'est une…", ["Épicerie", "Coopérative"], horizontal=True)
        ville = st.text_input("Ville")
        if st.form_submit_button("Enregistrer ce profil", use_container_width=True):
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
        st.subheader("Changer de profil")
        for p in profils:
            if st.button(f"Utiliser « {p['nom']} »", key=f"p{p['id']}", use_container_width=True):
                set_profil(p["id"])
                st.rerun()

# ===========================================================================
# ÉCRAN 2 — Je dis ce qui s'est passé (avec option audio)
# ===========================================================================
elif choix == ecrans[1]:
    st.title("2. Je dis ce qui s'est passé")
    st.write("Dites-le en quelques mots, comme à un ami. Ou enregistrez un message vocal.")

    if not profil:
        st.info("Créez d'abord un profil dans l'écran 1.")
    else:
        # --- interface séparée selon le profil ---
        type_profil = profil["type"]

        st.write("")
        st.write("**Exemples :**")
        for ex in exemples_profil(type_profil):
            st.caption(f"• {ex}")

        with st.form("saisie"):
            message = st.text_area("Qu'est-ce qui s'est passé ?", height=120,
                                   placeholder="Votre message…")
            envoyer = st.form_submit_button("✅ Enregistrer", use_container_width=True)

        if envoyer and message.strip():
            evt = parse.parse_message(message, type_profil, date.today())

            db.ajouter_evenement(
                conn, profil["id"], evt["date"], evt["type"], evt["montant"],
                evt["tiers"], evt["categorie"], evt["mode"], evt["statut"],
                evt["detail"] or None, message[:80],
            )
            st.success("C'est noté !")

            st.markdown(
                "<div class='carte'>"
                f"<div class='titre'>L'IA a compris</div>"
                f"<div class='chiffre'>{label_type(evt['type'])}</div>"
                f"<div class='note'>"
                f"Date : {evt['date']} — "
                + (f"Montant : {fmt(evt['montant'])}" if evt["montant"] else "Montant : à préciser")
                + (f" — {evt['tiers']}" if evt["tiers"] else "")
                + (" — **À confirmer**" if evt["statut"] == "a_confirmer" else " — Confirmé")
                + "</div></div>",
                unsafe_allow_html=True,
            )

            if evt["question"]:
                st.warning(f"❓ {evt['question']}")

        # --- option audio ---
        st.write("")
        st.subheader("🎤 Ou enregistrer un message vocal")
        audio_path = enregistrer_audio()
        if audio_path:
            st.success(f"Audio enregistré : {os.path.basename(audio_path)}")
            # on crée une entrée « note » qui garde la trace de l'audio
            db.ajouter_evenement(
                conn, profil["id"], date.today().isoformat(), "note", None,
                "", "", "comptant", "a_confirmer", None,
                f"Audio : {os.path.basename(audio_path)}",
            )
            st.info("Tapez ce que vous avez dit pour que l'IA le comprenne, "
                    "ou laissez l'audio comme preuve dans l'historique.")

        # --- Historique complet sous forme de tableau ---
        st.write("")
        st.subheader("Historique complet")
        events = db.lister_evenements(conn, profil["id"])

        if not events:
            st.write("Aucun événement enregistré pour le moment.")
        else:
            lignes = []
            for ev in events:
                lignes.append({
                    "ID": ev["id"],
                    "Date": ev["date"],
                    "Type": label_type(ev["type"]),
                    "Montant (dh)": ev["montant"] if ev["montant"] is not None else None,
                    "Tiers": ev["tiers"] or "",
                    "Catégorie": ev["categorie"] or "",
                    "Mode": ev["mode"],
                    "Statut": "✅ Confirmé" if ev["statut"] == "confirme" else "⚠️ À confirmer",
                    "Note": ev["note"] or "",
                })
            df = pd.DataFrame(lignes)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # --- Suppression ---
            st.subheader("Supprimer une entrée")
            col_input, col_btn = st.columns([3, 1])
            with col_input:
                id_a_supprimer = st.number_input(
                    "Numéro (ID) de la ligne à supprimer :",
                    min_value=1, step=1, key="id_suppr",
                )
            with col_btn:
                st.write("")
                st.write("")
                if st.button("🗑️ Supprimer", key="btn_suppr", use_container_width=True):
                    ev_exists = conn.execute(
                        "SELECT id FROM events WHERE id = ?", (int(id_a_supprimer),)
                    ).fetchone()
                    if ev_exists:
                        supprimer_evenement(int(id_a_supprimer))
                    else:
                        st.error("Aucune entrée avec ce numéro.")

# ===========================================================================
# ÉCRAN 3 — Mes chiffres (dashboard avec alertes)
# ===========================================================================
elif choix == ecrans[2]:
    st.title("3. Mes chiffres")
    st.write("Tout est calculé tout seul, à partir de ce qui a été dit.")

    if not profil:
        st.info("Créez d'abord un profil dans l'écran 1.")
    else:
        events = db.lister_evenements(conn, profil["id"])
        m = engine.compute(events)

        # --- bandeau d'alertes ---
        alertes = calculer_alertes(m, events, profil)
        for niveau, titre, texte in alertes:
            afficher_alerte(niveau, titre, texte)

        st.write("")

        # --- cartes de chiffres (adaptées au profil) ---
        if profil["type"] == "epicerie":
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Vendu (chiffre d'affaires)</div>"
                    f"<div class='chiffre'>{fmt(m['ca'])}</div>"
                    f"<div class='note'>dont {fmt(m['ca_a_confirmer'])} à confirmer</div></div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Encaissé (caisse théorique)</div>"
                    f"<div class='chiffre'>{fmt(m['caisse'])}</div>"
                    f"<div class='note'>ce que la caisse devrait contenir</div></div>",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Compté (caisse réelle)</div>"
                    f"<div class='chiffre'>{fmt(m['comptage'])}</div>"
                    f"<div class='note'>dernier comptage</div></div>",
                    unsafe_allow_html=True,
                )
            col4, col5, col6 = st.columns(3)
            with col4:
                ecart = m["ecart"]
                st.markdown(
                    f"<div class='carte'><div class='titre'>Écart de caisse{' ⚠️' if ecart is not None and abs(ecart) >= 1 else ''}</div>"
                    f"<div class='chiffre'>{fmt(ecart)}</div>"
                    f"<div class='note'>compté − encaissé</div></div>",
                    unsafe_allow_html=True,
                )
            with col5:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Les clients me doivent</div>"
                    f"<div class='chiffre'>{fmt(m['total_creances'])}</div>"
                    f"<div class='note'>créances</div></div>",
                    unsafe_allow_html=True,
                )
            with col6:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Je dois aux fournisseurs</div>"
                    f"<div class='chiffre'>{fmt(m['total_dettes'])}</div>"
                    f"<div class='note'>dettes</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            # coopérative
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Vendu (chiffre d'affaires)</div>"
                    f"<div class='chiffre'>{fmt(m['ca'])}</div>"
                    f"<div class='note'>hors subventions et cotisations</div></div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Encaissé (caisse)</div>"
                    f"<div class='chiffre'>{fmt(m['caisse'])}</div>"
                    f"<div class='note'>tous les encaissements</div></div>",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Hors chiffre d'affaires</div>"
                    f"<div class='chiffre'>{fmt(m['hors_ca'])}</div>"
                    f"<div class='note'>apports, cotisations, subventions</div></div>",
                    unsafe_allow_html=True,
                )
            col4, col5, col6 = st.columns(3)
            with col4:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Dépensé</div>"
                    f"<div class='chiffre'>{fmt(m['charges'])}</div>"
                    f"<div class='note'>achats + dépenses + transformation</div></div>",
                    unsafe_allow_html=True,
                )
            with col5:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Résultat (vendu − dépensé)</div>"
                    f"<div class='chiffre'>{fmt(m['resultat'])}</div>"
                    f"<div class='note'>bénéfice ou perte</div></div>",
                    unsafe_allow_html=True,
                )
            with col6:
                st.markdown(
                    f"<div class='carte'><div class='titre'>Je dois aux fournisseurs</div>"
                    f"<div class='chiffre'>{fmt(m['total_dettes'])}</div>"
                    f"<div class='note'>dettes</div></div>",
                    unsafe_allow_html=True,
                )

        # --- création des listes par tiers ---
        colA, colB = st.columns(2)
        with colA:
            st.subheader("Les clients me doivent")
            if m["creances"]:
                for client, montant in sorted(m["creances"].items(), key=lambda x: -x[1]):
                    st.write(f"• **{client}** : {fmt(montant)}")
            else:
                st.write("Personne ne vous doit rien. 👍")
        with colB:
            st.subheader("Je dois aux fournisseurs")
            if m["dettes"]:
                for fourn, montant in sorted(m["dettes"].items(), key=lambda x: -x[1]):
                    st.write(f"• **{fourn}** : {fmt(montant)}")
            else:
                st.write("Vous ne devez rien aux fournisseurs. 👍")

        # --- graphiques ---
        st.write("")
        st.subheader("Chiffre d'affaires par jour")
        ca_par_jour = {}
        for ev in events:
            if ev["type"] in ("cloture_jour", "vente") and ev["montant"]:
                ca_par_jour[ev["date"]] = ca_par_jour.get(ev["date"], 0) + ev["montant"]
        if ca_par_jour:
            df_ca = pd.DataFrame({"CA (dh)": pd.Series(ca_par_jour)})
            st.bar_chart(df_ca, height=250)
        else:
            st.write("Pas encore de ventes enregistrées.")

        # --- historique des caisses (épicerie uniquement) ---
        if profil["type"] == "epicerie":
            st.write("")
            st.subheader("La caisse, jour par jour")
            lignes = engine.daily_caisse(events)
            if lignes:
                df_caisse = pd.DataFrame(lignes)
                st.dataframe(
                    df_caisse.rename(columns={
                        "date": "Date", "theorique": "Caisse théorique",
                        "comptee": "Caisse comptée", "ecart": "Écart",
                    }),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.write("Pas encore de clôture enregistrée.")

        n = db.compter_a_confirmer(conn, profil["id"])
        if n:
            st.warning(
                f"⚠️ {n} saisie(s) à confirmer. Elles comptent dans les chiffres "
                "mais restent marquées « à confirmer »."
            )

# ===========================================================================
# ÉCRAN 4 — Questions du jour
# ===========================================================================
elif choix == ecrans[3]:
    st.title("4. Questions du jour")
    st.write("L'IA regarde vos chiffres et vous pose 1 ou 2 questions. Réponse en un geste.")

    if not profil:
        st.info("Créez d'abord un profil dans l'écran 1.")
    else:
        events = db.lister_evenements(conn, profil["id"])
        m = engine.compute(events)

        liste = questions.questions_du_jour(
            conn, profil, events, date.today(), creances=m["creances"], max_questions=2
        )

        if not liste:
            st.success("Rien à signaler aujourd'hui. Tout va bien ! ✅")

        for i, q in enumerate(liste):
            st.markdown(
                f"<div class='carte'><div class='chiffre'>❓ {q['texte']}</div></div>",
                unsafe_allow_html=True,
            )
            if q["reponse"]:
                st.success(f"Réponse : {q['reponse']}")
            else:
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("👍 Oui", key=f"o{i}", use_container_width=True):
                        _repondre(profil, q, "oui")
                with col2:
                    if st.button("👎 Non", key=f"n{i}", use_container_width=True):
                        _repondre(profil, q, "non")
                with col3:
                    montant = st.number_input(
                        "Ou un montant en dh :", min_value=0.0, step=50.0, key=f"m{i}"
                    )
                    if st.button("Valider le montant", key=f"v{i}", use_container_width=True):
                        _repondre(profil, q, montant)

# ---------------------------------------------------------------------------
# Pied de page
# ---------------------------------------------------------------------------
st.sidebar.write("")
st.sidebar.caption("MIZAN AI — prototype local, aucune donnée ne quitte votre machine.")
