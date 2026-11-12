# Research notes: identity and credentials for a fleet of agents (#86)

Working notes behind [identity.md](../identity.md). Every fact below was read on the vendor page linked, on the date
given. "Not on the page" means the page was read and did not say it; it is not a claim that the product lacks it.
Quotes are the vendor's words.

## GitHub

### Personal access tokens (classic and fine-grained)

Source: [Managing your personal access tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens),
read 2026-11-11.

- Two types: fine-grained and classic; GitHub recommends fine-grained where possible.
- "A token cannot grant additional access capabilities to a user"; both types "are tied to the user who generated
  them" and stop working for a resource when that user loses access to it.
- Fine-grained: one resource owner (a user or one organisation), a choice of repositories, specific permissions.
  At most 50 fine-grained tokens per account. Default lifetime 30 days; "Infinite lifetimes are allowed but may be
  blocked by a maximum lifetime policy."
- Classic: reaches every repository the user can reach; a classic token "will grant access to all repositories
  within the organizations that you have access to." GitHub recommends setting an expiration.
- "GitHub automatically removes personal access tokens that haven't been used in a year."
- Organisation controls: "Organization owners can require approval for any fine-grained personal access tokens"
  that can access the organisation (pending tokens read public resources only); organisations can block
  fine-grained tokens; "Organization owners can set a policy to restrict the access of personal access tokens
  (classic) to their organization."
- Fine-grained limits listed on the page: no contribution to public repositories where the user is not a member, no
  outside-collaborator repositories, one organisation at a time, no Packages, no Checks API, no user-owned Projects.
- "To access resources on behalf of an organization, or for long-lived integrations, you should use a GitHub App."
- Machine users / bot accounts: not on the page.

### SAML single sign-on and tokens

Source: [Authorizing a personal access token for use with single sign-on](https://docs.github.com/en/enterprise-cloud@latest/authentication/authenticating-with-single-sign-on/authorizing-a-personal-access-token-for-use-with-single-sign-on)
(Enterprise Cloud docs), read 2026-11-11.

- "You must authorize your personal access token (classic) after creation before the token can access an
  organization" that uses SAML SSO.
- "Fine-grained personal access tokens are authorized during token creation, before access to the organization is
  granted."
- Authorisation lasts "until revoked", among others by an owner revoking it or by the user being removed from the
  organisation.

### The workflow token (`GITHUB_TOKEN`)

Sources, read 2026-11-11:
[GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token),
[Use GITHUB_TOKEN for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token),
[Controlling permissions for GITHUB_TOKEN](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/controlling-permissions-for-github_token).

- "At the start of each workflow job, GitHub automatically creates a unique `GITHUB_TOKEN` secret"; it "is a GitHub
  App installation access token."
- Expires "when the job finishes or after its effective maximum lifetime": 6 hours on GitHub-hosted runners, up to
  24 hours (refreshed) on self-hosted runners.
- "The token's permissions are limited to the repository that contains your workflow."
- Permissions set with the `permissions` key, for the workflow or per job; "grant the `GITHUB_TOKEN` the least
  required access."
- Events it triggers do not start new runs, except `workflow_dispatch` and `repository_dispatch`; `pull_request`
  opened/synchronize/reopened runs need approval.
- Not on these pages: the default permission level, and the identity (e.g. `github-actions[bot]`) that its actions
  are attributed to. To verify.

### GitHub Apps and installation tokens

Sources, read 2026-11-11:
[About authentication with a GitHub App](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/about-authentication-with-a-github-app),
[Generating an installation access token](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app),
[Generating a JWT for a GitHub App](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app),
[Deciding when to build a GitHub App](https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/deciding-when-to-build-a-github-app).

- Three ways to authenticate: as the app (JWT), as an installation (installation access token), on behalf of a user
  (user access token). "authenticate as an app installation when you want to attribute app activity to the app";
  "on behalf of a user when you want to attribute app activity to a user."
- JWT: "must be signed using the `RS256` algorithm"; needs the app's private key and ID; `exp` "no more than 10
  minutes into the future."
- Installation token: "will expire after 1 hour." Can be narrowed with `repositories` / `repository_ids` (up to 500)
  and `permissions`; cannot exceed what the installation or the app was granted.
- A stateless token format (`ghs_APPID_JWT`) began rolling out on 2026-04-27; code that assumes 40-character tokens
  may break.
- "GitHub Apps are not tied to a user account and do not consume a seat." "A GitHub App installed on an organization
  is not dependent on a user." "GitHub Apps use short lived tokens."
- Private key storage advice: not on these pages.

### OIDC for workflows

Source: [OpenID Connect](https://docs.github.com/en/actions/concepts/security/openid-connect), read 2026-11-11.

- OIDC "allows your workflows to exchange short-lived tokens directly from your cloud provider"; "You won't need to
  duplicate your cloud credentials as long-lived GitHub secrets."
- The cloud provider checks "if the OIDC token's subject and other claims are a match" for its trust conditions.
  Example claims: `sub` (`repo:octo-org/octo-repo:environment:prod`), `repository`, `ref`, `environment`,
  `job_workflow_ref`, `actor`.
- The cloud token is "only valid for a single job, and then automatically expires."
- Repositories created after 2026-07-15 use an immutable default `sub` format with owner and repository IDs.
- Not on this page: the `id-token: write` permission, the OIDC token's lifetime.

### Audit log: which token did it

Source: [Identifying audit log events performed by an access token](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/identifying-audit-log-events-performed-by-an-access-token)
(Enterprise Cloud docs, enterprise audit log), read 2026-11-11.

- Fields: `hashed_token` ("SHA-256 hash of the token used for authentication"), `programmatic_access_type` ("Type of
  authentication used"), `token_scopes`.
- Search with `hashed_token:"VALUE"` in the UI or the REST API; you need the token's SHA-256 hash first.
- Covers personal access tokens, OAuth tokens, GitHub Apps (as an installation or on behalf of a user), deploy keys,
  SSH keys.
- "Searches using GitHub do not return Git events" (export the log); token data for Git events, SSH and deploy keys
  is in public preview.

### More on the workflow token (`permissions`)

Source: [Workflow syntax, `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
read 2026-11-11 (first 100,000 characters of the page).

- "If you specify the access for any of these permissions, all of those that are not specified are set to `none`."
- "Fetch an OpenID Connect (OIDC) token. This requires `id-token: write`."
- The starting permissions come from the enterprise, organisation or repository default; "If the default is set to
  the restricted permissions at any of these levels then this will apply."
- Workflows triggered by Dependabot "use a read-only `GITHUB_TOKEN` and cannot access secrets other than Dependabot
  secrets."

## GitLab

### Personal access tokens

Source: [Personal access tokens](https://docs.gitlab.com/user/profile/personal_access_tokens/), read 2026-11-11.

- "attached to a user rather than a group or project"; permissions come from that user's account. Free, Premium,
  Ultimate.
- "If you do not enter a date, the expiry date is set to 365 days from today." "By default, the expiry date cannot
  be more than 365 days from today." (400 days behind a feature flag, off by default.)
- "By default, new access tokens must have an expiry date." "If an administrator turns off this requirement, new
  tokens created without an expiry date never expire." Administrator maximum lifetime: Ultimate (GitLab 17.6+).
- "Revoke a token to immediately invalidate it and prevent further use." "GitLab retains the token for audit
  purposes." Blocking or deleting an enterprise user revokes their tokens.
- For pipelines "CI/CD job tokens are recommended instead"; for project automation, project access tokens "with
  minimal required permissions."

### Project and group access tokens

Sources: [Project access tokens](https://docs.gitlab.com/user/project/settings/project_access_tokens/),
[Group access tokens](https://docs.gitlab.com/user/group/settings/group_access_tokens/), read 2026-11-11.

- "When you create a project access token, GitLab creates a bot user and associates it with the token" (same for
  group tokens). "Their contributions are associated with the bot user account"; a removed bot's contributions move
  to a ghost user.
- A project token cannot reach other projects nor create other tokens. A group token covers the group and its
  projects. Permissions follow "the role and scope of the associated access token."
- Bot users "do not count towards your license limit."
- "On GitLab.com, project access tokens require a Premium or Ultimate subscription" (trial: one project token);
  self-managed and Dedicated: any licence. Same for group tokens.
- Expiry 365 days by default; reminders at 60, 30, 7 days. "By default, GitLab deletes a bot user and all of its
  tokens 30 days after the last of those tokens is revoked or expires."

### Service accounts

Source: [Service accounts](https://docs.gitlab.com/user/profile/service_accounts/), read 2026-11-11.

- "Service accounts are user accounts that represent non-human entities rather than individual people." Instance,
  group or project level; created by an administrator, a group Owner or a project Maintainer/Owner (details differ
  between GitLab.com and self-managed).
- Free, Premium, Ultimate; Premium and Ultimate: unlimited; GitLab.com Free: up to 100 per top-level group.
- "They do not use a seat"; "always marked as external users"; "They cannot sign in to GitLab through the UI."
- "Service accounts authenticate with a personal access token." "If expiration dates are not required, the token is
  created with no expiry date." Fine-grained token enforcement "does not apply to service account tokens."
- Listed in membership lists "as service accounts, not as regular users."
- Deleting one moves its contributions to a ghost user; revoking its tokens cuts access without deleting it.

### CI/CD job token

Source: [CI/CD job token](https://docs.gitlab.com/ci/jobs/ci_job_token/), read 2026-11-11.

- Made available to the job as `CI_JOB_TOKEN`. "The token is valid only while the job is running."
- "The token receives the same access level as the user that triggered the pipeline" (a push, a manual job, or the
  owner of a scheduled pipeline).
- "By default, the allowlist of any project only includes itself." Adding a group to the allowlist covers all its
  projects and subgroups. Fine-grained permissions can limit the token to a set of REST endpoints.
- An authentication log in the project shows which other projects authenticated with a job token (up to 5 minutes
  delay).

### Audit events for tokens

Source: [Audit event types](https://docs.gitlab.com/user/compliance/audit_event_types/), read 2026-11-11.

- `personal_access_token_created`, `personal_access_token_revoked`; `project_access_token_created` / `_deleted`;
  `group_access_token_created` / `_deleted` (and `_creation_failed`, `_deletion_failed`); `service_account_created`
  (no deletion event listed); `user_authenticated_using_job_token` (not saved to the database);
  `secure_ci_job_token_*` events for allowlist changes; `api_request_access_with_scope` ("A subset of API requests
  authenticated by a token with an audited scope").
- Saving most events to the database: Premium and Ultimate; streaming: Ultimate.

## Atlassian (Jira, Confluence)

### API tokens of a person

Source: [Manage API tokens for your Atlassian account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/),
read 2026-11-11.

- Used to "authenticate a script with an Atlassian cloud app"; "You generate the token from your Atlassian account,
  then copy and paste it into a script." Main use: REST APIs "using HTTP basic authentication" with the account's
  email and the token.
- "The scope for an API token defines the levels of access to data in your Jira and Confluence apps." "We recommend
  you create an API token with scopes because it's more secure." Tokens without scopes remain for apps that do not
  support scoped tokens. Scoped tokens call `https://api.atlassian.com/ex/jira/{cloudId}` or `.../ex/confluence/{cloudId}`.
- "By default we set tokens to expire in one year." "Token expiration is 1 to 365 days." Tokens created before
  2024-12-15 were set to expire between 2026-03-14 and 2026-05-12.
- "When you revoke a token it no longer works and we permanently remove it from your account."
- The page does not say whether the token carries all the account's permissions, nor whether admins can see or revoke
  a user's tokens.
- Service accounts: "You must create a service account before you can create a token for the service account."

### Service accounts (Data Center)

Source: [Service accounts overview](https://confluence.atlassian.com/enterprise/service-accounts-overview-1627095923.html)
(Data Center documentation), read 2026-11-11.

- "A service account is a special type of Data Center account that isn't tied to a person." Credentials: "a client
  ID and client secret", "OAuth 2.0 client credentials flow". Seats, attribution and audit: not on the page.
