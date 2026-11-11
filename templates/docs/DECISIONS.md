# Operator decisions

The operator's **standing** decisions, read by every agent before it acts. Only rows `in force` bind. A decision
given in a comment or in chat is not one until it is recorded here: the agent that receives it adds the row in its
next commit, quotes the source (link, date), and until then says "recorded: not yet". A new decision that contradicts
one in force names it: the old row becomes `replaced by <date>` (a freeze that ends: `lifted <date>`), so a scope key
has at most one row `in force` (`scripts/decisions-check.py`, run by the docs job; delete this file to switch the
rule off).

Newest first. Scope key: short and stable (`children.max`, `merge.policy`). One sentence per decision. Status:
`in force`, `replaced by <date>` or `lifted <date>`. Not here: architecture decisions (`docs/adr/`) and one-off
answers that are not standing rules.

| Date | Scope key | Decision | Source | Status |
|---|---|---|---|---|
