# Architecture decisions (ADR)

One file per decision: `NNNN-short-title.md`, template [TEMPLATE.md](TEMPLATE.md). Status: Proposed · Accepted ·
Superseded by NNNN. Format: Context → Options → Decision → Consequences. A decision that is not in an ADR is not a
decision. An accepted ADR is never rewritten: it is superseded.

This folder holds the ADRs **of the harness**. Each project keeps its own in its own `docs/adr/`.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-distribution-mechanism.md) | Distributing the harness: versioned vendoring + plugin + reusable workflows | Accepted |
| [0002](0002-specialised-agents-and-dashboard.md) | Vendored specialised agents, review service and flow dashboard | Proposed |
| [0003](0003-labels-readable-by-axis.md) | Labels readable by axis: `axis: value`, states "needs triage" and "ready" | Accepted |
| [0004](0004-plugin-named-belayline.md) | The Claude Code plugin is named `belayline` | Accepted |
