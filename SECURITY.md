# Security

## Supported versions
The latest tagged version (`vX.Y.Z`, see [CHANGELOG](CHANGELOG.md)) and the `master` branch. Earlier versions get
no fix: the answer is to move to the latest ([ADOPTION](docs/ADOPTION.md) §Updates).

## Reporting a vulnerability
**In private, never in an issue, a PR or a public discussion.**

- [Open a private report](https://github.com/francoisgn/belayline-agentic-harness/security/advisories/new) (the
  repository's Security tab → "Report a vulnerability";
  [GitHub docs](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)).
- Include: the version or the commit, the file concerned, the steps to reproduce, the effect (what an attacker
  gets), and a fix if you have one. No real secret in the report.

## What to expect
- Acknowledgement within **7 days**.
- Then: confirmation or a reasoned refusal, then a fix in a new version and a published advisory, with your name
  if you wish. The project is maintained in spare time: no guaranteed delay for the fix.
- Please disclose nothing before the fix is published.

## Scope
| In scope | Examples |
|---|---|
| Guardrails | `plugins/harness/scripts/guard-git.py` bypassed (direct push or force-push to a protected branch) |
| Scripts | `scripts/harness-sync.sh` writing outside the target repository; `scripts/repo-settings.py` applying more than the file |
| Reusable workflows | `.github/workflows/*.yml`: injection through a title, a body or a comment; token too broad; secret leak |
| Skills, agents, templates | an instruction that makes an agent follow the text of an issue, a PR or a log as an instruction |

Out of scope: the projects that use the harness (report them to their maintainers), the coding agents and
third-party services themselves (report them to their vendor), reports from automatic tools without an exploitation
scenario.
