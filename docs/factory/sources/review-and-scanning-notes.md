# Research notes for part 3, review and scanning

Working notes behind [review-and-scanning.md](../review-and-scanning.md) (issue
[#84](https://github.com/francoisgn/belayline-agentic-harness/issues/84)). Each fact names the page it was read on and
the date. Quotes are as the page gave them on that date. A page that could not be opened is marked "not opened".
These notes are kept for later articles; the page itself only uses what it needs.

## GitHub

### AI Scan (overview)

Page: [About AI Scan](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan), read 2026-11-11.

- AI Scan for repositories: "AI Scan for repositories is in public preview and subject to change." It "scans a
  repository's default branch on demand across all languages." "Users with write access run scans on demand."
  "Findings are added to your code scanning backlog alongside CodeQL alerts". It "can find additional
  vulnerabilities in languages CodeQL already analyzes."
- AI Scan for pull requests: "finds security vulnerabilities in pull request changes for selected languages and
  frameworks not covered by CodeQL." "Examples include PHP and Terraform configuration (HCL)." "When enabled, it
  scans eligible pull requests when they are created and after each new commit."
- Scan for AI applications: "finds security risks in AI applications and agents in pull requests, initially focusing
  on indirect prompt injection." Scans "when they are created and after each new commit." "Findings appear as
  comments on the pull request."
- "Each feature has its own coverage, availability, and billing requirements" (details in the linked articles).
- Policy: "a shared AI Scan policy controls whether organizations can enable these features." "Allowing AI Scan does
  not automatically enable any feature." "Organizations enable each feature separately, and repository
  administrators can opt out for each feature independently."
- The overview page does not say where code is sent or processed.

### AI Scan for repositories

Page: [AI Scan for repositories](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan-for-repositories),
read 2026-11-11.

- "AI Scan for repositories is in public preview and subject to change."
- "Scans analyze the default branch only." "AI Scan for repositories supports all languages, including languages
  already supported by CodeQL."
- "Scans are manually triggered. Scheduled scans and automatic scans on push are not supported."
- "A scan does not exhaustively analyze every file or guarantee that it finds every vulnerability."
- Availability table: organization public repository "Available without an active-committer license"; organization
  private or internal "Available with GitHub Code Security or GitHub Advanced Security"; personal public
  "Available"; personal private "Not available". "You do not need a GitHub Copilot license."
- Billing: "each scan consumes Code Security AI credits." "This usage is separate from active-committer licensing."
- Limits: "Detection steps are limited to 30 minutes and 150,000 AI credits." "Self-hosted runners are not
  supported."
- Engine: "uses a proprietary harness that leverages multiple models, when available." Where code is processed: not
  stated.
- Findings: alerts in the code scanning alert list, filterable by the AI Scan tool. "The alert will only close
  automatically if the applied fix changes the exact line of code that triggered the alert."

### AI Scan for pull requests

Page: [AI Scan for pull requests](https://docs.github.com/en/code-security/concepts/code-scanning/ai-powered-security-detections),
read 2026-11-11.

- Scope: "find security vulnerabilities in pull requests for languages and frameworks not covered by CodeQL."
  "Examples include PHP, Shell/Bash, Terraform configuration (HCL), Dockerfiles, JSP for Java, and Blazor for C#."
  Supported languages "may change as the feature evolves."
- Trigger: "Scans run when a pull request is created and after each new commit, as they do for CodeQL." Not on
  pull requests from forks or Dependabot. Needs code scanning enabled and the AI Scan on pull requests setting; does
  not need CodeQL default setup. "Enabling the organization setting enables AI Scan immediately for all eligible
  repositories where code scanning is enabled."
- Preview: neither "preview" nor "generally available" appears on this page (checked 2026-11-11). The overview page
  marks only AI Scan for repositories as public preview.
- Availability: same table as for repositories (organization private or internal: "Available with GitHub Code
  Security or GitHub Advanced Security"; personal private "Not available"). "You do not need a GitHub Copilot
  license to use AI Scan."
- Billing: "AI Scan usage is separate from active-committer licensing and is reported under the Code Security AI
  creditss SKU" (sic). "Usage begins only when a qualifying pull request is scanned." "If the billing account
  receives included AI credits through a GitHub Copilot entitlement, AI Scan uses those credits first." After that,
  usage is metered under budgets. "If a hard budget leaves no Code Security AI credits available, AI Scan cannot
  produce findings." "Repository administrators can then opt out, but qualifying pull requests can consume Code
  Security AI Credits before they do."
- Limits: "AI Scan findings cannot yet be used in rulesets to enforce merge requirements." "Self-hosted runners are
  not supported." "As with any AI-based tool, AI Scan findings may include false positives."
- Findings: labelled "AI", on the Conversation and Files changed tabs. "When available, Copilot Autofix recommends a
  code change, as it does for CodeQL alerts." It "may use code search to gather more context from the repository"
  and "uses specialized prompts, not custom instruction files such as `/.github/copilot-instructions.md` or
  `/CLAUDE.md`."

### AI applications scanning for pull requests

Page: [AI applications scanning for pull requests](https://docs.github.com/en/code-security/concepts/code-scanning/ai-applications-scanning-for-pull-requests),
read 2026-11-11.

- "AI applications scanning is currently in public preview and subject to change."
- Risk types named: indirect prompt injection, sensitive information disclosure, excessive agency. "During public
  preview, AI applications scanning only detects indirect prompt injection (XPIA) vulnerabilities in AI agents."
- "Because it doesn't rely on static analysis built for specific languages, it has no language or framework
  limitations."
- "Scans run when a pull request is created and after each new commit." Not on fork or Dependabot pull requests. No
  backlog scan.
- Off by default at enterprise, organization and repository level; enterprise policy, organization setting "Scan for
  AI applications", repository opt-out. Enabling AI Scan for pull requests does not enable it.
- Billing: "Using AI applications scanning requires a GitHub Advanced Security license and consumes AI credits on top
  of that license." "Eligible public repositories are also included in this billing requirement."
- Findings advisory: "They don't block a pull request from being merged." Cannot be used in rulesets. Shown as pull
  request comments with an "AI app" label. "Copilot Autofix suggestions are generated automatically for findings
  from this detector." "This behavior is independent of the Code Scanning Autofix setting".

### Code scanning (CodeQL)

Page: [About code scanning](https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning),
read 2026-11-11.

- "You can configure code scanning to use the CodeQL product maintained by GitHub or a third-party code scanning
  tool." Third-party tools that output SARIF.
- Runs on a schedule or on an event "such as a push".
- "If you want to use code scanning on private repositories, you need a GitHub Code Security license."
- "Code scanning uses GitHub Actions, with each workflow run consuming GitHub Actions minutes."

### Products: GitHub Advanced Security

Page: [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security),
read 2026-11-11.

- Two paid products: GitHub Secret Protection and GitHub Code Security. Purchase needs GitHub Team or GitHub
  Enterprise.
- Secret Protection lists: secret scanning, push protection, AI-detected secrets, custom patterns, delegated bypass
  for push protection, delegated alert dismissal, security campaigns, security overview.
- Code Security lists: code scanning, CodeQL CLI, Copilot Autofix, AI Scan, security campaigns, custom auto-triage
  rules for Dependabot, dependency review, security overview.
- "Some features are enabled for public repositories by default" (code scanning and secret scanning given as
  examples). Dependency graph and Dependabot alerts are included in all plans.
- Billing model not described on this page (links to a billing page).

### Features available on every plan

Page: [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features),
read 2026-11-12.

- "The following security features are available for you to use, regardless of the GitHub plan you are on": dependency
  graph, Dependabot alerts, Dependabot security updates ("choose whether to have pull requests generated automatically
  to update these dependencies"), Dependabot version updates ("automatically raise pull requests to keep your
  dependencies up-to-date"), push protection for users ("automatically protects you from accidentally committing
  secrets to public repositories"), security advisories.
- Secret scanning, listed under GitHub Secret Protection: "Available for public repositories by default."
- Secret Protection and Code Security are for "accounts on GitHub Team and GitHub Enterprise Cloud".

### Copilot code review

Page: [GitHub Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review), read 2026-11-11.

- "Copilot reviews your pull requests, identifies issues, and suggests fixes you can apply in a couple of clicks."
- Plans: automatic reviews on "the Copilot Pro, Copilot Pro+, and Copilot Max plans"; reviews for members without a
  license: "available to organizations on Copilot Business and Copilot Enterprise plans"; "the Copilot Free plan,
  which does not include Copilot code review."
- Trigger: "By default, Copilot only reviews a pull request if you assign it to the pull request." "Repository owners
  can configure Copilot to automatically review all pull requests in the repository". Rulesets and user settings
  are two separate configurations, "not hierarchical". "Unless Copilot has been configured to review each push to a
  pull request, it will only review a pull request once." Option "Review new pushes".
- Billing: "Each time Copilot reviews a pull request or reviews code in your IDE, the interaction consumes AI
  credits." Two cost components: AI credits and GitHub Actions minutes for agentic work. "Self-hosted runners do not
  consume GitHub Actions minutes."
- "By default, Copilot's reviews do not count toward required approvals for the pull request." (Can be enabled.)
- Custom instructions: "short, natural-language statements that you write and store as one or more files in a
  repository."
- Preview: "Max review effort level is currently in public preview and subject to change." "Passing suggestions to
  Copilot cloud agent is in public preview and subject to change." Azure DevOps support "(public preview)".
- "Copilot is not guaranteed to spot all problems or issues in a pull request." Excludes dependency files, log files,
  SVG files.
- Related on the same page: GitHub Code Quality offers "Optional merge gating with rulesets, so pull requests with
  unresolved rules-based findings" can be blocked (not researched further).

### Copilot Autofix and agentic autofix

Pages: [About autofix for code scanning](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning),
[Managing access to agentic autofix](https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-code-scanning-alerts/managing-access-to-agentic-autofix-for-code-scanning),
[Application card: GitHub security and quality AI features](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning),
read 2026-11-11.

- Two features, as named by the docs. "Use agentic autofix when you want Copilot to investigate and fix one or more
  alerts for you, end to end." "Use Copilot Autofix when you want a single suggested code change for one alert that
  you review and apply yourself."
- Copilot Autofix: "available to all public repositories on GitHub.com", and to private or internal repositories with
  GitHub Code Security. "Copilot Autofix suggested fixes don't consume AI credits." "Copilot Autofix is available for
  CodeQL analysis and does not require a GitHub Copilot subscription." "allowed by default and enabled for every
  repository using CodeQL". "Copilot Autofix uses a generative model that is non-deterministic." "You must always
  review suggestions from Copilot Autofix and edit changes as needed before accepting them."
- Agentic autofix: on an organization repository "an organization owner or security manager must enable it"; not for
  repositories owned by Enterprise Managed Users. "Each agentic autofix agent session consumes AI credits and GitHub
  Actions minutes." "Agentic Autofix works on a best-effort basis." "Copilot validates fixes by re-running CodeQL with
  the code scanning query suite." It "can't confirm fixes for alerts from custom CodeQL queries, the
  `security-extended` CodeQL query suite", nor for third-party tool alerts. After enabling, "users with write access
  to the repository can assign code scanning alerts to Copilot." "If your organization used agentic autofix during
  the public preview, you must enable it again." The docs pages read do not state GA; a GitHub changelog titled
  "Agentic autofix for code scanning alerts general availability" (2026-10-15) appeared in search results, not opened.
- Search summary (not verified on a page): only default-branch backlog alerts can be assigned; up to 25 alerts per
  assignment from the backlog or a campaign.

### Secret scanning and push protection

Pages: [About secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning),
[About push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection),
read 2026-11-11.

- "Secret scanning automatically detects credential leaks so you can secure them before they're exploited." "scans
  your entire Git history on all branches of your repository", plus issues, pull request titles, descriptions and
  comments, discussions, wikis, secret gists.
- Public repositories: "Secret scanning runs automatically for free." Private and internal: "Available with GitHub
  Secret Protection enabled on GitHub Team or GitHub Enterprise Cloud."
- Push protection: "a secret scanning feature designed to prevent hardcoded credentials, such as secrets or tokens"
  from being pushed. Surfaces: command line, commits in the GitHub UI, file uploads, REST API requests, GitHub MCP
  server (public repositories only). Repository push protection "Requires GitHub Secret Protection to be enabled" and
  "Is disabled by default." User push protection "Stops you from pushing secrets to public repositories on GitHub."
  AI-detected secrets: public preview. "anyone with write access to the repository can bypass push protection by
  specifying a bypass reason"; delegated bypass available.

### Dependabot and dependency review

Pages: [About Dependabot alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts/about-dependabot-alerts),
[About dependency review](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/about-dependency-review),
read 2026-11-11.

- "Dependabot alerts help you find and fix vulnerable dependencies before they become security risks." Assigning
  alerts (to an agent) needs Code Security or Advanced Security, "including for public repositories"; the agent
  "opens a draft pull request with a proposed fix." "Dependabot doesn't scan archived repositories."
- "Dependency review helps you understand dependency changes and the security impact of these changes at every pull
  request." "By default, the dependency review action check will fail if it discovers any vulnerable packages." "The
  action is available for all public repositories", and private repositories with Code Security or Advanced
  Security. "Dependabot alerts will find vulnerabilities that are already in your dependencies."

### Security campaigns

Page: [About security campaigns](https://docs.github.com/en/code-security/concepts/security-at-scale/about-security-campaigns),
read 2026-11-12.

- "Security campaigns are a way to group alerts and share them with developers." Code scanning alerts: default branch
  only. "Campaigns for secret scanning alerts are currently in public preview and are subject to change."
- "For code scanning alerts, GitHub Copilot Autofix is automatically triggered to suggest a resolution." With agentic
  autofix, "you can select up to 25 code scanning alerts in a security campaign and assign them to Copilot." "One
  assignment starts one agent session and creates one pull request for the selected alerts."
- Plans: listed under both Secret Protection and Code Security on the Advanced Security page. Search summary (not
  verified on a page): limit of 10 active campaigns, 1000 alerts per campaign.
