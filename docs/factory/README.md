# The software factory, rethought for agents: a guide in parts

For developers, tech leads and the people who run their CI, review and access rules. Read [the layers of
AI](../ai-layers/README.md) first if "agent", "OBO" or "inference" are new words.

**TL;DR**: a software factory is sized for people: a few pull requests a day, a human reviewer, one CI run per push,
one account per person. One developer can now start about a hundred agents in a day, and the factory sees all of
their work. Review, CI minutes, scanners and accounts then become the limit, not the writing of code. This guide
says what breaks, what the harness chose in response, and what else is reasonable. Each part is one page for one
audience; the facts about outside products are sourced and dated in the parts, not here.

| Part | Question it answers | For whom | File | Status |
|---|---|---|---|---|
| 1. The pace | Why must the factory be rethought: what does the volume of pull requests break? | anyone who runs or pays for a factory | `pace.md` ([#82](https://github.com/francoisgn/belayline-agentic-harness/issues/82)) | planned |
| 2. The CI choices of the harness | What does the harness run, when, and why was it chosen? | tech leads, CI owners | [`ci-choices.md`](ci-choices.md) ([#83](https://github.com/francoisgn/belayline-agentic-harness/issues/83)) | 🟢 available |
| 3. Review and scanning | What does each of adversarial review, review services, SAST, SCA, secret scanning and AI-assisted scanning catch, and when should it run? | tech leads, security | `review-and-scanning.md` ([#84](https://github.com/francoisgn/belayline-agentic-harness/issues/84)) | planned |
| 4. Run only when needed | Which triggers, loops and runners cost what, and when should work move to the edge? | CI owners, developers | `run-when-needed.md` ([#85](https://github.com/francoisgn/belayline-agentic-harness/issues/85)) | planned |
| 5. Identity and credentials for a fleet of agents | Who does what, who can reach what, and whom do you stop when something goes wrong? | security, platform teams | `identity.md` ([#86](https://github.com/francoisgn/belayline-agentic-harness/issues/86)) | planned |
| 6. The economics of spawning | How do short context, the right model and the shared bottlenecks change the cost of each agent? | tech leads, whoever pays | [`spawn-economics.md`](spawn-economics.md) ([#87](https://github.com/francoisgn/belayline-agentic-harness/issues/87)) | 🟢 available |

The order is the reading order: part 1 gives the reason, parts 2 to 4 the pipeline, part 5 access, part 6 cost. Each
part can be read alone.

Words used in every part:

- **Factory**: everything between a change being written and it running in production: tracker, branches, pull
  requests, CI, review, scanning, release. Here it is the whole line, not only the build.
- **Toolchain**: the programs the factory calls to build, test, check and ship a change (compiler, test runner,
  linter, scanner, package manager). A tool in the chain usually needs an identity and a token.
- **Runner**: a machine that executes CI jobs. It is hosted by the CI provider, or self-hosted, and each job holds
  it for some time.
- **Edge**: the developer's own machine, as opposed to the shared factory. Work run there costs no CI minutes, and
  it is not shared: it depends on that machine and on its owner.
- **Fleet**: the agents one person or one team has running at the same time, including the sub-agents they start.
  What matters is that they act in parallel and each one touches the factory.
- **Identity**: the account, token or app credential under which something acts on a service. For an agent it
  settles what it can reach and who answers for it, and whom you can switch off without stopping the others.

Words defined in [the layers of AI](../ai-layers/README.md), and used here with the same meaning:
[OBO](../ai-layers/README.md), [inference](../ai-layers/README.md) and [harness](../ai-layers/README.md).
