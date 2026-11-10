# LOT-XXX: <short name>

- **Module / layer:** <engine | app | tooling | docs>
- **Model:** <author> → <reviewer> (never the same; tier label of the issue, `difficulty:` by default, otherwise deduced from the project's routing)
- **Difficulty:** trivial | easy | medium | hard (hard spanning several layers = split into lots before starting)
- **Issue:** #…  ·  **Depends on:** #… (or none)

## Summary
A user story or two lines: what the lot brings and why now.

## Sources
Each external fact (rule, API, protocol, reference behaviour) with its source: official link, `file:line`
at a named commit, capture. Nothing guessed: what is missing is listed under "Pending" below.

## Behaviour
Inputs, outputs, rules. Edge cases (empty, very large, errors, cancellation, concurrency).

## Intended differences
Accepted deviations from the reference (old behaviour, old version), each one justified.

## Data and compatibility
Persisted fields added or renamed: optional or with a default, tolerant decoding, migration on read
(CONVENTIONS.md §Persistence). "None" otherwise.

## Tests
The tests that prove the lot, each seen failing without the change. What can only be tested by hand (and where).

## Pending
Captures, decisions (`status: needs-decision`), missing access: each with its issue.

## Lessons
To carry over to LESSONS (method) or to the project notes (domain facts) at closing.
