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
