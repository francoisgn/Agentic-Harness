# Changelog

Format : une section par version (semver), du plus récent au plus ancien. « Action » = ce qu'un projet consommateur doit
faire en passant à cette version.

## Non publié

- **Identité du dépôt** (CONVENTIONS §Identité du dépôt) : tout dépôt qui suit le cadre porte une description (une
  phrase), des topics (5 à 10), une bannière en tête du README (`docs/assets/banner.svg`) et une social preview
  (`docs/assets/social-preview.png`, 1280×640, texte en anglais, déposée à la main par l'opérateur). Le doc steward
  vérifie les quatre (STEWARDS §2, agent `doc-steward`), ADOPTION le prévoit.
- `repo-settings.py` : avertit (sans bloquer) si la description ou les topics manquent ou sont mal formés ; la
  description restée celle du gabarit (`<…>`) n'est plus envoyée à GitHub.
- Le cadre s'applique la règle : bannière et social preview ajoutées ; `check-framework.py` contrôle description,
  topics et images.

Action : remplir la description et les topics dans `.github/repo-settings.json`, ajouter les deux images (une issue
suffit pour commencer) ; l'opérateur dépose la social preview dans les réglages du dépôt.

## 0.3.0 — 2026-11-09

Retours du premier projet consommateur : un cadre neutre, des règles qui ne se contredisent plus. **Rupture de
convention** (avant 1.0.0, un MINEUR peut casser) : branches, prise en charge et corps de PR changent.

- **Neutre** : plus aucune référence aux autres projets du mainteneur (noms, numéros de décision, coûts mesurés,
  anecdotes) ; leurs leçons restent, reformulées pour valoir partout (source « terrain » dans LESSONS).
- **Pousser souvent, payer au « Ready »** (CI-BUDGET §2) : remplace « un push par lot, pas de push d'essai ». On pousse
  tôt et souvent sur une PR en brouillon (sauvegarde, visibilité) ; la CI coûteuse ne tourne qu'au passage « Ready »
  ou sur un label explicite (motif de workflow fourni) ; un commit par cycle de revue ; jamais de push « pour voir »
  sur une PR prête. Le tableau de bord ne compte plus les runs sautés ou annulés comme des pushes testés.
- **Prise en charge** = commentaire `/claim <id>` (première ligne), rejoué dans l'ordre : la première prise gagne,
  seuls les membres du dépôt comptent, `/release [<id>]` la rend ; la PR porte `Claim: <id>`. Remplace « Pris en
  charge — branche … » (ESSENTIEL, METHODOLOGY, CONVENTIONS, ORCHESTRATION, skills, label, session-start).
- **Axes de labels réglables** : `.harness/config.json` → `labels.model_prefixes`, `labels.size_prefixes` ;
  `/lot-start` ne s'arrête plus sur un label de niveau ou de taille manquant (déduit du texte et du routage, dit dans
  la prise en charge).
- **Registre (« ledger »)**, brique facultative (CONVENTIONS §Registre) : les PR ne touchent plus les journaux
  partagés, leurs entrées vont dans une section `### Ledger` du corps (label `ledger`), qu'un steward replie après le
  merge dans une PR de docs reproduite par le script du projet. `pr-hygiene.yml` : entrée `ledger-label` (contrôle
  section ↔ label). `/lot-finish` et le gabarit de PR : ligne d'issue, `Claim:`, lot, problème / cause / changement /
  tests, `### Ledger` seulement si le projet en tient un, au lieu de `## Changelog`.
- **Branches** `<type>/<nom-court>` (`lot`, `fix`, `feat`, `chore`, `docs` ; `branch_types` dans `config.json`) au
  lieu de `claude/<lot>`, partout (skills, docs, gabarits, workflow de synchro, message du hook). Le tableau de bord
  reconnaît une PR d'agent à sa ligne `Claim:` ou à son pied de génération.
- **guard-git** durci : options groupées (`-fu`, `-uf`, `-nm`), abréviations, `--force-with-lease`, `+refspec`,
  `--mirror`, `--all`, suppression d'une branche protégée (`--delete`, `-d`, `:branche`), `git -C`, `git -c`,
  enveloppes (`env`, `command`, `exec`, `sudo`, `xargs`, `eval`, `bash -c`, `sh -c`…), sous-shells, groupes,
  substitutions, here-documents, tous les séparateurs ; `git push` nu, `git push origin` et `HEAD` résolus contre la
  branche courante (`rev-parse`, ou la branche choisie plus tôt dans la ligne par `git switch` / `git checkout`),
  `@` comme `HEAD`, `--tags` seul permis, refspecs à joker couvrant une branche protégée refusées ; repli sur une expression prudente si la commande ne se découpe pas. Laisse passer
  `--dry-run`, `--force-if-includes` seul et les branches non protégées ; reste ouvert sur une entrée illisible. Le
  ruleset côté serveur reste la vraie protection (BRANCHING-RELEASE §Règles communes). Tests :
  `scripts/tests/test_guard_git.py`.
- **Blocs gérés** de `CLAUDE.md` / `AGENTS.md` (fr, en) : `harness-sync.sh` vit dans le dépôt du cadre (comment le
  lancer depuis un projet) ; précédence explicite, dérogations du projet dans une section « Harness overrides » de son
  `AGENTS.md` (ajoutée au gabarit).

Action :
- `/harness-update` vers v0.3.0 ; la PR de mise à jour montre les nouveaux blocs gérés.
- Créer la section « Harness overrides » dans `AGENTS.md` et y écrire ce que le projet garde à sa façon (branches,
  labels, prise en charge, politique de merge).
- `.harness/config.json` (fichier du projet, non réécrit) : ajouter au besoin `branch_types`, `labels`
  (`model_prefixes`, `size_prefixes` ; `[]` si l'axe n'existe pas), `ledger` (`enabled`, `label`, `fold_command`).
- Branches et prises en charge : passer à `<type>/<nom-court>` et `/claim <id>` (ou consigner la dérogation).
- `harness.yml` : retirer `require-changelog: true` du job `pr` (le gabarit de PR n'a plus de section « Changelog ») ;
  poser `ledger-label: ledger` si le projet tient un registre, et créer les labels `ledger` et `ledger: done` dans
  `.github/labels.local.json`. `.github/pull_request_template.md` (fichier du projet) : reprendre le nouveau gabarit
  au besoin.
- CI du projet : appliquer le motif de CI-BUDGET §2 (jobs coûteux sautés sur un brouillon, sauf label explicite).

## 0.2.0 — 2026-11-07

Intention, TDD, FinOps, stewards, conformité, sécurité et mesure du flux.

- **Ouvert à tous** : plus aucune référence nominative au créateur (rôles : mainteneur, opérateur ; auteur du plugin
  « agentic-harness contributors ») ; le cadre vaut pour tout agent de code (Claude Code, Codex CLI, Cursor, Gemini CLI,
  Copilot, Aider… ; chargement par `AGENTS.md`, natif ou à activer selon l'outil : ADOPTION §Brancher votre agent), Claude Code restant l'adaptateur fourni (plugin, hooks, `.claude/`) ; pied de commentaire nommant
  l'agent ; niveaux de modèles par fournisseur (ORCHESTRATION §2).
- **Méthode** : intention obligatoire des issues (user story, comportements d'erreur, critères Étant donné / Quand /
  Alors, définition de fini : METHODOLOGY §2 bis) et TDD (§2 ter) ; formulaires d'issue enrichis ; ESSENTIEL (fr, en).
- **Docs** : FINOPS (orchestrateur SPOC seul agent long, contexte dans le dépôt, routage des modèles, quotas et
  reprise, boucles bornées, signaux de dérive), STEWARDS (rôles d'entretien, rapport non technique), REVIEW-SERVICE
  (service de revue maison), COMPLIANCE (relecteurs de conformité), UTILISATION (guide pas à pas, exemple SwiftHFR),
  ADR 0002 ; CI-BUDGET §3 (secrets et variables) et §5 (volume agentique) ; ORCHESTRATION §7 (**nommage des agents**
  `<projet>.<orchestrateur>.<rôle>.<cible>`, vérifié en CI) ; LESSONS : remontée des leçons par issue.
- **Agents** (vendorisés en `.claude/agents/`) : `adversarial-reviewer`, `issue-steward`, `doc-steward`,
  `flow-monitor`, `compliance-gdpr`, `-eu-ai-act`, `-nis2`, `-iso27001`, `-soc2`, `-tisax`, `-pci` (DSS, PIN, P2PE),
  `-hds`, et le relecteur générique `compliance-reviewer`. Les identifiants d'exigence non vérifiés sur le texte
  officiel sont marqués « (à vérifier) ».
- **Conformité branchable** (COMPLIANCE §2) : par référentiel, agent intégré, agent de l'entreprise, ou spec seule
  (`docs/compliance/<id>.md`, gabarit fourni) appliquée par le relecteur générique ; périmètre décidé sans jeton par
  `paths` / `keywords` ; résolution et validation par `compliance-plan.py` (vendorisé, testé).
- **Qualité au premier passage** : le tableau de bord mesure le ratio de PR à problème (constat en revue
  adversariale, IA, conformité, CodeRabbit, humaine), agents / humains, et l'effort de correction (commits après le
  premier constat, délai jusqu'au merge) ; règle de traçabilité de chaque verdict (REVIEW-ROUNDS §Traçabilité).
- **Réglages du dépôt « as code »** : `.github/repo-settings.json` (description, topics, rulesets) appliqué au merge
  par `repo-settings.yml` / `repo-settings.py` (secret `REPO_ADMIN_TOKEN`), dérive contrôlée chaque semaine ; le
  cadre s'en sert pour lui-même (`settings.yml`). Contrôles requis vérifiés contre les noms de jobs réels.
- **Schémas** : README illustré de trois schémas (mécanismes, cycle d'un changement, tirer parti du harnais), source
  `docs/diagrams/*.json`, scène `.excalidraw` modifiable et SVG rendus par `scripts/diagrams/render.py` (contrôlés
  en CI).
- **Points d'extension** (ADOPTION §Remplacer ou étendre une brique) : chaque brique du cadre se garde, se remplace
  par celle de l'entreprise ou se complète.
- **Skills** : `/intent`, `/lesson-propose`, `/status-report`, `/compliance-review` ; `/lot-start` pose l'identifiant
  d'agent.
- **Workflows réutilisables** : `security.yml` (Semgrep CE, Trivy, gitleaks), `flow-report.yml` (issue « Tableau de
  bord du projet »), `ai-review.yml` (revue IA, claude-code-action épinglée, jamais requise).
- **Script** `flow-metrics.py` (vendorisé en `.harness/scripts/`) : jalons, goulots, travaux en panne, boucles de CI
  et de revue, ratio agents / humains, délai de merge, minutes de CI ; tests unitaires.
- **Labels** : `leçon`, `tableau de bord`, `revue: aucune`, `conformité`. `.harness/config.json` : clé `compliance`.
- **CI du cadre** : contrôle de cohérence (`check-framework.py` : skills, agents, manifeste, labels, nommage), tests
  Python, gitleaks ; Dependabot pour les actions ; formulaire d'issue « Leçon ».

Action supplémentaire : créer le secret `REPO_ADMIN_TOKEN` pour que le job `settings` applique
`.github/repo-settings.json` (sinon il avertit seulement).

Correctif : la CI du cadre écoutait `main`, la branche par défaut est `master`.

Action : `/harness-update` vers v0.2.0. Dans `harness.yml` (fichier du projet, non réécrit) : ajouter le
déclencheur `schedule` et le job `flow` (voir le gabarit), activer au besoin `security` et `review`. Renseigner
`compliance` dans `.harness/config.json` et exclure les agents de conformité inutiles.

## 0.1.0 — 2026-11-07

Première version, distillée de HFRnow (`dev-swift`) et d'un autre projet.

- Docs (français) : ESSENTIEL (règles chargées à chaque session), METHODOLOGY, CONVENTIONS, LESSONS (82 leçons à
  portée, sources citées), ORCHESTRATION, REVIEW-ROUNDS, BRANCHING-RELEASE, CI-BUDGET, MAC-HANDOFF, ADOPTION, ADR 0001
  et gabarit d'ADR. Édition anglaise d'ESSENTIEL et des blocs `CLAUDE.md`/`AGENTS.md` (`i18n/en/`).
- Taxonomie de labels canonique (type, priorité, modèle, taille, statut, hôte) avec `axis` et `aliases`.
- Gabarits : bloc `CLAUDE.md`/`AGENTS.md`, formulaires d'issue (retour de test, bug, fonctionnalité, tâche), PR, lot,
  markdownlint, `.harness/config.json`, workflows appelants `harness.yml` et `harness-sync.yml`.
- `scripts/harness-sync.sh` : vendorisation idempotente (modes copy, tree, block, seed, jsonmerge, refbump), verrou à
  empreintes, `--check`, `--dry-run`, `--force`, `--skip-workflows`, `--skip-seed`, langue et exclusions par projet.
- Plugin `harness` (marketplace `agentic-harness`) : six skills, hook `guard-git` (push forcé, push vers une branche
  protégée, `--no-verify`), hook de rappel en début de session.
- Workflows réutilisables : `labels-sync`, `issue-hygiene`, `pr-hygiene`, `docs-security`.

Action : adoption, voir docs/ADOPTION.md.
