# Notes: "Redesigning source control at Anthropic"

Source: <https://www.anthropic.com/research/redesigning-source-control>. Read 2026-11-11.

These are notes for future writing, not a substitute for the source: re-read the page before quoting it. Written in
our own words, section by section; quotation marks mark the only verbatim wording. Used by
[part 1, the pace](../pace.md).

## Page facts

| Item | Value |
|---|---|
| Title | Redesigning source control at Anthropic |
| Published | 2026-10-13, team "Engineering"; topics Coding, Agents, Productivity, Claude Code |
| Updated | 2026-10-15, "to include more detail on the projects that pioneered many of the techniques we use in Scion" |
| Authors | Nick G. and the source control team (S.G., R.K., Dan C., Garrett H., Ben L., Colin M., Joe P.); thanks to Vilas J., Sergiu D. and Amir O. (early contributions to Antique) |
| Figures | Six captioned figures: merges per day (Jan to Sep 2026); "the typical setup for scaling git checkouts"; the shape of a changeset; Scion's checkout architecture; merged changes to the Scion and Antique codebases per week (Jan to Sep 2026); observed performance improvements on native Scion repos |

## Introduction

- Claim: at Anthropic, writing code is no longer the bottleneck; the bottleneck is "all of the developer
  infrastructure built for human scale: source control, builds, and CI".
- Claude is said to iterate on research loops, micro-optimise programs and build new services on its own.
- Volume: about 2,500 code changes merged per day on average in May 2026; over 30,000 per day "as of September"
  (2026). No figure for any other month in the text.
- Expectation: growth will not slow; "the latent demand for merging code is practically infinite"; each bottleneck
  removed raises the amount of code produced.
- First figure (caption: changes merged to the monorepo per day, January to September 2026). What it shows, as read
  from the image on 2026-11-11: daily bars split into "Pull requests" and "Antique change requests", with a 7-day
  average line. Bars are pull requests only from January to May, under about 3,500 a day; Antique change requests
  appear in June and make up nearly all merges from July; a dip labelled "Quiet week" around the turn of July and
  August; a peak annotated "30,401 merged on Sep 9". The y axis runs to 35,000.
- What was built, in five months: Scion (an in-house version control system) and the full migration of the monorepo
  from Git to it; also a code review surface called Antique, code search, a source control IAM system, and "novel
  ways of managing and landing large amounts of reviewed code".
- Framing: Claude's coding is both the cause of the problem and the way the replacement was built quickly.

## Growing our monorepo (what broke)

- The page calls its workload unusual: Anthropic uses Claude to write software more than almost any other company.
  It does not expect many organisations to hit these problems "in the very near term", but expects others using AI
  coding tools to meet the same pressure points before long.
- Git's design: every clone is a complete repository (diffs, history, blame, any checkout, offline). The page says this
  is right for most repositories.
- Size: main-branch history almost 100 GB; a compressed working copy over 25 GB.
- Load: on the order of 25 million code checkouts per day for CI alone, not counting developer environments, agent
  sandboxes and research jobs. Fetched naively: over 600 PB of Git traffic per day.
- Workarounds used: shallow clones, sparse checkouts, promisor remotes, internal Git mirrors (several hundred at the
  peak), repository snapshots ("seeds") in blob storage.
- What gave way: mirrors got harder to operate as the merge rate rose; seeds drifted further from the tip of main
  between refreshes; history operations (diff, blame) on partial clones needed more and more care. Later in the page:
  the mirrors no longer scaled once the repository outgrew their disks or memory.
- Diagnosis: Git was used as a centralised system with one authoritative copy, while nearly all clients were agents
  and jobs that are always online; Git's offline strengths worked against scaling.

## Principles for agent-scale source control

Prior art named: Google's Piper and Meta's Sapling (footnote: Sapling's server, Mononoke, and its Bonsai data model).

| Principle | In our words |
|---|---|
| Clients are always online | The client fetches data from a server that is always reachable, instead of holding a full copy |
| Client-server asymmetry | The server answers history and blame, creates commits, merges and rebases; the client keeps a bounded cache, lays out files, watches the filesystem |
| A source control service powers new tools | Every query the client uses is also an API, so many jobs need no local repository; automated bisect and revert pipelines depend on this |
| Everything scales horizontally | Data is distributed; no full copy of the repository exists anywhere, even on the server; no packfiles, so no repository maintenance |
| Commits are cheap, incremental, lock-free | Commits, rebases and merges happen on the server; cost scales with the change, not the repository; refs are discouraged except main and release branches, because global state is a scaling problem |
| The working copy is optional and sparse | A CI job can ask the server for a diff instead of checking out; sparse and virtualised checkouts; many writes also skip the checkout |

## How Scion works

- Unit of work: the "changeset", an entry in a write-ahead log. It lists the files changed relative to its first
  parent, with content-addressed pointers to compressed contents in blob storage (a Git commit points to a tree
  instead). Footnote: storing changes relative to the first parent is a choice; people only care about main-line
  history in trunk-based development in a monorepo.
- Throughput: no packfiles, no locking or cross-server coordination, no refs to move when creating a changeset. Moving
  a ref is a compare-and-swap on a single Spanner row.
- "Derived data": blame, path history, skip lists for the commit graph and later indices (copy detection, path-based
  file search), each defined recursively from parents; each computed eagerly or deferred; invisible to the client, so
  it can change without client changes.
- Servers: a small fleet answers every client operation (changesets, diffs, merge bases, blobs). All data is
  content-addressed, so any server can cache it without coordination; servers are "essentially large caches" that
  also compute derived data and write it back to Spanner.
- Migration order: early on, Scion answered only metadata queries (ancestry, blame) before it had its own client,
  repository format and protocols.
- Client `scn`: the fetch negotiation asks only for trees and blobs the client wants, recursively from a root tree;
  every request is for an immutable object, so any cache can answer; resumable, no multi-gigabyte packfile; sparse and
  virtualised checkouts need no special support.
- Fleet tiers: `scion-daemon` per node (starts from a periodically refreshed snapshot), regional `scion-cache`
  (streams objects from memory in the daemon's disk format), authoritative `scion-server` (reads Spanner or cloud
  storage). All three answer the same RPCs; tiering is enforced to isolate failure domains.
- Results reported: over 99% cache hit rate per tier; footprint 200x smaller than the former Git mirroring in CPU and
  memory; CI and research checkouts two orders of magnitude faster (seconds rather than minutes); 25% CPU capacity
  regained for CI; no repository maintenance for clients or caches.

## What we learned building Scion

- Timing: Scion was started around when Claude Mythos Preview and Claude Tag became available internally; both raised
  the need and sped up the work.
- Example: a largely hand-written prototype of the Git-to-Scion ingestion pipeline was rewritten by an early Claude
  Mythos Preview snapshot, with no further instructions, using 20x less memory and running 4x faster, keeping the
  ordering and data-structure invariants.
- Team: seven people built Scion and Antique and half a dozen related systems, and migrated in five months, while
  merged code per day grew 10x.
- Engineers: all engineers on the system "would now rate Claude as better at writing code than them"; they supplied
  system-level understanding and design trade-offs; their role was often to tell Claude "no". Examples: systems that
  found when a change merged by reading the commit log linearly instead of asking the code review tool; an
  adversarial review that was "overly defensive" about trusting another internal service and led to excess
  validation. Anthropic uses adversarial review extensively and calls it effective but sometimes myopic.
- Review: team members still review every change request for the system, now for the intent of the change rather
  than every line. This sentence is about the Scion team's own work.
- Quality: hermetic simulations of every non-trivial infrastructure and source control interaction, fuzzing, rate
  limiting; Claude found an ancestry-query optimisation that missed an index.
- Security: access control per repository and per directory; the review tooling expresses "complex semantic
  constraints on approvals" (for example comment-only changes versus sensitive logic) so human reviewers focus on the
  consequential changes.
- Operations: Claude Tag "superfans", one Slack channel per component (scion-daemon, scion-cache, the Antique merge
  queue…), with access to telemetry and logs, alongside traditional alerts.
- Merging: a proper merge queue "doesn't make much sense at agent scale"; hundreds or thousands of changes can merge
  while tests run. They could not replicate a global repository lock on the merge queue, so they rely on post-merge
  and pre-deploy automated testing; concurrent changes can conflict and Claude usually fixes the conflicts.

## Contributing to the wider ecosystem

- Scion is one part of an answer; the page does not expect its solution to suit every case.
- "Scion is by no means a suitable replacement for git for general use": only for very large monorepos, with tens of
  thousands of engineers or swarms of agents. Anthropic's token spending for internal use far exceeds what other
  businesses would want.
- Not offered publicly: it diverges from Git, needs its own review, search and CI, and the internal pieces are bespoke.
- Prediction: this class of problems becomes more common "over the next six to 12 months".
- Suggestions for Git: servers need not work like clients; forges could offer server-side RPCs, perhaps standardised;
  the negotiation protocol could change; sparse and shallow features could compose better.
- Tone: acknowledges two decades of Git community work; wants to partner with GitHub, GitLab and the open-source
  community.

## What the page does not say

- No per-day figures in the text other than May (about 2,500 average) and September (over 30,000); the 30,401 peak on
  September 9 is in the first figure only.
- Not how many of the merged changes were written by agents versus people, nor how many people or agents produced them.
- Not the CI cost in money, minutes or runners, beyond the 25% CPU capacity and the checkout counts.
- Not whether Git or GitHub is still used elsewhere in the company (open source, other repositories).
- No technical reason why the global merge queue lock could not be replicated, beyond the volume.
- Not how changes are tested before merge now, only that testing moved to post-merge and pre-deploy.
- No error or incident figures for the migration.

## Commentary articles (secondary, pointers only)

**dev.to**, Gabriel Anhaia, "Claude took Anthropic from 2,500 to 30,000 merges a day, then it moved off Git"
(<https://dev.to/gabrielanhaia/claude-took-anthropic-from-2500-to-30000-merges-a-day-then-it-moved-off-git-5g7j>, read
2026-11-11). It retells the primary page's figures. Beyond the primary page, each secondary, not verified on the
primary page:

- the author's opinion that Scion's ideas are not new as a category and that what is new is the reason it was built;
- that a Hacker News thread drew significant discussion within hours;
- that outsiders cannot reproduce Anthropic's numbers;
- that most teams will not reach 30,000 merges a day, but many will soon have agent-written changes outpacing CI and
  review;
- the advice to look at the merge queue and review rules before the version control system;
- a promotion of the author's own IDE product.

**Medium**, "Anthropic ditched Git after agents pushed 30,000 changes a day"
(<https://medium.com/@lordmoma/anthropic-ditched-git-after-agents-pushed-30-000-changes-a-day-5480bab1b4fd>): could
not be read on 2026-11-11 (HTTP 403 to WebFetch). Its headline says the 30,000 changes were "pushed by agents"; the
primary page does not split the count between agents and people (secondary, not verified on the primary page).
