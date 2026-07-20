# Machronologie

Une chronologie des actions et annonces d'Emmanuel Macron et de ses
gouvernements depuis 2017, reconstituée à partir d'une archive personnelle de
réseaux sociaux.

**Le site :** https://zevinci.github.io/machronologie/

Ce n'est pas un bilan exhaustif des deux quinquennats. C'est une sélection
subjective assumée. Chaque fiche décrit un fait sourcé, puis restitue,
dans un registre typographiquement distinct, la critique qui lui a été faite
à l'époque. Les deux ne sont jamais mélangés.

## Organisation

```
sources/          les chronologies annuelles, une par année — le contenu réel
page.md           titre, chapô et note de pied de page du site
methode.md        contenu du panneau « Méthode »
apropos.md        contenu du panneau « Qui suis-je »
build_json.py     lit tout ce qui précède et produit docs/
docs/             le site publié par GitHub Pages — généré, ne pas éditer
```

## Régénérer le site

```bash
python build_json.py
```

Aucune dépendance externe. Le script lit les `sources/*.md`, normalise les
dates, calcule la densité mensuelle, puis écrit `chronologie.json`,
`chronologie.js` et le dossier `docs/` prêt à publier. Il signale en fin
d'exécution toute fiche dont la date résiste à l'analyse ou dont la source
manque.

`docs/` est entièrement dérivé : toute modification s'y perd au build suivant.
Pour changer le contenu, éditer les `.md`.

## Format d'une fiche

```markdown
## 4. Un gouvernement à forte coloration de droite
**Date : 17/05/2017**

Description factuelle, vérifiable, deux à six phrases.

*Prisme critique — La lecture critique, une à trois phrases.*

Sources : [Légifrance](https://…) · [Vie-publique.fr](https://…)
```

Le champ `Date` accepte le texte lisible : `17/05/2017`, `janvier 2024`,
`mars–juin 2021`, `08/07 – 07/08/2025`, `2018 – 2023`. Le script en déduit une
date de début, une date de fin et une précision. Une fiche dont l'empan
dépasse six mois est traitée comme transverse et présentée en tête de son
année plutôt que dans le fil mensuel.

Une fiche peut citer plusieurs sources, séparées par un point médian, un
point-virgule ou une virgule.

## Sources privilégiées

Le Monde, AFP, Mediapart, sites officiels (Légifrance, INSEE, DREES,
gouvernement), franceinfo, LCP, Public Sénat. Un point qui ne repose que sur
une opinion invérifiable est écarté plutôt que faiblement sourcé.
