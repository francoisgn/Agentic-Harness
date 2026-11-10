# One label per lot (or per milestone)

- **Asked in:** label review of 2026-11-09 ([ADR 0003](../docs/adr/0003-labels-readable-by-axis.md))
- **Decision:** declined on 2026-11-09
- **Why:** labels would grow with the plan (168 lots on the most active project observed) and drown the four
  exclusive axes that make state readable. The information already has a native home.
- **What would change the answer:** a project where GitHub milestones and sub-issues are unavailable. Until then:
  milestone = GitHub milestone, lot = `type: epic` issue with sub-issues, `LOT-NNN` in the title.
