---
id: <short identifier, e.g. dora>
framework: <official text and version, e.g. Regulation (EU) 2022/2554 (DORA)>
confirmed_by: <who decides: DPO, CISO, QSA, auditor>
spec-version: 1
---
# <Name of the compliance framework>: review spec

Spec read by the generic reviewer `compliance-reviewer` (Belayline, COMPLIANCE.md §2). The project
writes it, keeps it up to date and declares it in `.harness/config.json`:
`{"id": "<id>", "spec": "docs/compliance/<id>.md", "paths": ["…"], "keywords": ["…"]}`.
Nothing guessed: a requirement identifier not verified against the official text carries "(to verify)".

## When to step in
- Paths, keywords, data types that bring a diff into scope.

## What I check
1. <What can be verified in the code, the configuration, the CI or the docs>: <requirement, no.> (<source>)
2. …

## Expected evidence
- Artifacts that must exist in the repository (register, impact assessment, ADR, SBOM, policy…).

## Sources
- <Official URL> (accessed on <YYYY-MM-DD>)
