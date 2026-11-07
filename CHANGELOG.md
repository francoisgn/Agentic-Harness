# Changelog

Format : une section par version (semver), du plus récent au plus ancien. « Action » = ce qu'un projet consommateur doit
faire en passant à cette version.

## 0.2.0 — 2026-11-07

Intention, TDD, FinOps, stewards, conformité, sécurité et mesure du flux.

- **Ouvert à tous** : plus aucune référence nominative au créateur (rôles : mainteneur, opérateur ; auteur du plugin
  « agentic-harness contributors ») ; le cadre vaut pour tout agent de code (Claude Code, Codex CLI, Cursor, Gemini CLI,
  Copilot, Aider…), Claude Code restant l'adaptateur fourni (plugin, hooks, `.claude/`) ; pied de commentaire nommant
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

Première version, distillée de HFRnow (`dev-swift`) et ios-app_credit-immo (`develop`).

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
