# Identity and credentials for a fleet of agents

Part 5 of [the software factory, rethought for agents](README.md). For security and platform teams, and for the tech
leads who give agents access to the code, the tracker and the wiki.

> **Last checked: 2026-11-12.** Products, plans and limits change every few months. Every product fact below cites
> the vendor page it comes from; each was read on 2026-11-11 or 2026-11-12. The full notes, with quotes, are in
> [sources/identity-notes.md](sources/identity-notes.md). Re-check them before you decide anything.

**TL;DR**

- One developer can start about a hundred agents and sub-agents in a day. The tools they touch authenticate
  **people**: a directory, single sign-on (SSO), a seat, a personal access token.
- So an agent usually works with a person's token. It then reaches everything that person can reach, and the logs
  record its actions as that person's.
- You want three answers at any time: **who did what and when**, **who can reach what**, and **whom you stop** when
  something goes wrong, without stopping the person's other ninety-nine agents.
- Code hosts already offer identities that are not people: workflow and job tokens, app installation tokens, bot
  users and service accounts, short-lived cloud credentials through OIDC. Trackers and wikis offer fewer.
- The harness gives every agent an id in its claims, commits and pull requests. That is traceability by convention:
  the harness issues and revokes no credential.

## 1. The problem

A token is how a tool knows who is calling. Most tools issue tokens to people, because people are what the directory
holds and what the seat licence counts. An agent that is handed a person's token inherits three things:

| What it inherits | Consequence for a fleet |
|---|---|
| Everything the person can reach | A docs agent with the developer's token can also push to every repository and edit every ticket the developer can |
| The person's name in the logs | The audit trail says "the developer did it", for a hundred agents at once |
| The person's off switch | Revoking the token stops every agent that shares it, and the person's own scripts too |

GitHub states the first point plainly: personal access tokens "are tied to the user who generated them", and "A token
cannot grant additional access capabilities to a user", so it can grant all of them
([GitHub, managing personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)).

What a fleet needs instead is close to "one agent, one task, one identity": an identity that reaches only what the task
needs, shows up in the logs as itself, expires with the task, and can be cut without touching the others. No product
read for this page offers exactly that for every tool. The sections below show how close each one gets.

![Person, orchestrator, agents and tools from left to right: the person is known to the company directory through SSO and a seat; the orchestrator is a long-lived agent session under the person's login to the agent vendor; each agent and sub-agent either borrows the person's token or gets its own identity (an app, a job token, a vendor proxy); the code host, tracker and wiki log the person, a bot user or an app, while the agent id only appears in the text; the harness writes an agent id in claims, commits, pull requests and the State, and issues and revokes no credential](../diagrams/factory-identity.svg)

## 2. How an agent reaches the code

| Credential | What it reaches | How it ends | What the logs show | Cost |
|---|---|---|---|---|
| **GitHub personal access token, classic** | Every repository the person can reach, "all repositories within the organizations that you have access to" | Expiry if one was set; revocation; organisations can restrict classic tokens; unused for a year: removed | The person | None beyond the person's seat |
| **GitHub personal access token, fine-grained** | One owner (a user or one organisation), chosen repositories, chosen permissions | Default 30 days; organisations can set a maximum lifetime, require approval, or block these tokens | The person | None beyond the seat. At most 50 per account |
| **GitHub workflow token** (`GITHUB_TOKEN`) | The repository of the workflow; permissions set per workflow or per job with `permissions` | When the job finishes, at most 6 hours on GitHub-hosted runners | To verify (the pages read do not say which actor it appears as) | None |
| **GitHub App installation token** | The repositories the installation was granted, narrowed per token to listed repositories (up to 500) and permissions | Expires after 1 hour; a new token is minted per run | The app, when it authenticates as an installation | No seat. Setup: create the app, keep its private key, mint tokens |
| **OIDC from a workflow** | A cloud provider's resources, when the token's claims (repository, ref, environment, workflow) match a trust rule | The cloud token is valid for a single job | The cloud side sees the claims of the workflow | Setup of a trust rule per cloud |
| **GitLab personal access token** | What the person can reach, within the token's scopes | 365 days by default and at most, unless an administrator lifts the requirement; revocation | The person | None beyond the seat |
| **GitLab project or group access token** | One project, or one group and its projects, with a role and scopes | 365 days by default; revocation; the bot user is deleted 30 days after its last token ends | A bot user created for the token | Bot users do not count toward the licence; on GitLab.com, Premium or Ultimate |
| **GitLab service account** | What its role in each group or project allows | Its tokens can have no expiry if expiry is not required; revoke the tokens or delete the account | A service account, listed as such | No seat; Free tier on GitLab.com: up to 100 per top-level group |
| **GitLab job token** (`CI_JOB_TOKEN`) | The same access level as the user who triggered the pipeline, limited to an allowlist of projects (by default the project itself) and to some endpoints | When the job finishes | An authentication log lists which projects used a job token on yours | None |

Sources. GitHub, read 2026-11-11:
[personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens),
[`GITHUB_TOKEN`](https://docs.github.com/en/actions/concepts/security/github_token),
[`permissions` in workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[authentication with a GitHub App](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app),
[installation access token](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app),
[when to build a GitHub App](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/deciding-when-to-build-a-github-app),
[OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect). GitLab, read 2026-11-11:
[personal access tokens](https://docs.gitlab.com/user/profile/personal_access_tokens/),
[project access tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/),
[group access tokens](https://docs.gitlab.com/user/group/settings/group_access_tokens/),
[service accounts](https://docs.gitlab.com/user/profile/service_accounts/),
[job token](https://docs.gitlab.com/ci/jobs/ci_job_token/).

Three points the table does not show:

- **SSO does not make a token less personal.** In a GitHub organisation that uses SAML SSO, a classic token must be
  authorised for that organisation after it is created; a fine-grained token is authorised when it is created. Either
  way it stays the person's token, and its authorisation ends when an owner revokes it or the person leaves the
  organisation ([GitHub, authorising a token for SSO](https://docs.github.com/en/enterprise-cloud@latest/authentication/authenticating-with-single-sign-on/authorizing-a-personal-access-token-for-use-with-single-sign-on),
  read 2026-11-11).
- **The audit log can name the token, not the agent.** GitHub's enterprise audit log records `hashed_token` (the
  SHA-256 of the token used), `programmatic_access_type` and `token_scopes`, for personal tokens, OAuth tokens and
  GitHub Apps. You search by the hash of a token you already hold; Git events are not returned by search and must be
  exported ([GitHub, identifying events performed by an access token](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/identifying-audit-log-events-performed-by-an-access-token),
  Enterprise Cloud documentation, read 2026-11-11). So one token per agent makes the log answer "which agent"; one
  token shared by a fleet does not.
- **GitLab logs the life of a token more than its use.** Its audit events include `personal_access_token_created` and
  `_revoked`, project and group token creation and deletion, and `service_account_created`; for API calls only "A
  subset of API requests authenticated by a token with an audited scope". Saving most events needs Premium or
  Ultimate ([GitLab, audit event types](https://docs.gitlab.com/user/compliance/audit_event_types/), read
  2026-11-11).

GitHub's own advice for automation points the same way as this page: "To access resources on behalf of an
organization, or for long-lived integrations, you should use a GitHub App", and "GitHub Apps are not tied to a user
account and do not consume a seat" (both pages above).

## 3. A vendor-managed connection: the agent never holds the token

A cloud agent can reach a repository without the raw token ever entering its machine. Claude Code cloud sessions are
one documented example (read 2026-11-12):

- GitHub is connected either through the Claude GitHub App (public repositories, and private ones the app is
  installed on) or with `/web-setup`, which sends the person's local `gh` token to their Claude account
  ([Use Claude Code in the cloud](https://code.claude.com/docs/en/claude-code-on-the-web)).
- "your GitHub credentials stay encrypted on Anthropic's servers and never enter a session's VM." The git client in
  the session holds "a scoped credential, which the proxy verifies and swaps for your actual GitHub token"
  ([cloud environments, GitHub proxy](https://code.claude.com/docs/en/cloud-environments)).
- The proxy serves the API only for the repositories attached to the session, refuses branch deletions and tag
  pushes, and "doesn't limit which branches a push can update": branch protection or rulesets do that (same page).
- Keys for other APIs can be stored as network secrets, which the vendor's proxy adds "after each request leaves the
  session's VM, so the key itself stays outside the VM" (same page).
- What it does not change: the identity behind the proxy is still the person's token or the app. Replies the agent
  posts on review threads "appear under your username", labelled as coming from Claude Code
  ([Use Claude Code in the cloud](https://code.claude.com/docs/en/claude-code-on-the-web)).

This removes the leak of a pasted token and narrows what one session reaches. It does not give each agent its own name
in GitHub's logs.

## 4. Trackers and wikis

| Tool | How a non-human gets access | Token | What the trail records |
|---|---|---|---|
| **GitHub Issues** | The same credentials as the code (§2); fine-grained tokens have an "Issues" repository permission | As in §2 | As in §2 |
| **GitHub wiki** | To verify: the permissions page lists no wiki permission | | |
| **GitLab issues and wiki** | Project or group access token ("authenticated access to a specific project", or a group and its projects), service account; per-feature limits not checked | As in §2 | Contributions belong to the bot user; token events as in §2 |
| **Jira, Confluence (Cloud), as a person** | The person's API token, with scopes (recommended) or without | Basic authentication with the person's email and the token; 1 to 365 days, one year by default | The pages read do not say; to verify |
| **Jira, Confluence (Cloud), service account** | A service account created in Atlassian Administration; five free per organisation, more with Atlassian Guard | An API token (scopes fixed at creation, 1 to 365 days, revocation takes up to 10 minutes) or OAuth 2.0 client credentials (scoped, access token valid 60 minutes) | The pages read do not say; to verify |
| **Jira, Confluence (Cloud), OAuth app** | An app that acts "on a user's behalf" after the user's consent; the user's permissions always constrain it | Access token plus rotating refresh tokens, which expire after 90 days of inactivity by default | Admins "can see who authorized the app and when" |

Sources, read 2026-11-12 unless noted:
[GitHub, permissions for fine-grained tokens](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens);
GitLab pages of §2 (2026-11-11);
[Atlassian, API tokens of an account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
(2026-11-11),
[API tokens for service accounts](https://support.atlassian.com/user-management/docs/manage-api-tokens-for-service-accounts/),
[OAuth 2.0 credentials for service accounts](https://support.atlassian.com/user-management/docs/create-oauth-2-0-credential-for-service-accounts/),
[OAuth 2.0 (3LO) apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/). Atlassian Data
Center has its own service accounts with OAuth 2.0 client credentials
([service accounts overview](https://confluence.atlassian.com/enterprise/service-accounts-overview-1627095923.html),
2026-11-11). Whether Atlassian Cloud service accounts take a seat, and what the audit log records per API call, were
not found in the pages read.

## 5. What the harness does, and what it cannot do

What it does, without any identity provider:

| Question | What answers it | Where |
|---|---|---|
| Who did what, and when | Every agent has an id `<project>.<orchestrator>.<role>.<target>`, written in its claim (`/claim <id>`), its PR (`Claim: <id>`), its commits (trailer `Agent: <id>`) and its comments | [ORCHESTRATION §7](../ORCHESTRATION.md#7-naming-agents-who-for-whom-on-what), [CONVENTIONS §GitHub comments](../CONVENTIONS.md#github-comments) |
| Which agent holds which task | The State lists the children from the `/claim <id>` comments and the `Claim:` lines of open PRs | [ORCHESTRATION §8](../ORCHESTRATION.md#8-orchestrator-memory-one-state-the-rest-is-a-log), `scripts/orch-state.py` |
| Who let a change in | The merge gate requires, among others, an adversarial verdict naming the head sha and the body lines (issue, claim, docs), and prints the sha to merge | [CONVENTIONS §Pull requests](../CONVENTIONS.md#pull-requests), `scripts/merge-gate.py` |
| Who can reach what | A child inherits only pre-approved tools; a cloud session's GitHub access covers only the repositories attached to it | [ORCHESTRATION §4](../ORCHESTRATION.md#4-child-sessions-orchestrator) |
| Whom to stop | The watchdog stops a child with no commit and no comment for 30 minutes, or one that repeats a failing command three times, and releases its issue | [ORCHESTRATION §4](../ORCHESTRATION.md#4-child-sessions-orchestrator) |
| Where secrets live | Never in the repository or the chat: GitHub secrets, a vault, or a cloud environment's network secrets; a secret goes only to the job that needs it, never on a fork event | [CI-BUDGET §3](../CI-BUDGET.md#secrets-and-variables-nothing-hard-coded), [CONVENTIONS §Secrets](../CONVENTIONS.md#secrets) |

What it cannot do:

- **It issues and revokes nothing.** It has no token of its own to hand out. The scripts use whatever `GH_TOKEN` or
  `GITHUB_TOKEN` the session has (headers of `scripts/merge-gate.py` and `scripts/orch-state.py`).
- **The agent id is text, not an identity.** The code host still logs the person, the app or the bot behind the
  token. Anyone holding the token could write any `Agent:` trailer; the id is as trustworthy as the session that
  writes it.
- **It does not know whether a session is alive.** The State reads visible claims only; the orchestrator checks
  sessions with its own tools (header of `scripts/orch-state.py`).
- **Stopping an agent means stopping its session**, through the agent vendor's tools. If the agent used a shared
  token, the only credential-level stop is to revoke that token, which stops every agent that shares it.

## 6. Choosing a credential for "one agent, one task"

| Situation | Credential that fits | Why | Reasonable alternative |
|---|---|---|---|
| An agent in CI that touches only its own repository | The workflow or job token, with minimal `permissions` | Created per job, scoped to the repository, gone at the end of the job | None needed |
| A fleet that opens PRs and comments across an organisation's repositories | A GitHub App, one installation token per agent run, narrowed to the task's repositories and permissions | Its own name in the logs, a 1-hour token, no seat; on Enterprise Cloud the token hash identifies the run in the audit log | A fine-grained token per agent, short expiry, organisation approval required |
| A cloud agent started by a person | The vendor's proxy with the app connection, plus branch protection on the code host | No raw token in the agent's machine; the session reaches only attached repositories | `/web-setup` with the person's token, accepting that the logs show the person |
| An agent that deploys to a cloud | OIDC from the workflow, with a trust rule on repository, ref and environment | No long-lived cloud secret stored anywhere | A cloud secret in the CI's secret store, given only to the deploy job |
| GitLab | A project access token or a service account per kind of agent, with a short expiry | A bot user or service account in the logs, no seat | The job token inside pipelines |
| Jira or Confluence | A service account with a scoped API token or OAuth client credentials | Not a person, scopes fixed, short access tokens with OAuth | An OAuth app acting for the person, when the action must stay the person's |
| Any tool that only knows people | A dedicated, scoped, short-lived token of a person, one per agent, stored in a secret store | At least the log names the token, and revoking it stops only that agent | Do the step by hand, or through a tool that has a non-human identity |

Questions to ask a vendor before giving it to a fleet:

- Can a non-human hold its own identity (app, bot, service account), and does it take a seat?
- Can a token be narrowed to one project and a few permissions, and limited to hours rather than months?
- Does the audit log record which token made each call, including API reads, and can it be exported?
- Can one token be revoked without touching the others, and how long does revocation take?
- Can the credential stay outside the agent's machine (a proxy, a broker), so it is never pasted into a chat or a
  repository?

None of these choices needs a secret in a chat or a repository: a token is created in the tool's settings and placed in
a secret store, a CI secret or a cloud environment's network secrets, never in the conversation
([CI-BUDGET §3](../CI-BUDGET.md#secrets-and-variables-nothing-hard-coded)).
