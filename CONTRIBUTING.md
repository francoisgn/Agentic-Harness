# Contribuer à agentic-harness

Le cadre est une boîte à outils, pas une doctrine : chaque brique doit pouvoir se garder, se remplacer ou se couper.
Une contribution qui ajoute une règle dit aussi comment la désactiver.

## En bref

1. **Une issue d'abord**, avec son intention : l'échec observé dans un vrai projet, ce que la brique change, comment
   on saura que c'est fini. Une leçon née dans votre projet : formulaire « Leçon ».
2. **Une branche** depuis `master` à jour ; commits atomiques, en français, dans le style de `git log`.
3. **Contrôles en local** (les mêmes que la CI, un job Linux) :
   ```bash
   python3 scripts/check-framework.py && python3 -m unittest discover -s scripts/tests -p 'test_*.py' \
     && scripts/tests/test-harness-sync.sh && python3 scripts/diagrams/render.py --check \
     && python3 scripts/readme-check.py
   ```
4. **Une PR en brouillon**, puis « Ready for review » quand tout est fini et relu par un autre modèle que l'auteur.
   Rien ne tourne en CI sur un brouillon.

## Ce qu'une PR garde vrai

| Vous touchez | À mettre à jour dans la même PR |
|---|---|
| Un skill, un agent | `name` = dossier ou fichier, `description` ; le compte et la table du README ; `templates/CLAUDE.md.block` |
| Un fichier vendorisé | `harness.manifest` ; un test dans `scripts/tests/test-harness-sync.sh` si le mode est nouveau |
| Un script | Bibliothèque standard seulement ; un test `scripts/tests/test_*.py` vu en échec sans le changement |
| Un schéma | `docs/diagrams/<nom>.json`, puis `scripts/diagrams/render.py` ; commiter `.json`, `.svg`, `.excalidraw` |
| Un label | `templates/.github/labels.json` (nom unique, axe) ; `docs/METHODOLOGY.md` |
| Une règle chargée à chaque session | `docs/ESSENTIEL.md` **et** `i18n/en/docs/ESSENTIEL.md` ; rester court |
| Un comportement visible d'un projet | `CHANGELOG.md`, ligne « Action » si le projet doit faire quelque chose |

## Ce qui n'entre pas

- Une règle sans échec observé derrière elle, ou qui ne se coupe pas.
- Une dépendance (paquet Python, action tierce non épinglée par SHA, compte tiers obligatoire).
- Un nom de personne, de client ou de projet privé ; un secret, même factice mais plausible.

## Signaler une faille

Jamais dans une issue publique : onglet **Security** › *Report a vulnerability* du dépôt.
