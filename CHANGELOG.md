# Changelog

Format : une section par version (semver), du plus récent au plus ancien. « Action » = ce qu'un projet consommateur doit
faire en passant à cette version.

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
