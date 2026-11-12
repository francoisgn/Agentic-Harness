# The pace, and what it breaks

Part 1 of [The software factory, rethought for agents](README.md). For anyone who runs or pays for a software
factory: tech leads, CI owners, and the managers who approve agent tools.

> **Last checked: 2026-11-11.** The outside example cites the page it comes from, with the date it was read. Our own
> numbers cite the issue or the pull request list they come from. Re-check them before you decide anything.

**TL;DR**

- A factory is sized for people: a few pull requests a day, a human who reads each one, one CI run per push, one
  account per person. Agents keep the steps and multiply how often each one runs.
- At the front of the field, Anthropic reports going from about 2,500 merged changes a day in May 2026 to over 30,000
  a day in September, and replacing Git for its monorepo with a system of its own (§2). That is one company's account
  of its own tooling, at a size few teams reach.
- At our scale the change is smaller but already visible: this repository merged 22 pull requests on one day, and the
  first consumer project reached about 830 issues and pull requests in ten days (§3).
- What breaks first is not the writing of code: it is everything that runs once per change, or waits for one person
  (§4). The harness answers most of these by running less, later and in the right place; it has no answer for the
  version control itself, and works on Git and GitHub as they are (§5).

## 1. The same change, at two paces

| Step of one change | At human pace | At agent pace |
|---|---|---|
| Writing | Hours to days per change | Minutes; many changes in parallel, from one person |
| Pushes | A few per change | Many small commits per change, pushed often |
| CI | One run per push is affordable | One run per push multiplies minutes by the number of pushes |
| Review | A colleague reads every line | The reader becomes the queue every change waits in |
| Scanners | Run on every commit, results read | Run on every commit, results pile up unread |
| Tracker and docs | Updated by the author, by hand | Updated by whoever remembers, or by nobody |
| Coordination | People remember what they are doing | One orchestrating agent holds the state, until its context is full |
| Accounts | One person, one seat, one token | One person, a hundred agents, still one seat |

"Agent pace" is not a fixed figure: it is whatever one person's fleet produces. §2 and §3 give measured examples.

## 2. At the front of the field: Anthropic's source control

Anthropic published
[Redesigning source control at Anthropic](https://www.anthropic.com/research/redesigning-source-control) (dated
2026-10-13, updated 2026-10-15; read 2026-11-11). Detailed notes of the page, section by section:
[sources/anthropic-source-control.md](sources/anthropic-source-control.md).

![Bar chart "Changes merged per day, Anthropic monorepo, January to September 2026": daily merges split into pull requests and Antique change requests, with a 7-day average line; pull requests only and under about 3,500 a day until May, Antique change requests from June and nearly all merges from July, a dip marked "Quiet week" around the start of August, then a rise to a peak annotated "30,401 merged on Sep 9"](https://www-cdn.anthropic.com/images/4zrzovbb/website/1e2a750dba61db4a76b72eec5b0cf50b8a7f878c-3840x2160.png)

Figure: Anthropic, Redesigning source control at Anthropic,
<https://www.anthropic.com/research/redesigning-source-control>, read 2026-11-11. Shown by reference; © Anthropic.

What the page says, in its own words:

| Topic | What the page says |
|---|---|
| Volume | "In May 2026, Anthropic averaged around 2,500 code changes merged per day; as of September, we merged over 30,000 per day." |
| Why | "coding is no longer the bottleneck to building systems or doing research"; the bottleneck is "all of the developer infrastructure built for human scale: source control, builds, and CI"; "the latent demand for merging code is practically infinite" |
| Size | "The history of our main branch alone is almost 100 GB", and a compressed working copy is over 25 GB |
| CI load | "We perform on the order of 25 million code checkouts per day for CI"; fetched naively, "over 600 PB of git traffic per day" |
| What broke | "at our peak, we operated several hundred internal git mirrors to deal with the load"; they "became harder to operate as our merge rate increased"; history-dependent operations such as diff and blame took "more and more care" on partial clones |
| Merging | The team has not been able to replicate "a global repository lock on the merge queue"; it invested instead in "post-merge and pre-deploy automated testing", so "concurrent changes can conflict", which Claude "can typically fix" |
| Review | About the team that built Scion: "Our team members still review every change request for the system, but they now examine the intent of the change as opposed to reading every line of code." The review tooling separates comment-only changes from sensitive logic "so that human reviewers can focus on the most consequential changes" |
| What changed | "we built Scion, an in-house version control system, and fully migrated our monorepo from git in five months", plus a code review surface called Antique; a team of seven did it while merges per day grew 10x; Scion's footprint is "200x smaller than our previous git mirroring infrastructure" in CPU and memory; "CI alone realized a 25% CPU capacity win" |
| Scope | "Scion is by no means a suitable replacement for git for general use"; the ideas "really only make sense for truly enormous monorepos" |

Read it as the far end of the curve, not as a plan. It describes one company, with one very large monorepo, writing
about its own tools; the page itself says the result is not for general use. What carries over to smaller teams is
the list of what gave way: the machinery that runs once per change (mirrors, checkouts, CI), the merge queue, and the
way people review. Two commentary articles retell the story
([dev.to](https://dev.to/gabrielanhaia/claude-took-anthropic-from-2500-to-30000-merges-a-day-then-it-moved-off-git-5g7j),
[Medium](https://medium.com/@lordmoma/anthropic-ditched-git-after-agents-pushed-30-000-changes-a-day-5480bab1b4fd));
every figure above is taken from the primary page, not from them (the Medium one could not be opened on 2026-11-11;
what each adds is in the notes).

## 3. At our scale

**This repository.** Merged pull requests per day, counted from the repository's closed pull requests (GitHub pull
request list, read 2026-11-11 at about 22:35 UTC; every closed pull request of the period was merged, 37 in all;
days in UTC):

| Day (2026) | 11-07 | 11-08 | 11-09 | 11-10 | 11-11 (until 22:35 UTC) |
|---|---|---|---|---|---|
| Merged PRs | 2 | 0 | 1 | 22 | 12 |

One operator, one repository of documents and scripts, no app build; the harness runs lots in parallel
([ORCHESTRATION §5](../ORCHESTRATION.md#5-lots-in-parallel)). The period starts with the first merged pull request, so
it shows a burst, not a steady rate.

**The first consumer project** (an iOS client), as recorded in
[#59](https://github.com/francoisgn/belayline-agentic-harness/issues/59) on 2026-11-11, after ten days of use:

| Fact | Figure |
|---|---|
| Issues and pull requests | about 830 |
| The orchestrator's memory issue | 287 comments in 10 days (about 100 k tokens to re-read) |
| Merged pull requests with no `Docs:` line | 85 of 85 |
| Conflicts fixed by hand after two pull requests edited the same cell | 20 |
| Successive holders of the doc steward role | 4 in 10 days, about two docs PRs a day |
| Issues left in `status: needs-triage` | 55 |

**Observed by the operator (2026-11):** one developer can start about a hundred agents and sub-agents in a day; a
laptop has run at full CPU for weeks while agents built several iOS apps.

These are one operator's projects. They show the shape of the load, not a rate for anyone else.

## 4. What the volume breaks

Each subsection gives the mechanism, the part of this guide that treats it, and the harness file that already
answers it.

### Per-push CI and its minutes

CI that starts on every push costs one run per push. Agents push small commits often, so the bill grows with the
number of pushes, not with the number of finished changes. Anthropic's version of the same mechanism is 25 million
checkouts a day (§2).
Treated in part 2 ([#83](https://github.com/francoisgn/belayline-agentic-harness/issues/83)) and part 4
([#85](https://github.com/francoisgn/belayline-agentic-harness/issues/85)).
Harness: full CI on the move to "Ready", not on draft pushes; fast checks run locally first
([CI-BUDGET §2 and §5](../CI-BUDGET.md#5-agentic-volume-many-commits-few-runs)); at most 6 CI-tested pushes per pull
request ([FINOPS §3](../FINOPS.md#3-quotas-parallelism-and-resuming)).

### Human review as the only gate

When a person must read every line, review time grows with the number of changes and that person becomes the queue.
On Anthropic's Scion team, reviewers moved to checking the intent of a change rather than every line (§2).
Treated in part 3 ([#84](https://github.com/francoisgn/belayline-agentic-harness/issues/84)).
Harness: two reviews by agents before a human looks, one against the issue's intent and one on the code
([REVIEW-ROUNDS](../REVIEW-ROUNDS.md#the-two-reviews), [REVIEW-SERVICE](../REVIEW-SERVICE.md#3-optimising-rounds-agentic-volume)),
at most 3 rounds, and a merge gate that checks the verdicts on the exact head
([CONVENTIONS §Pull requests](../CONVENTIONS.md#pull-requests)). A human still decides what is merged.

### Scanners triggered on every commit

A SAST or dependency scan that runs on every commit repeats the same work many times per change, and its findings
arrive faster than anyone reads them.
Treated in part 3 ([#84](https://github.com/francoisgn/belayline-agentic-harness/issues/84)).
Harness: heavy security scans run on ready pull requests, on the integration branch and weekly, not on every push
([CI-BUDGET §5](../CI-BUDGET.md#5-agentic-volume-many-commits-few-runs)); secrets are checked locally before the push.

### A tracker kept by hand

Labels and statuses that someone must move by hand fall behind as soon as changes outnumber the people moving them.
On the first consumer, 55 issues sat in `status: needs-triage` and 21 `status: blocked` issues cited blockers that
were all closed ([#59](https://github.com/francoisgn/belayline-agentic-harness/issues/59)).
Treated in part 4 ([#85](https://github.com/francoisgn/belayline-agentic-harness/issues/85)).
Harness: a script brings `status:` labels in line with issues, pull requests and claims, with no workflow needed
(`scripts/issue-reconcile.py`, [ADOPTION](../ADOPTION.md)), and an issue steward keeps the queue ready to claim
([STEWARDS §1](../STEWARDS.md#1-issue-steward-a-queue-ready-to-be-claimed)).

### Docs that drift between merges

Each merge can make a doc untrue. When many pull requests also edit the same shared file (a changelog, a status
table), they conflict with each other. The first consumer had no `Docs:` line on 85 merged pull requests and 20
conflicts fixed by hand on one cell ([#59](https://github.com/francoisgn/belayline-agentic-harness/issues/59)).
Treated in part 4 ([#85](https://github.com/francoisgn/belayline-agentic-harness/issues/85)).
Harness: every pull request declares its doc impact in a `Docs:` line, and its entries for shared files go in a
ledger section that one steward folds after the merge
([CONVENTIONS §Ledger](../CONVENTIONS.md#ledger-never-a-conflict-on-a-shared-file),
[STEWARDS §2](../STEWARDS.md#2-doc-steward-docs-that-stay-true-and-readable)).

### A single orchestrator as memory

An orchestrating agent that keeps the project's state in its own conversation, or in a long comment thread, has to
re-read all of it to resume. At 287 comments in ten days, that was about 100 k tokens, and pull requests were merged
before their reports had been read ([#59](https://github.com/francoisgn/belayline-agentic-harness/issues/59)).
Treated in part 6 ([#87](https://github.com/francoisgn/belayline-agentic-harness/issues/87)).
Harness: context lives in the repository, not in the agent ([FINOPS §1](../FINOPS.md#1-topology-one-long-lived-agent-disposable-agents));
one State comment rewritten by a script is the only thing a resuming session reads
([ORCHESTRATION §8](../ORCHESTRATION.md#8-orchestrator-memory-one-state-the-rest-is-a-log)).

### Tools licensed and authenticated per human

Trackers, wikis, scanners and review bots are usually bought and signed into per person. A fleet of agents then
either shares one person's account, so nobody can tell which agent did what or stop one without stopping all, or
needs credentials the tool was not designed to hand out.
Treated in part 5 ([#86](https://github.com/francoisgn/belayline-agentic-harness/issues/86)).
Harness: partly. Every agent carries an id that ties its comments, commits and pull requests to its task
([ORCHESTRATION §7](../ORCHESTRATION.md#7-naming-agents-who-for-whom-on-what)), and the review service runs on one
repository or organisation secret ([REVIEW-SERVICE](../REVIEW-SERVICE.md#1-service-contract)). It does not settle
licensing or per-agent identities: that is part 5's subject.

### The version control workflow itself

At the far end, the source control system and its merge queue become the limit: mirrors to serve checkouts, a merge
queue that cannot hold one global lock, history too large to clone (§2).
Not treated by a part of this guide; replacing Git is out of its scope.
Harness: **no answer.** It works on Git and GitHub as they are, and it merges one pull request at a time on an exact
head ([CONVENTIONS §Pull requests](../CONVENTIONS.md#pull-requests)), which is a serial step. At our volumes that is
not a limit; at Anthropic's it would be.

## 5. What the harness chose, and what else is reasonable

The harness keeps the usual factory (Git, GitHub, pull requests, a human merge decision) and moves work around it:
cost per ready change instead of per push, agents review before people do, scripts keep state instead of memory. A
team at much higher volume can reasonably go further, as Anthropic did with post-merge testing and intent-level
review (§2). A team at lower volume can keep per-push CI and line-by-line review: the point of this page is to
measure the load before choosing, not to copy either answer.
