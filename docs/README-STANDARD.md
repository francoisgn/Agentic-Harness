# Le README du projet : standard par défaut

**TL;DR** : par défaut, les agents tiennent le README du projet comme un livrable. Il porte six choses : des tuiles
technologiques en en-tête, une image du produit, un schéma d'architecture (Excalidraw), l'avancement des lots, le
démarrage, et comment contribuer. Un script le contrôle, un skill le met à jour, chaque point se coupe.

Pourquoi : le README est la seule page que lisent à la fois l'opérateur, un nouveau contributeur et un agent qui
arrive sans contexte. Un README périmé fait repartir chaque session de zéro ; un README tenu à la fin de chaque lot
coûte quelques lignes par PR.

## 1. Ce que le README contient

| # | Élément | Règle | Contrôlé |
|---|---|---|---|
| 1 | **En-tête** | Titre, puis les **tuiles technologiques** (langage, framework, plateforme, CI, licence), puis une phrase : ce que fait le produit, pour qui | au moins une tuile avant le premier `##` |
| 2 | **Image** | Une capture ou une image du produit en service, avec un texte alternatif | une image hors tuiles ; alt présent ; fichier local présent |
| 3 | **Architecture** | Un schéma de ce qui est livré : `docs/diagrams/architecture.svg`, source `.excalidraw` versionnée à côté | image `.svg` + `.excalidraw` du même nom |
| 4 | **Avancement** | Un tableau, une ligne par lot (ou jalon), entre les marqueurs `harness:begin avancement` / `harness:end avancement` | marqueurs, tableau, chaque `LOT-…` de `docs/LOTS.md` cité |
| 5 | **Démarrage** | Les commandes exactes pour installer, lancer, tester | une section d'installation ou de démarrage |
| 6 | **Contribuer** | Une section courte qui renvoie à `CONTRIBUTING.md` (issue, branche, contrôles, PR, revue) | section présente, fichier présent, lien |

Ordre libre après l'en-tête. Le reste (FAQ, feuille de route, crédits) appartient au projet.

## 2. Tuiles technologiques

- Une tuile par brique **réellement utilisée**, lue dans les manifestes du projet, version comprise. Pas de tuile
  décorative, pas plus d'une ligne.
- Format : `https://img.shields.io/badge/<nom>-<version>-<couleur>?logo=<slug>&logoColor=white` (slugs :
  simpleicons.org).
- Une tuile d'**état** (CI, dernière version, couverture) pointe vers une source vivante (badge du workflow GitHub,
  release) : jamais un chiffre écrit à la main, il serait faux au commit suivant.

## 3. Avancement des lots

```markdown
<!-- harness:begin avancement -->
| Lot | Périmètre | État | Issue / PR |
|---|---|---|---|
| LOT-001 | Moteur de calcul | 🟢 livré | #12 · #31 |
| LOT-002 | Écran de saisie | 🔵 en cours | #14 |
<!-- harness:end avancement -->
```

- États : ⚪ à faire · 🔵 en cours · 🟠 en revue · 🔴 bloqué · 🟢 livré.
- La **source de vérité reste l'issue** ([METHODOLOGY](METHODOLOGY.md)) : le tableau en est une vue, réécrite à la
  fin de chaque lot (`/lot-finish` → `/readme-update`) à partir de l'état relu sur GitHub. `docs/LOTS.md` reste le
  plan et ne change pas pour un avancement.
- Sans plan de lots : une ligne par jalon GitHub (milestone), ou par capacité du produit.
- Deux lots parallèles touchent le même tableau : chacun ne modifie que sa ligne, pour éviter le conflit.

## 4. Schéma d'architecture : Excalidraw par défaut

Excalidraw parce que le schéma se lit par un humain non technique, se modifie à la souris sur excalidraw.com, et que
sa source est un JSON versionné que la CI sait rendre et contrôler.

| Fichier | Rôle |
|---|---|
| `docs/diagrams/<nom>.json` | Source : liste d'éléments (rectangle, ellipse, texte, flèche, `label`) |
| `docs/diagrams/<nom>.svg` | Image affichée dans le README, rendu déterministe |
| `docs/diagrams/<nom>.excalidraw` | Scène native, à ouvrir sur excalidraw.com |

```bash
python3 .harness/scripts/diagrams-render.py            # rend docs/diagrams/*.json
python3 .harness/scripts/diagrams-render.py --check    # CI : sort en 1 si un rendu est périmé ou un texte déborde
```

Les trois fichiers se commitent ensemble. Le schéma montre **ce qui est livré** ; 5 à 9 boîtes. Mermaid reste permis
pour un flux court dans une doc interne ; pour le README, `"architecture": "any"` l'accepte aussi.

## 5. Qui le tient, et quand

| Moment | Qui | Quoi |
|---|---|---|
| Adoption | `harness-sync.sh` | Crée `README.md`, `CONTRIBUTING.md` et `docs/diagrams/architecture.*` **s'ils n'existent pas** ; ne les réécrit jamais ensuite |
| Fin de lot | l'agent du lot (`/lot-finish`, étape 2) | `/readme-update` : ligne du lot, tuiles, schéma si l'architecture a bougé |
| Après un merge, chaque semaine | `doc-steward` | Compare README et code mergé, ouvre une PR de docs |
| Chaque PR prête | CI (`docs-security.yml`, entrée `readme`) | `readme-check.py` + `diagrams-render.py --check` |

## 6. Régler ou couper

Dans `.harness/config.json` ; absent = tout actif.

```json
"readme": { "badges": true, "image": true, "architecture": "excalidraw", "progress": true,
            "quickstart": true, "contributing": true }
```

- Une clé à `false` coupe le point. `"architecture": "any"` accepte une image quelconque ou un bloc Mermaid.
- `"readme": false` coupe tout (dépôt de configuration, bibliothèque interne sans lots).
- Un README déjà en place n'est pas remplacé : `readme-check.py` liste les écarts, le projet choisit ce qu'il comble.
