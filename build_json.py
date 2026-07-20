#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_json.py — genere chronologie.json a partir des fichiers sources.

Organisation attendue du dossier :

  timeline.html
  build_json.py
  page.md          titre, chapo, note de pied de page
  methode.md       panneau « Methode », optionnel
  apropos.md       panneau « Qui suis-je », optionnel
  sources/
      20NN_Chronologie_sourcee.md    contenu des fiches

Si le dossier sources/ n'existe pas, les chronologies sont cherchees a cote
du script.

Le script ne modifie jamais les sources. Il n'invente aucune donnee :
tout champ absent reste vide et est signale dans le rapport de fin.

Usage :  python build_json.py
Aucune dependance externe.
"""

import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parent
SORTIE = RACINE / "chronologie.json"
ANNEES = range(2017, 2026)

# Les chronologies annuelles vivent dans sources/. Si ce dossier n'existe
# pas, on retombe sur le dossier du script : le projet reste fonctionnel
# quelle que soit l'organisation.
SOURCES = RACINE / "sources" if (RACINE / "sources").is_dir() else RACINE

# Au-dela de ce nombre de jours, une fiche est consideree comme couvrant
# une periode trop large pour etre placee dans le flux mensuel : elle
# devient "transverse" et s'affiche en tete de son annee.
SEUIL_TRANSVERSE = 180

MOIS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10,
    "novembre": 11, "decembre": 12,
    "janv": 1, "fev": 2, "avr": 4, "juil": 7, "sept": 9, "oct": 10,
    "nov": 11, "dec": 12,
}

SAISONS = {
    "hiver": (1, 3), "printemps": (4, 6), "ete": (7, 9), "automne": (10, 12),
}

avertissements = []


def sans_accents(s):
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


def fin_de_mois(a, m):
    return date(a + (m == 12), 1 if m == 12 else m + 1, 1) - timedelta(days=1)


def jour_sur(a, m, j):
    """Construit une date en bornant le jour au dernier jour du mois."""
    dernier = fin_de_mois(a, m).day
    return date(a, m, min(j, dernier))


def normaliser_date(libelle, annee_fichier):
    """
    Traduit un libelle de date lisible en (debut, fin, precision).
    precision : 'jour' | 'periode' | 'mois' | 'annee' | None
    Retourne (None, None, None) si le libelle resiste a l'analyse.
    """
    t = sans_accents(libelle)
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    t = t.replace("&", "-").replace("/", "-") if False else t
    t = re.sub(r"\s+", " ", t).strip()

    # 1. jj/mm/aaaa - jj/mm/aaaa  (periode inter-annuelle ou longue)
    m = re.search(
        r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})\s*-\s*(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        j1, m1, a1, j2, m2, a2 = map(int, m.groups())
        return jour_sur(a1, m1, j1), jour_sur(a2, m2, j2), "periode"

    # 2. jj/mm - jj/mm/aaaa   (periode intra-annuelle, annee en fin)
    m = re.search(
        r"(\d{1,2})[/.](\d{1,2})\s*-\s*(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        j1, m1, j2, m2, a = map(int, m.groups())
        a1 = a - 1 if m1 > m2 else a
        return jour_sur(a1, m1, j1), jour_sur(a, m2, j2), "periode"

    # 3. jj-jj/mm/aaaa  ou  jj & jj/mm/aaaa  (jours dans un meme mois)
    m = re.search(r"(\d{1,2})\s*[-&]\s*(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        j1, j2, mo, a = map(int, m.groups())
        return jour_sur(a, mo, j1), jour_sur(a, mo, j2), "periode"

    # 4. jj/mm/aaaa  (jour unique)
    m = re.search(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", t)
    if m:
        j, mo, a = map(int, m.groups())
        d = jour_sur(a, mo, j)
        return d, d, "jour"

    # 5. mois - mois aaaa   (ex. "avril-mai 2018", "aout-dec. 2020")
    noms = "|".join(sorted(MOIS, key=len, reverse=True))
    m = re.search(rf"\b({noms})\.?\s*-\s*({noms})\.?\s*(\d{{4}})", t)
    if m:
        m1, m2, a = MOIS[m.group(1)], MOIS[m.group(2)], int(m.group(3))
        return date(a, m1, 1), fin_de_mois(a, m2), "mois"

    # 6. mois aaaa - mois aaaa  (ex. "mai 2023 / mars 2024")
    m = re.search(rf"\b({noms})\.?\s*(\d{{4}})\s*[-/]\s*({noms})\.?\s*(\d{{4}})", t)
    if m:
        m1, a1 = MOIS[m.group(1)], int(m.group(2))
        m2, a2 = MOIS[m.group(3)], int(m.group(4))
        return date(a1, m1, 1), fin_de_mois(a2, m2), "mois"

    # 7. saison aaaa
    m = re.search(rf"\b({'|'.join(SAISONS)})\s*(\d{{4}})", t)
    if m:
        d1, d2 = SAISONS[m.group(1)]
        a = int(m.group(2))
        return date(a, d1, 1), fin_de_mois(a, d2), "mois"

    # 8. mois aaaa  (mois unique)
    m = re.search(rf"\b({noms})\.?\s*(\d{{4}})", t)
    if m:
        mo, a = MOIS[m.group(1)], int(m.group(2))
        return date(a, mo, 1), fin_de_mois(a, mo), "mois"

    # 9. aaaa - aaaa  (empan pluriannuel)
    m = re.search(r"\b(\d{4})\s*-\s*(\d{4})\b", t)
    if m:
        a1, a2 = int(m.group(1)), int(m.group(2))
        return date(a1, 1, 1), date(a2, 12, 31), "annee"

    # 10. aaaa (annee) / aaaa (toute l'annee)
    m = re.search(r"\b(\d{4})\b", t)
    if m:
        a = int(m.group(1))
        return date(a, 1, 1), date(a, 12, 31), "annee"

    return None, None, None


BLOC = re.compile(
    r"^## (\d+)\.\s*(.+?)\n"          # numero + titre
    r"\*\*Date\s*:\s*(.+?)\*\*\n"     # date
    r"(.*?)"                          # corps
    r"(?=^## |\Z)",
    re.S | re.M,
)
PRISME = re.compile(r"^\*Prisme critique\s*[—-]\s*(.+?)\*\s*$", re.S | re.M)

# Une fiche peut citer plusieurs sources. Sont acceptes :
#   Source : [Le Monde](url)
#   Sources : [Le Monde](url) ; [Mediapart](url)
#   Sources : [Le Monde](url), [AFP](url)
# ainsi que plusieurs lignes « Source : » successives.
# Un nom sans lien reste une source valide, simplement non cliquable.
LIGNE_SOURCE = re.compile(r"^Sources?\s*:\s*(.+)$", re.M)
LIEN_MD = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")


def lire_annee(annee):
    chemin = SOURCES / f"{annee}_Chronologie_sourcee.md"
    if not chemin.exists():
        avertissements.append(f"{annee} : fichier .md absent, annee ignoree")
        return None

    brut = chemin.read_text(encoding="utf-8")

    # La section "Points mis de cote" n'est pas de la chronologie : on la coupe.
    coupe = re.search(r"^## Points mis de c[oô]t[eé]", brut, re.M)
    if coupe:
        brut = brut[:coupe.start()]

    lignes = brut.split("\n")
    note = ""
    for ligne in lignes[1:6]:
        if ligne.startswith("*") and ligne.rstrip().endswith("*"):
            intro = ligne.strip().strip("*").strip()
            phrases = re.split(r"(?<=\.)\s+", intro)
            note = phrases[-1].strip() if phrases else ""
            break

    fiches = []

    for m in BLOC.finditer(brut):
        num = int(m.group(1))
        titre = m.group(2).strip()
        libelle = m.group(3).strip()
        corps = m.group(4)

        p = PRISME.search(corps)
        critique = re.sub(r"\s+", " ", p.group(1)).strip() if p else ""
        if not p:
            avertissements.append(f"{annee} #{num} : prisme critique introuvable")

        sources = []
        for ligne in LIGNE_SOURCE.findall(corps):
            liens = LIEN_MD.findall(ligne)
            if liens:
                for nom, url in liens:
                    sources.append({"nom": nom.strip(), "lien": url.strip()})
            else:
                nu = ligne.strip().rstrip(";,.")
                if nu:
                    sources.append({"nom": nu, "lien": ""})
                    avertissements.append(
                        f"{annee} #{num} : source sans lien « {nu[:40]} »")
        if not sources:
            avertissements.append(f"{annee} #{num} : source introuvable")

        corps_sans = corps
        if p:
            corps_sans = corps_sans[:p.start()] + corps_sans[p.end():]
        corps_sans = LIGNE_SOURCE.sub("", corps_sans)
        factuel = "\n\n".join(
            re.sub(r"\s+", " ", b).strip()
            for b in corps_sans.split("\n\n") if b.strip()
        )

        debut, fin, precision = normaliser_date(libelle, annee)
        if debut is None:
            avertissements.append(
                f"{annee} #{num} : date non analysee « {libelle} »")

        etendue = (fin - debut).days if debut and fin else 0
        transverse = bool(debut) and etendue > SEUIL_TRANSVERSE
        mois = None if (transverse or not debut) else (
            debut.month if debut.year == annee else 1)


        fiches.append({
            "n": num,
            "titre": titre,
            "date_libelle": libelle,
            "debut": debut.isoformat() if debut else None,
            "fin": fin.isoformat() if fin else None,
            "precision": precision,
            "transverse": transverse,
            "mois": mois,
            "factuel": factuel,
            "critique": critique,
            "sources": sources,
        })

    fiches.sort(key=lambda f: f["n"])

    densite = [0] * 12
    for f in fiches:
        if f["mois"]:
            densite[f["mois"] - 1] += 1

    return {
        "annee": annee,
        "note": note,
        "total": len(fiches),
        "densite": densite,
        "fiches": fiches,
    }


def lire_page(nom):
    """Charge une page secondaire optionnelle. Absente ou vide => None."""
    chemin = RACINE / f"{nom}.md"
    if not chemin.exists():
        return None
    texte = chemin.read_text(encoding="utf-8").strip()
    return texte or None


# Textes de la page, utilises si page.md est absent ou incomplet.
TEXTES_DEFAUT = {
    "titre": "Ce que Macron a fait, année après année",
    "chapo": "",
    "pied": "",
}


def lire_textes():
    """
    Lit page.md, qui pilote les textes editoriaux de la page :

        # Titre de la page

        Paragraphe(s) de presentation.

        ---

        Note de pied de page.

    Chaque partie est facultative. Le fichier peut etre edite librement
    sans toucher au HTML.

    Dans le titre, ce qui est entoure de ** s'affiche en encre foncee, le
    reste en gris. C'est ce qui fait ressortir un mot dans un mot :

        # **Mac**h**ron**ologie

    donne « Mac » et « ron » en fonce, « h » et « ologie » en gris.
    Sans aucun **, le titre s'affiche uniformement en encre foncee.
    Les balises sont retirees du titre de l'onglet et des apercus de partage.
    """
    chemin = RACINE / "page.md"
    if not chemin.exists():
        avertissements.append("page.md absent : textes par defaut utilises")
        return dict(TEXTES_DEFAUT)

    brut = chemin.read_text(encoding="utf-8").strip()
    haut, _, bas = brut.partition("\n---")

    titre_balise = ""
    m = re.search(r"^#\s+(.+)$", haut, re.M)
    if m:
        titre_balise = m.group(1).strip()
        haut = haut[:m.start()] + haut[m.end():]

    titre_balise = titre_balise or TEXTES_DEFAUT["titre"]
    # Version nue, pour l'onglet, les moteurs de recherche et les partages.
    titre_nu = re.sub(r"\*\*(.+?)\*\*", r"\1", titre_balise).strip()

    return {
        "titre": titre_nu,
        "titre_balise": titre_balise,
        "chapo": haut.strip(),
        "pied": bas.lstrip("-").strip(),
    }


def publier(textes):
    """
    Prepare docs/, le dossier publie par GitHub Pages.

    GitHub Pages n accepte comme source que la racine du depot ou un dossier
    nomme exactement docs/ : ce nom n est pas un choix esthetique.

    Ne contient que la page et ses donnees : aucun fichier de travail,
    aucune archive personnelle. Le titre et la description issus de page.md
    sont injectes dans le HTML pour que les moteurs de recherche et les
    apercus de partage les voient sans executer de JavaScript.
    """
    site = RACINE / "docs"
    site.mkdir(exist_ok=True)

    html = (RACINE / "timeline.html").read_text(encoding="utf-8")

    titre = textes.get("titre", "")
    desc = re.sub(r"\s+", " ", re.sub(r"[*_#\[\]]|\(https?://[^)]*\)",
                                      "", textes.get("chapo", ""))).strip()
    if len(desc) > 300:
        desc = desc[:297].rsplit(" ", 1)[0] + "…"

    def att(balise, valeur):
        return balise.split('content="')[0] + 'content="' + \
               valeur.replace('"', "&quot;") + '">'

    if titre:
        html = re.sub(r"<title>.*?</title>",
                      "<title>" + titre + "</title>", html, count=1)
        html = re.sub(r'<meta property="og:title" content="[^"]*">',
                      lambda m: att(m.group(0), titre), html, count=1)
    if desc:
        html = re.sub(r'<meta name="description" content="[^"]*">',
                      lambda m: att(m.group(0), desc), html, count=1)
        html = re.sub(r'<meta property="og:description" content="[^"]*">',
                      lambda m: att(m.group(0), desc), html, count=1)

    (site / "index.html").write_text(html, encoding="utf-8")
    for f in ("chronologie.js", "chronologie.json"):
        (site / f).write_text(
            (RACINE / f).read_text(encoding="utf-8"), encoding="utf-8")

    # Empeche GitHub Pages de faire passer les fichiers par Jekyll.
    (site / ".nojekyll").write_text("", encoding="utf-8")

    return site


def main():
    annees = [a for a in (lire_annee(y) for y in ANNEES) if a]
    total = sum(a["total"] for a in annees)

    donnees = {
        "genere_le": date.today().isoformat(),
        "total_fiches": total,
        "textes": lire_textes(),
        "annees": annees,
        "pages": {
            "methode": lire_page("methode"),
            "apropos": lire_page("apropos"),
        },
    }

    brut = json.dumps(donnees, ensure_ascii=False, indent=1)
    SORTIE.write_text(brut, encoding="utf-8")

    # Double sortie : le .json est la donnee de reference, le .js permet
    # d'ouvrir timeline.html par simple double-clic (file:// interdit fetch).
    (RACINE / "chronologie.js").write_text(
        "window.DONNEES = " + brut + ";\n", encoding="utf-8")

    ou = SOURCES.name + "/" if SOURCES != RACINE else "dossier courant"
    print(f"chronologie.json ecrit — {total} fiches, {len(annees)} annees"
          f" (sources lues dans : {ou})")
    for a in annees:
        tr = sum(1 for f in a["fiches"] if f["transverse"])
        print(f"  {a['annee']} : {a['total']:>3} fiches"
              f"{f' · {tr} transverse(s)' if tr else ''}")

    site = publier(donnees["textes"])
    print(f"  docs/ pret a publier — {sum(f.stat().st_size for f in site.iterdir()) // 1024} Ko")

    for p, contenu in donnees["pages"].items():
        if contenu is None:
            print(f"  page « {p} » : vide, l'entree de menu ne s'affichera pas")

    if avertissements:
        print(f"\n{len(avertissements)} avertissement(s) :")
        for a in avertissements:
            print(f"  - {a}")
    else:
        print("\nAucun avertissement.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
