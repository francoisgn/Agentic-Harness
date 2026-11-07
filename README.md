# agentic-harness

Cadre commun, versionné, pour **encadrer le développement agentique** (Claude Code) dans tous les projets de François :
une même méthode (issues → lots → PR), les mêmes garde-fous, les mêmes leçons, la même taxonomie de labels et les mêmes
contrôles GitHub, récupérés par chaque projet à une version donnée et mis à jour par PR.

Né de deux projets réels : **HFRnow** (client iOS SwiftHFR, branche `dev-swift` : orchestration multi-sessions, revues
adversariales, 57 leçons) et **ios-app_credit-immo** (simulateur de crédit : workflow piloté par les issues, labels
modèle/taille, budget CI, reprise sur Mac). Ce qui est propre à leur domaine (protocole HFR, calcul de crédit) est resté
chez eux ; le reste est ici, traduit et généralisé.

## Contenu

| Chemin | Rôle |
|---|---|
| [`docs/ESSENTIEL.md`](docs/ESSENTIEL.md) | Les règles chargées à chaque session (importées par le `CLAUDE.md` du projet) |
| [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) | Boucle pilotée par les issues, lots, parapluies de retours, labels |
| [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) | Commits, PR, commentaires GitHub, persistance compatible, version et Nouveautés |
| [`docs/LESSONS.md`](docs/LESSONS.md) | 82 leçons fusionnées, par portée (général, swift, ios, linux-cloud, ci, docs), sources citées |
| [`docs/ORCHESTRATION.md`](docs/ORCHESTRATION.md) | Sessions parallèles, sous-agents, choix du modèle, revue adversariale, worktrees |
| [`docs/REVIEW-ROUNDS.md`](docs/REVIEW-ROUNDS.md) | Traiter un cycle de revue (bots, humains) une fois, complètement |
| [`docs/BRANCHING-RELEASE.md`](docs/BRANCHING-RELEASE.md) | Modèles de branches, promotions, hotfix, semver et tags |
| [`docs/CI-BUDGET.md`](docs/CI-BUDGET.md) | Facturation des minutes, règles d'économie, socle de sécurité gratuit |
| [`docs/MAC-HANDOFF.md`](docs/MAC-HANDOFF.md) | Cloud Linux et Mac : partage des rôles, script de reprise, sessions Mac autonomes |
| [`docs/ADOPTION.md`](docs/ADOPTION.md) | Adopter, régler, mettre à jour, retirer |
| [`docs/adr/`](docs/adr/README.md) | Décisions du cadre (0001 : mécanisme de distribution) et gabarit d'ADR |
| `templates/` | Gabarits vendorisés : bloc `CLAUDE.md`/`AGENTS.md`, labels, formulaires d'issue, PR, lot, workflows appelants |
| `i18n/en/` | Édition anglaise des fichiers chargés à chaque session (`language: "en"`) |
| `plugins/harness/` | Plugin Claude Code : skills `lot-start`, `lot-finish`, `review-round`, `feedback-triage`, `lessons-check`, `harness-update` ; hooks `guard-git` et rappel de session |
| `.claude-plugin/marketplace.json` | Ce dépôt est une marketplace Claude Code (`agentic-harness`) |
| `.github/workflows/` | Workflows réutilisables (`workflow_call`) : `labels-sync`, `issue-hygiene`, `pr-hygiene`, `docs-security` ; `ci.yml` du cadre |
| [`scripts/harness-sync.sh`](scripts/harness-sync.sh) + `harness.manifest` | Vendorise le cadre dans un projet, à une version, sans toucher à ce qui est au projet |

## Comment un projet l'utilise
Trois canaux, une source ([ADR 0001](docs/adr/0001-mecanisme-de-distribution.md)) :
1. **Vendorisation** (principal, marche aussi en session cloud) : `scripts/harness-sync.sh` copie docs, labels, skills et
   hooks dans le projet (`.harness/`, `.claude/`) et gère un bloc balisé dans `CLAUDE.md` qui importe `ESSENTIEL.md`.
2. **Plugin** `harness@agentic-harness` pour les sessions locales et les dépôts pas encore adoptés :
   `/plugin install harness --marketplace francoisgn/agentic-harness` (Claude Code ≥ 2.1.275), ou
   `claude plugin marketplace add francoisgn/agentic-harness && claude plugin install harness@agentic-harness`.
3. **Workflows réutilisables** appelés par un `harness.yml` fin dans le projet (labels, hygiène des issues et PR,
   sécurité), plus une PR hebdomadaire de mise à jour (`harness-sync.yml`).

Adopter en trois commandes (détail, réglages et cas HFRnow : [ADOPTION](docs/ADOPTION.md)) :
```bash
git clone --depth 1 --branch v0.1.0 https://github.com/francoisgn/agentic-harness.git ../agentic-harness
../agentic-harness/scripts/harness-sync.sh --target . --dry-run
../agentic-harness/scripts/harness-sync.sh --target .
```

## Versions
- Semver, tags `vX.Y.Z` sur `main` ; [CHANGELOG](CHANGELOG.md) tenu à chaque version ; `VERSION`,
  `plugins/harness/.claude-plugin/plugin.json` (`version`) avancent ensemble (contrôlé par la CI). Sans changement de
  `version`, les utilisateurs du plugin ne reçoivent pas les nouveaux commits.
- MAJEUR : un projet doit agir (fichier déplacé, règle qui change un usage, format de `.harness/lock`) ; MINEUR : ajout
  (doc, skill, leçon, workflow) ; CORRECTIF : correction. Avant 1.0.0, un MINEUR peut casser : le CHANGELOG le dit.
- Une leçon née dans un projet et valable ailleurs remonte ici par PR ; numéros `L..` stables.

## Contribuer au cadre
Même méthode que les projets : une issue, une branche `claude/<sujet>`, une PR vers `main`, `scripts/tests/test-harness-sync.sh`
et la CI verts. Release : PR « Version : passe en X.Y.Z » (VERSION + plugin.json + CHANGELOG), puis tag `vX.Y.Z` par
François.
