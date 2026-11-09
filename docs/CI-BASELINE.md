# Socle de CI : ce que tout projet a, par paliers

**TL;DR** : cinq paliers, du gratuit au cher. Le palier 0 vaut pour tout dépôt, même un dépôt de configuration ; les
suivants s'ajoutent selon le projet. Chaque ligne se coupe. Relevé sur trois projets réels le 2026-11-09 (un client
iOS, un développeur de photos en Rust, un dépôt de configuration shell) : ce socle est leur dénominateur commun, plus
ce qui leur a manqué. Budget et détail des outils : [CI-BUDGET](CI-BUDGET.md).

## 1. Les paliers

| Palier | Pour qui | Contenu | Coût par PR prête |
|---|---|---|---|
| **0 · Hygiène** | tout dépôt | secrets (gitleaks), lint des workflows (zizmor, actionlint), Markdown et README ([README-STANDARD](README-STANDARD.md)), Dependabot `github-actions` hebdomadaire groupé | 1 min Linux |
| **1 · Qualité** | tout dépôt avec du code | **une commande locale, la même que la CI** ; lint du langage en mode strict ; tests | 1 à 10 min Linux |
| **2 · Cher** | macOS, simulateur, VM, matrice d'OS | derrière le palier 1 (`needs:`), seulement si les chemins concernés changent, jamais sur un brouillon | 10 min et plus, ×10 sur macOS |
| **3 · Sécurité lourde** | code livré à des utilisateurs | SAST, dépendances (CVE), sur PR prête + branche d'intégration + chaque semaine | 2 à 5 min Linux |
| **4 · Processus** | projet piloté par issues | labels synchronisés depuis un fichier, PR liée à une issue, ruleset versionné, tableau de bord | secondes |

Paliers 0, 3 et 4 : workflows réutilisables du cadre (`docs-security.yml`, `security.yml`, `labels-sync.yml`,
`issue-hygiene.yml`, `pr-hygiene.yml`, `repo-settings.yml`, `flow-report.yml`), appelés par `harness.yml`. Paliers 1
et 2 : au projet, le cadre n'impose ni l'outil ni le langage.

## 2. Les six invariants de tout workflow

Vérifiés par zizmor, actionlint et la revue ; aucun ne dépend du langage.

| # | Invariant | Pourquoi |
|---|---|---|
| 1 | `permissions: contents: read` (ou `{}`) en tête ; l'écriture se donne au job qui en a besoin | un workflow compromis ne peut pas écrire |
| 2 | Actions épinglées par SHA complet, version en commentaire ; Dependabot les met à jour | un tag se déplace |
| 3 | `concurrency` avec annulation sur les PR, jamais sur une branche protégée | un push n'en paie qu'un |
| 4 | `timeout-minutes` sur chaque job | un job bloqué coûte 6 h par défaut |
| 5 | `persist-credentials: false` ; jamais de `${{ … }}` d'événement dans un `run:` | injection, fuite du jeton |
| 6 | Rien sur un brouillon ; les contrôles requis passent sans secret (PR de fork) | budget, contributions externes |

## 3. Palier 1 : la commande locale d'abord

Le socle ne commence pas par un workflow mais par **une commande** (`make check`, `cargo xtask ci`,
`pre-commit run --all-files`, `scripts/ci/local-check.sh`) que l'agent lance avant chaque push et que la CI rejoue
telle quelle. Sans elle, « rien sur un brouillon » veut dire que l'agent découvre ses erreurs au passage « Ready »,
et que chaque correction coûte un passage.

- Elle dit **INCOMPLET** quand un outil manque, jamais « vert ».
- Elle a un mode rapide (ce qui a changé) et un mode complet (ce que la CI lance).
- Elle écrit un résumé lisible (ce qui a tourné, ce qui a été sauté, pourquoi) que la PR reprend.
- `CLAUDE.md` › Build et tests la nomme. Le hook pre-commit en lance la partie rapide.

## 4. Ce que le relevé a montré

| Constat | Où | Ce que le socle en tire |
|---|---|---|
| 🔴 Des workflows `issues`, `issue_comment`, `pull_request_target`, `schedule` écrits mais **jamais lancés** : ils ne partent que de la branche par défaut, et le projet travaille sur une autre | client iOS | La branche d'intégration **est** la branche par défaut, ou ces workflows vivent aussi sur la branche par défaut. Et l'état d'une issue se lit sans workflow : un label posé à la main vaut un label posé par un robot |
| 🔴 Jobs macOS sans `timeout-minutes` ; aucun cache des dépendances | client iOS | Invariant 4 ; cache au palier 2 |
| 🔴 Actions par tag, écriture donnée au workflow entier, ni timeout ni concurrence | dépôt de configuration | Palier 0 et invariants 1 à 4 : le dépôt « trop petit pour une CI » est celui qui a les droits les plus larges |
| 🔴 Aucun scan de secrets, aucun audit de CVE des dépendances | projet Rust | Paliers 0 et 3 |
| 🟠 Secrets hérités en bloc (`secrets: inherit`) par un workflow partagé suivi sur une branche | projet Rust | Un workflow réutilisable s'épingle par SHA et reçoit ses secrets nommément |
| 🟠 Le scan de secrets tourne deux fois par push (hook rejoué + job dédié ; `push` + `pull_request`) | deux projets | Un contrôle, un endroit |
| 🟠 Pas de point d'entrée local unique | client iOS | Palier 1 |
| 🟢 Une commande locale = la CI, avec rapport de ce qui a été sauté | projet Rust | Le modèle du palier 1 |
| 🟢 Détection de changements + échec immédiat des jobs macOS sur brouillon | client iOS | Palier 2 ([CI-BUDGET](CI-BUDGET.md) §2) |
| 🟢 Contrôle de chaîne d'approvisionnement fait maison (verrou à jour, sources git autorisées) | projet Rust | Palier 3, quand un audit de CVE ne suffit pas |

## 5. Ce que ce socle remet en cause dans le cadre

1. **« Rien sur un brouillon » ne tient que si le palier 1 existe.** Le cadre donnait la règle sans fournir la
   commande : c'est maintenant la première chose à poser, avant tout workflow.
2. **Le cadre ne s'applique pas ses propres règles partout** : ses labels ne sont pas synchronisés sur son propre
   dépôt, et il n'a pas de fichier de licence. Un cadre se juge d'abord sur lui-même.
3. **Un job, pas dix.** Les contrôles Linux d'un palier tiennent dans un job dont chaque étape tourne même si la
   précédente échoue : un passage, tous les constats, une minute facturée. À éclater seulement quand un contrôle
   requis doit pouvoir être sauté seul.
4. **L'automatisation du processus (palier 4) est un confort, pas une fondation** : sur le projet le plus actif,
   elle est inerte depuis des mois et le suivi tient quand même, à la main, sur 437 issues. Les règles doivent donc
   rester applicables sans elle.
5. **La revue IA en CI n'est pas dans le socle.** Elle demande un secret, donc ne peut pas être un contrôle requis
   (invariant 6) ; elle reste une option.

## 6. Adopter le socle dans un projet

1. Palier 1 : écrire la commande locale, la nommer dans `CLAUDE.md`, la faire rejouer par le workflow du projet.
2. Palier 0 : décommenter le job `docs` de `harness.yml`.
3. Vérifier que la branche d'intégration est la branche par défaut (sinon les jobs `issue`, `flow`, `settings`
   restent muets).
4. Ruleset : contrôles requis = noms de jobs réels ([CI-BUDGET](CI-BUDGET.md) §4), dans `.github/repo-settings.json`.
5. Paliers 2 et 3 selon le projet.
