"""Accès à la base SQLite de MIZAN AI.

Une seule base, un seul journal d'événements. Rien d'autre n'est stocké.
"""
import os
import sqlite3
from datetime import datetime

# La base vit à la racine du projet, à côté de app.py
DOSSIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DOSSIER, "mizan.db")


def connect():
    """Ouvre une connexion SQLite (les lignes redeviennent des dictionnaires)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée les tables si elles n'existent pas."""
    conn = connect()
    c = conn.cursor()

    # 1) Les profils (une épicerie ou une coopérative)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nom         TEXT NOT NULL,
            type        TEXT NOT NULL CHECK (type IN ('epicerie', 'cooperative')),
            ville       TEXT,
            cree_le     TEXT
        )
        """
    )

    # 2) Le journal d'événements. C'est LA source de tous les chiffres.
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,              -- AAAA-MM-JJ
            type        TEXT NOT NULL,              -- voir engine.EVENT_TYPES
            montant     REAL,                       -- NULL = saisie incomplète
            tiers       TEXT,                       -- client, fournisseur, adhérent...
            categorie   TEXT,                       -- loyer, electricite, farine...
            mode        TEXT,                       -- 'comptant' ou 'credit'
            statut      TEXT NOT NULL DEFAULT 'confirme',  -- 'confirme' / 'a_confirmer'
            detail      TEXT,                       -- infos en plus, en JSON
            note        TEXT,
            cree_le     TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles (id)
        )
        """
    )

    # 3) Les réponses aux « questions du jour »
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS questions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id  INTEGER NOT NULL,
            date        TEXT NOT NULL,              -- jour concerné (AAAA-MM-JJ)
            regle       TEXT NOT NULL,              -- quelle règle a posé la question
            texte       TEXT NOT NULL,
            reponse     TEXT,                       -- 'oui' / 'non' / un montant
            cree_le     TEXT
        )
        """
    )

    # 4) Les notes audio (stockées dans la base pour ne pas être perdues)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS audios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id  INTEGER NOT NULL,
            nom         TEXT,
            donnees     BLOB NOT NULL,
            cree_le     TEXT,
            FOREIGN KEY (profile_id) REFERENCES profiles (id)
        )
        """
    )

    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Profils
# ---------------------------------------------------------------------------
def lister_profils(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM profiles ORDER BY id")]


def creer_profil(conn, nom, type_profil, ville=""):
    cur = conn.execute(
        "INSERT INTO profiles (nom, type, ville, cree_le) VALUES (?, ?, ?, ?)",
        (nom, type_profil, ville, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return cur.lastrowid


def profil_par_id(conn, profil_id):
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profil_id,)).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Événements
# ---------------------------------------------------------------------------
def ajouter_evenement(conn, profil_id, date, type_evt, montant=None, tiers="",
                      categorie="", mode="comptant", statut="confirme",
                      detail=None, note=""):
    import json
    cur = conn.execute(
        """
        INSERT INTO events
            (profile_id, date, type, montant, tiers, categorie, mode, statut, detail, note, cree_le)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (profil_id, date, type_evt, montant, tiers or None, categorie or None,
         mode, statut, json.dumps(detail) if detail else None, note or None,
         datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return cur.lastrowid


def lister_evenements(conn, profil_id):
    rows = conn.execute(
        "SELECT * FROM events WHERE profile_id = ? ORDER BY date, id", (profil_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def compter_a_confirmer(conn, profil_id):
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE profile_id = ? AND statut = 'a_confirmer'",
        (profil_id,),
    ).fetchone()
    return row["n"]


# ---------------------------------------------------------------------------
# Questions du jour
# ---------------------------------------------------------------------------
def question_existe(conn, profil_id, date, regle):
    row = conn.execute(
        "SELECT * FROM questions WHERE profile_id = ? AND date = ? AND regle = ?",
        (profil_id, date, regle),
    ).fetchone()
    return dict(row) if row else None


def ajouter_question(conn, profil_id, date, regle, texte):
    cur = conn.execute(
        "INSERT INTO questions (profile_id, date, regle, texte, cree_le) VALUES (?, ?, ?, ?, ?)",
        (profil_id, date, regle, texte, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return cur.lastrowid


def repondre_question(conn, question_id, reponse):
    conn.execute(
        "UPDATE questions SET reponse = ? WHERE id = ?", (str(reponse), question_id)
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Notes audio
# ---------------------------------------------------------------------------
def ajouter_audio(conn, profil_id, nom, donnees):
    """Enregistre un audio dans la base et retourne son identifiant."""
    cur = conn.execute(
        "INSERT INTO audios (profile_id, nom, donnees, cree_le) VALUES (?, ?, ?, ?)",
        (profil_id, nom, donnees, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    return cur.lastrowid


def lister_audios(conn, profil_id):
    """Liste les audios sans charger leur contenu (seulement la taille)."""
    rows = conn.execute(
        "SELECT id, nom, cree_le, length(donnees) AS taille "
        "FROM audios WHERE profile_id = ? ORDER BY id DESC",
        (profil_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def obtenir_audio(conn, audio_id):
    """Retourne l'audio complet (avec ses données binaires)."""
    row = conn.execute("SELECT * FROM audios WHERE id = ?", (audio_id,)).fetchone()
    return dict(row) if row else None


def supprimer_audio(conn, audio_id):
    conn.execute("DELETE FROM audios WHERE id = ?", (audio_id,))
    conn.commit()
