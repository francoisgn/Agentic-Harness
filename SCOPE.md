# Scope: what enters the harness, and what does not

The harness is a toolbox, not a doctrine. It ships skills, agents, scripts, workflows and a method that a project
can keep, replace or switch off piece by piece. This file is the bar a change must clear, so the toolbox stays small.

## The bar: two tests, both required

1. **Observed failure.** The change answers a failure seen in a real project: a link to the issue, PR, CI run or
   review where it happened. "It could happen" and "another framework does it" do not pass.
2. **Fits the toolbox.** The change:
   - can be switched off or replaced without breaking the rest (a config key, a workflow input, a deletable file);
   - works with any coding agent that reads `AGENTS.md`, or says plainly which adapter it needs;
   - adds no required account, secret or third-party service;
   - costs little context: a rule loaded in every session (`docs/ESSENTIALS.md`) has to earn its line.

A mechanical rule becomes a deterministic check (script, hook, CI step). A judgment rule becomes a line in the
standards a reviewer reads. A rule that is neither does not enter.

## In scope

| Area | Examples |
|---|---|
| Method | issue-driven loop, intent, lots, review rounds, lessons |
| Guardrails | git guard hook, secret scanning, workflow invariants |
| Skills and agents | lot start/finish, reviewers, stewards, README upkeep |
| Repository plumbing | label taxonomy, issue forms, PR template, rulesets as code |
| Measurement | flow dashboard, first-pass quality, CI budget |

## Out of scope

| Not here | Why | Where instead |
|---|---|---|
| Language or framework style rules (Swift, Rust, React…) | project knowledge, not method | the project's `CLAUDE.md` / `AGENTS.md` |
| A full spec-driven process that owns every step | the harness assists a workflow, it does not replace one | a dedicated framework |
| Product design taste (UI, copy) | needs its own vocabulary and detectors | a design skill |
| Anything requiring a paid service to pass a required check | required checks pass without secrets | optional workflow |
| Rules that cannot be turned off | non-dogmatic by construction | nowhere |

## Refusals are recorded

A proposal that does not clear the bar gets a file in [`.out-of-scope/`](.out-of-scope/README.md): what was asked,
why it was declined, what would change the answer. A later request for the same thing starts from that file instead
of from zero.
