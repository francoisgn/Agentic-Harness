---
name: compliance-review
description: Lance, sur le diff courant, les relecteurs de conformité activés dans .harness/config.json (gdpr, eu-ai-act, nis2, iso27001, soc2, tisax, pci, hds) dont le périmètre est touché, en parallèle, et consolide leurs verdicts pour la PR. À utiliser avant « Ready for review » dans un projet soumis à un référentiel.
argument-hint: "[ids séparés par des virgules, défaut : config] [base]"
---

# Revue de conformité

Référence : `.harness/docs/COMPLIANCE.md`.

1. **Quels agents** : `$ARGUMENTS` s'il nomme des ids ; sinon `compliance` de `.harness/config.json`, plus ceux
   qu'exige un label `conformité: <id>` des issues liées. Aucun → répondre « aucun référentiel activé » et s'arrêter.
2. **Diff** : `git diff origin/<base>...HEAD` (base : argument, sinon `integration_branch`). Pour chaque agent, lire
   sa section « Quand intervenir » (`.claude/agents/compliance-<id>.md`) ; hors périmètre → `HORS PÉRIMÈTRE` sans lancer.
3. **Lancer en parallèle** les sous-agents concernés (`compliance-<id>`), nommés `<projet>.<orc>.conf-<id>.<cible>`
   (ORCHESTRATION §7 ; description `conf-<id> <cible> — conformité`), chacun avec : le diff, la tête (SHA), la spec
   liée, `ESSENTIEL.md`. Jamais les conclusions de l'auteur. Ils sont en lecture seule.
4. **Consolider** dans un tableau `Référentiel | Verdict | Constats ouverts | À confirmer par` et ajouter la section
   « Conformité » à la PR. Une faille de sécurité : aucun détail public.
5. Écarts Haute / Moyenne : corriger en un commit puis relancer seulement les agents concernés, ou ouvrir une issue
   `conformité: <id>` pour décision du responsable (risque accepté = ADR).
