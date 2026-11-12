# Review and scanning: the steps a factory with agents needs

Part 3 of [the software factory, rethought for agents](README.md). For tech leads and security leads who decide what
a change must go through before it merges.

> **Last checked: 2026-11-12.** Products, plans and preview labels change every few months. Every product fact below
> links the vendor page it comes from; the date each page was read is in [Sources](#sources). The full quotes behind
> each fact are kept in [the research notes](sources/review-and-scanning-notes.md). Re-check before you buy or
> enable anything.

**TL;DR**

- This is not a market comparison. It names the **nine steps** a change goes through, then shows that each step can be
  provided **three ways**: embedded in the platform that hosts the code, by an independent tool, or by an agent you
  write yourself. Products appear as examples of a way, never ranked.
- With agents, the question is less "which tool is best" than "which step, at which moment". A step that runs on
  every commit runs a hundred times a day when agents push.
- The harness runs the cheap deterministic checks before the push, its own reviewers before "Ready", and the paid or
  slow steps **once per ready head**, plus a weekly scan for what arrives without a commit.
- Two providers for one step at the same moment means paying twice and answering twice. Pick one per step.

![Review and scanning along the life of a change: four moments from left to right (before push on the developer's machine, draft PR, ready PR once per head, integration branch and weekly) and three lanes (embedded in the platform, independent tool, your own agent). Platform lane: push protection before push; AI Scan for pull requests and the AI applications scan on opening and on each commit; CodeQL, dependency review and Copilot code review on the ready PR; Dependabot alerts and on-demand AI Scan for repositories later. Tool lane: the local check with a secret hook before push; nothing costly on a draft; Semgrep, Trivy, gitleaks, zizmor, CodeRabbit or Sonar on the ready PR; the same scans weekly. Agent lane: adversarial review and compliance agents before Ready; the review service once per head. A note says the harness pushes often to a draft, reviews and scans once per ready head, runs the dependency scan weekly, one provider per step](../diagrams/review-scanning.svg)

## 1. The steps

Each step answers one question. "Moment" uses the stages of the diagram: before push (the developer's machine), draft
pull request, ready pull request, integration branch, schedule.

### Intent review

- **Looks at**: the issue (spec, error behaviours, definition of done) and the diff together.
- **Catches**: a change that compiles and passes its tests but does not do what was asked, or does more. **Misses**:
  anything the issue does not say; it is not a security scanner.
- **Moment**: before "Ready", and again when the head moves after an approval.
- **Needs**: a model other than the author's, isolated from the author's context
  ([REVIEW-ROUNDS](../REVIEW-ROUNDS.md#the-two-reviews)).

### Code review of the diff

- **Looks at**: the diff only. Is the code correct and clean?
- **Catches**: logic errors, missed cases, rule breaks a linter cannot see. **Misses**: whether the change is the
  right one (that is the intent review), and whatever the reviewer was not told about the project.
- **Moment**: ready pull request, once per head.
- **Needs**: a review service seat or app, or a model API secret in CI.

### Static analysis for vulnerabilities (SAST)

- **Looks at**: the source code, for patterns that lead to a vulnerability (injection, unsafe deserialisation…).
  **Rule-based** analysers apply written queries; **AI-based** ones ask a model.
- **Catches**: known vulnerability classes with a data path from input to sink. **Misses**: rule-based tools miss
  languages and frameworks they have no rules for; AI-based ones are not exhaustive and may report false positives
  (GitHub says both of its AI Scan, below).
- **Moment**: ready pull request and integration branch; on a schedule for new rules.
- **Needs**: a runner; for private repositories on a platform, a licence.

### Dependency analysis (SCA)

- **Looks at**: the declared and locked dependencies against advisory databases.
- **Catches**: a known vulnerable version. **Misses**: an unknown flaw, a malicious package without an advisory yet.
- **Moment**: ready pull request (new dependencies) and **every week**: a CVE is published without any commit.
- **Needs**: nothing beyond a runner for the open tools.

### Secret scanning

- **Looks at**: added text and history for tokens, keys and passwords.
- **Catches**: a credential committed by mistake. **Misses**: a secret in a format no pattern knows. A secret found
  after the push is already leaked: it must be revoked ([CI-BUDGET](../CI-BUDGET.md#3-security-baseline)).
- **Moment**: **before the push** (hook or push protection) first; then on the pull request and the history.
- **Needs**: nothing for gitleaks; a licence for platform scanning of private repositories.

### Risks specific to AI applications and agents

- **Looks at**: code that calls a model or runs an agent: what untrusted text reaches the prompt, and what the agent
  may do with tools. **Indirect prompt injection** is the case where an instruction hidden in data the agent reads
  (a web page, an issue, a file) is followed as if the user had given it.
- **Catches**: an agent that reads untrusted content and holds tools that can act on it. **Misses**: today's
  detectors cover a narrow set of risks (the GitHub one starts with indirect prompt injection only).
- **Moment**: ready pull request, when the diff touches model calls or agent tools.
- **Needs**: a dedicated detector, or a reviewer with a checklist for it.

### Quality gate

- **Looks at**: maintainability, test coverage of new code, duplication, reliability findings, against thresholds.
- **Catches**: a slow decay that no single review notices. **Misses**: correctness; a gate measures, it does not
  understand.
- **Moment**: ready pull request (gate on new code), integration branch (trend).
- **Needs**: a server or service account, and coverage reports from the tests.

### Compliance review against a named framework

- **Looks at**: the diff against the requirements of one framework (PCI DSS, ISO/IEC 27001, TISAX, GDPR…).
- **Catches**: a gap hypothesis: a card number in a log, a missing access log, customer data in a test.
  **Misses**: everything outside the code (processes, contracts); it is never a certification
  ([COMPLIANCE](../COMPLIANCE.md)).
- **Moment**: before "Ready", only when the diff touches the framework's scope.
- **Needs**: a framework owner who confirms (DPO, CISO, QSA), and a strong model.

### Workflow and configuration linting

- **Looks at**: CI workflows and tool configuration.
- **Catches**: write permissions given to a whole workflow, actions not pinned, event data injected into a shell
  step, jobs without a timeout ([CI-BASELINE](../CI-BASELINE.md#2-the-six-invariants-of-every-workflow)).
  **Misses**: what the workflow's scripts do once they run.
- **Moment**: before push (local check) and on the ready pull request.
- **Needs**: nothing; the tools run offline.

## 2. Three ways to provide a step

| | Embedded in the platform | Independent tool | Your own agent |
|---|---|---|---|
| Cost model | Licence per product or tier, plus usage: Actions minutes for code scanning, AI credits for GitHub's AI features; a GitLab tier plus a GitLab Duo add-on or credits (§2.1) | Open-source CLI: only your runner minutes. Hosted service: the vendor's subscription (not compared here) | Model tokens per run, plus a runner minute in CI |
| Where the code goes | Stays with the platform that already hosts it; the AI Scan pages read do not say where the models run | A CLI keeps it on your runner; a hosted service receives it | To the model provider you pay; its contract governs it ([layers of AI §4](../ai-layers/obo-agents.md#4-layer-4-paying-for-the-model-and-the-contract-that-comes-with-it)) |
| Who operates it | The platform: rules, models, updates | You (CLI version, rules, container) or the vendor (service) | You: brief, checklist, model choice, yearly review of the sources |
| How it is triggered | Platform events and settings, sometimes on every commit | Your workflow's triggers | Your workflow or the session, when you decide |

### 2.1 Embedded in the platform

**GitHub.** The paid security features come in two products, **GitHub Secret Protection** and **GitHub Code
Security**, bought on GitHub Team or GitHub Enterprise; some features are on by default for public repositories, and
the dependency graph and Dependabot alerts are in every plan
([About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security),
[GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features)).

| Feature | What the docs say it does | Plan, billing, status as documented |
|---|---|---|
| Code scanning with CodeQL | Finds vulnerabilities and errors with CodeQL or a third-party tool that outputs SARIF; runs on a schedule or on events such as a push ([About code scanning](https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning)) | Private repositories need GitHub Code Security; each run consumes Actions minutes |
| AI Scan for repositories | "scans a repository's default branch on demand across all languages", including those CodeQL covers; "Scans are manually triggered" ([AI Scan for repositories](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan-for-repositories)) | **Public preview**, "subject to change". Organization private or internal repositories: with Code Security or Advanced Security; personal private: not available; no Copilot licence needed; each scan consumes Code Security AI credits |
| AI Scan for pull requests | Vulnerabilities in pull request changes "for languages and frameworks not covered by CodeQL" (PHP, Shell/Bash, Terraform, Dockerfiles, JSP, Blazor); runs "when a pull request is created and after each new commit"; not on fork or Dependabot pull requests ([AI Scan for pull requests](https://docs.github.com/en/code-security/concepts/code-scanning/ai-powered-security-detections)) | Same availability table; usage in Code Security AI credits, Copilot-included credits first, then metered under budgets. The page carries no preview label. Findings "cannot yet be used in rulesets to enforce merge requirements" |
| Scan for AI applications | Risks in AI applications and agents in pull requests; "During public preview, AI applications scanning only detects indirect prompt injection (XPIA) vulnerabilities in AI agents"; no language limit; runs on creation and each new commit; findings are advisory pull request comments ([AI applications scanning](https://docs.github.com/en/code-security/concepts/code-scanning/ai-applications-scanning-for-pull-requests)) | **Public preview**. "requires a GitHub Advanced Security license and consumes AI credits on top of that license", public repositories included. Off by default |
| Copilot code review | Reviews pull requests and suggests fixes; by default only when assigned; can review every pull request, and each new push if "Review new pushes" is on ([Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review)) | Copilot plans (not Copilot Free); consumes AI credits, plus Actions minutes for agentic work. Does not count toward required approvals by default. Max effort level and passing suggestions to the cloud agent: public preview |
| Copilot Autofix | "a single suggested code change for one alert that you review and apply yourself" ([About autofix](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning)) | All public repositories, and private ones with Code Security; no AI credits; no Copilot subscription needed ([application card](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning)) |
| Agentic autofix | Copilot "investigate[s] and fix[es] one or more alerts for you, end to end" and opens a pull request; validates by re-running CodeQL ([About autofix](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning)) | Each session consumes AI credits and Actions minutes; enabled by an organization owner or security manager; not for Enterprise Managed Users repositories. GA status: to verify (the docs pages read state none) |
| Secret scanning, push protection | Scans the whole history, issues and pull request text for credentials; push protection blocks a push that contains one ([secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning), [push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection)) | Free on public repositories; private ones need Secret Protection. Repository push protection is off by default; anyone with write access can bypass it with a reason. AI-detected secrets: public preview |
| Dependabot, dependency review | Alerts on vulnerable dependencies; security and version update pull requests; dependency review fails a pull request check on a vulnerable package ([Dependabot alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts/about-dependabot-alerts), [dependency review](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/about-dependency-review)) | Dependabot in every plan; dependency review on all public repositories and on private ones with Code Security |
| Security campaigns | Group alerts and share them with developers; up to 25 code alerts per assignment to Copilot ([security campaigns](https://docs.github.com/en/code-security/concepts/security-at-scale/about-security-campaigns)) | Listed in both Secret Protection and Code Security; campaigns for secret alerts: public preview |

The three AI Scan features share one enterprise policy: allowing it "does not automatically enable any feature";
organizations enable each one, and repository administrators can opt out of each
([About AI Scan](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan)).

**GitLab.** GitLab pages carry a "Tier" line, quoted here.

| Feature | Tier and add-on as documented |
|---|---|
| SAST | Free, Premium, Ultimate for basic scanning with open-source analysers; Ultimate only for GitLab Advanced SAST (cross-file, cross-function), vulnerability management, new findings in merge request reports and "Agentic SAST Vulnerability Resolution"; "GitLab Duo false positive detection" needs Ultimate and a GitLab Duo add-on ([SAST](https://docs.gitlab.com/user/application_security/sast/)) |
| Dependency scanning | Ultimate ([dependency scanning](https://docs.gitlab.com/user/application_security/dependency_scanning/)) |
| Secret detection | Free, Premium, Ultimate; methods: secret push protection, pipeline secret detection, client-side secret detection ([secret detection](https://docs.gitlab.com/user/application_security/secret_detection/)) |
| Code review by GitLab Duo | Two features: "Code Review Flow" (no add-on, "Uses GitLab Credits") and "GitLab Duo Code Review" (GitLab Duo Enterprise). Reviews on request, when a non-draft merge request opens, when a draft is marked ready; on each push only for Code Review Flow with "Start a new review on push" ([GitLab Duo in merge requests](https://docs.gitlab.com/user/project/merge_requests/duo_in_merge_requests/)) |
| Vulnerability Explanation | Ultimate, add-on GitLab Duo Enterprise or GitLab Duo with Amazon Q, generally available since 17.2 ([Explain vulnerabilities with AI](https://docs.gitlab.com/user/application_security/analyze/duo/)). The [feature summary](https://docs.gitlab.com/user/gitlab_duo/feature_summary/) says Premium and Ultimate with Duo Pro or Enterprise: the two pages disagree, to verify |
| Vulnerability Resolution | Ultimate for the agentic SAST resolution (SAST page above); the feature's own page was not opened: add-on to verify |

### 2.2 Independent tools

| Tool | What its own documentation says, in one line |
|---|---|
| CodeRabbit | Reviews pull requests on GitHub, GitLab, Azure DevOps and Bitbucket; a full review when the pull request is created, then "incremental reviews" on each later commit; runs "third-party linters and security scanners during the review"; also an IDE extension and command-line pre-commit reviews ([docs](https://docs.coderabbit.ai/), [review overview](https://docs.coderabbit.ai/guides/code-review-overview)) |
| SonarQube | "verifies code, whether a developer or an AI agent wrote it, before it ships"; Cloud, Server and a free Community Build; AI features on the product page: AI CodeFix, Sonar MCP, Sonar Vortex, Remediation Agent, Hunter Agent, Gitar (PR review) ([product page](https://www.sonarsource.com/products/sonarqube/)); plan and preview status of each AI feature: to verify. Its quality gate can block a pull request merge or fail a pipeline; the default "Sonar way" includes coverage of new code ≥ 80 % and duplication ≤ 3 % ([quality gates](https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates)) |
| Semgrep | SAST, SCA and secrets "from one platform" ([docs](https://docs.semgrep.dev/)); the Community Edition engine is LGPL-2.1 and "can only analyze code within the boundaries of a single function or file"; cross-file analysis is in the platform, which has free and paid tiers ([repository](https://github.com/semgrep/semgrep)) |
| Trivy | Finds known vulnerabilities, IaC misconfigurations, secrets and licences in images, filesystems, repositories and Kubernetes; Apache-2.0 ([repository](https://github.com/aquasecurity/trivy)) |
| gitleaks | Detects secrets "in git repos", "past or present"; pre-commit hook or GitHub Action; MIT ([repository](https://github.com/gitleaks/gitleaks)) |
| zizmor | "a static analysis tool for your CI/CD" that finds and fixes security issues in GitHub Actions, Dependabot and pre-commit setups ([docs](https://docs.zizmor.sh/)) |

### 2.3 Your own agent

An agent with a narrow brief and read-only tools, started for one question. The harness ships three kinds:

- **Intent review**: `adversarial-reviewer` answers only "does the change do what the issue asks?", refuses to give a
  verdict if it is not isolated from the author's context, and has no write tool
  ([adversarial-reviewer.md](../../plugins/harness/agents/adversarial-reviewer.md)).
- **Compliance review**: one agent per framework (`compliance-pci`, `compliance-tisax`, `compliance-iso27001`…), each
  with its triggers, a checklist of requirement → source, expected evidence and a fixed verdict format; plus the
  generic `compliance-reviewer`, which applies a spec the project writes and nothing else
  ([COMPLIANCE §1–2](../COMPLIANCE.md#1-catalogue), [compliance-reviewer.md](../../plugins/harness/agents/compliance-reviewer.md)).
- **Code review in CI**: the optional review service `ai-review.yml`, which can only post a comment, never approve
  ([REVIEW-SERVICE](../REVIEW-SERVICE.md#1-service-contract)).

**When it makes sense**: a framework no product covers (TISAX, a national health-data rule), a house rule, a question
that needs the issue as input (intent). **What it costs**: the tokens of a strong model per review, and upkeep:
frameworks change, so each agent's sources are reviewed every year ([COMPLIANCE §1](../COMPLIANCE.md#1-catalogue)).
The scope is decided from `paths` and `keywords` **without starting an agent**, so an out-of-scope diff costs no token
([COMPLIANCE §2](../COMPLIANCE.md#2-plugging-in-a-framework-three-modes)). **Its limits**: it is a reviewer, not a
certification, an audit or legal advice; each finding is a hypothesis for the named owner (QSA, CISO, DPO). It is not
deterministic, so it never replaces the scanners for secrets or dependencies. Identifiers it could not check against
the official text are marked "(to verify)", as in
[compliance-pci.md](../../plugins/harness/agents/compliance-pci.md) and
[compliance-tisax.md](../../plugins/harness/agents/compliance-tisax.md).

## 3. Steps × the three ways

★ marks what the harness uses or ships ([CI-BUDGET §3](../CI-BUDGET.md#3-security-baseline): first value for a public
repository, second for a private one without GitHub's paid products). "—" means none found in the pages read, or
not a good fit.

| Step | Embedded in the platform | Independent tool | Your own agent |
|---|---|---|---|
| Intent review | — | — | ★ `adversarial-reviewer` |
| Code review of the diff | Copilot code review; GitLab Duo Code Review, Code Review Flow | CodeRabbit (★ supported); SonarQube's Gitar | ★ `ai-review.yml` (optional) |
| SAST, rule-based | ★ CodeQL (public); GitLab SAST, Advanced SAST | ★ Semgrep CE (private); SonarQube | — |
| SAST, AI-based | AI Scan for repositories, for pull requests (GitHub); Duo false positive detection (GitLab) | Semgrep and SonarQube platform AI features | Possible; the adversarial checklist covers injection |
| SCA | ★ Dependabot + dependency review (public); GitLab dependency scanning | ★ Trivy `fs` (private); Semgrep Supply Chain | — (a database lookup, not a judgement) |
| Secret scanning | ★ secret scanning + push protection (public); GitLab secret detection | ★ gitleaks (both) | — (must be deterministic) |
| AI applications and agents | Scan for AI applications (GitHub, preview) | — | A narrow reviewer with an injection checklist (not shipped) |
| Quality gate | GitHub Code Quality merge gating (named on the Copilot code review page, not researched) | SonarQube quality gate | — (the harness uses its tier 1 local command: strict lint and tests) |
| Compliance review | — | — | ★ `compliance-*`, `compliance-reviewer` |
| Workflow and config linting | — | ★ zizmor, actionlint | — |

## 4. When each step runs in the harness

From [CI-BASELINE §1](../CI-BASELINE.md#1-the-tiers) (tiers 0, 1 and 3), [CI-BUDGET §2–3](../CI-BUDGET.md#2-rules-),
[REVIEW-ROUNDS](../REVIEW-ROUNDS.md#the-two-reviews) and [COMPLIANCE §3](../COMPLIANCE.md#3-place-in-the-loop).

| Step | Before push | Draft | Ready PR | Integration branch | Weekly |
|---|---|---|---|---|---|
| Intent review | | in the session, before "Ready" | again if the head moves after approval | | |
| Code review | | | once per head | | |
| SAST | | | `security.yml` (Semgrep) or CodeQL | CodeQL may run only here | `security.yml` |
| SCA | | | `security.yml` (Trivy) or dependency review | | `security.yml`; Dependabot `github-actions` grouped |
| Secrets | pre-commit `detect-private-key` | | gitleaks | | `security.yml` |
| AI applications | | | (not covered) | | |
| Quality gate | local command | | tier 1 CI replays it | | |
| Compliance | | in the session, before "Ready", if in scope | | | |
| Workflow lint | local command | | zizmor, actionlint (`docs-security.yml`) | | |

On a draft nothing costly runs: the draft is a backup and a window, not a test bench
([CI-BUDGET §2](../CI-BUDGET.md#2-rules-)).

## 5. Overlaps and loops

**Doing one job twice.**

- *An AI scan and a review bot on every commit.* GitHub's AI Scan for pull requests and its AI applications scan run
  "after each new commit"; Copilot code review can review each push; CodeRabbit reviews each later commit
  incrementally (sources in §2). With all three on, one push buys three AI passes. The GitHub pages read exclude fork
  and Dependabot pull requests but do not say whether drafts are skipped: to verify before enabling them where agents
  push to drafts. They also warn that qualifying pull requests "can consume Code Security AI Credits" before a
  repository administrator opts out.
- *Two review services.* The harness keeps CodeRabbit and its own service side by side for about ten pull requests,
  then keeps one ([REVIEW-SERVICE §4](../REVIEW-SERVICE.md#4-setting-it-up-in-a-project)).
- *The same secret scan twice per push.* Seen on two projects (a hook replayed by a job, `push` plus `pull_request`);
  the rule is one check, one place ([CI-BASELINE §4](../CI-BASELINE.md#4-what-the-survey-showed)). The two harness
  security workflows are called with gitleaks off in one of them ([CI-BUDGET §3](../CI-BUDGET.md#3-security-baseline)).
  Push protection and gitleaks are not a double: push protection blocks at the push on GitHub, gitleaks runs in the
  harness's own checks and on private repositories without Secret Protection.
- *CodeQL and AI Scan.* Complementary by design rather than a double: AI Scan for pull requests targets what CodeQL
  does not cover, while AI Scan for repositories runs on demand and may add findings in CodeQL's languages.

**Loops to avoid.**

- *A bot reviewing every push.* At agent pace a pull request can get many pushes; each one starts a review, a new set
  of comments and a new round. The harness reviews **once per ready head** and pushes **one commit per round**
  ([REVIEW-ROUNDS](../REVIEW-ROUNDS.md#convergence-a-settled-finding-stays-settled), step 6).
- *An agent answering a bot that answers back.* An author agent that replies to every comment, and a bot that reviews
  every reply, can run without end. The harness stops it: a round with no finding ends the loop, at most 3 review
  rounds and 6 CI-tested pushes per pull request, and a settled finding is not reopened without new evidence
  ([FINOPS §3](../FINOPS.md#3-quotas-parallelism-and-resuming),
  [REVIEW-ROUNDS](../REVIEW-ROUNDS.md#convergence-a-settled-finding-stays-settled)).
- *Bots that open pull requests for bots.* Agentic autofix opens a pull request per assignment, and Copilot code
  review can pass suggestions to the cloud agent (preview); each new pull request then goes through every review and
  scan again. Batch them (a campaign assigns up to 25 alerts in one pull request) and keep them under the same
  per-head rule.

What the harness does about agent pace, in short: push often to a **draft** (nothing costly), move to "Ready" once,
review and scan **once per ready head**, cancel a run when a new push arrives (`concurrency`), and run the dependency
scan weekly so that it does not need a commit ([CI-BUDGET §2](../CI-BUDGET.md#2-rules-)). Other choices are
reasonable: a team with few pushes per pull request can let a platform scan every commit, and a public repository
gets CodeQL and secret scanning at no licence cost.

## Sources

Vendor pages, read on the date given. Full quotes: [research notes](sources/review-and-scanning-notes.md).

- GitHub, read 2026-11-11:
  [About AI Scan](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan),
  [AI Scan for repositories](https://docs.github.com/en/code-security/concepts/code-scanning/ai-scan-for-repositories),
  [AI Scan for pull requests](https://docs.github.com/en/code-security/concepts/code-scanning/ai-powered-security-detections),
  [AI applications scanning for pull requests](https://docs.github.com/en/code-security/concepts/code-scanning/ai-applications-scanning-for-pull-requests),
  [About code scanning](https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning),
  [About GitHub Advanced Security](https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security),
  [Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review),
  [About autofix for code scanning](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning),
  [Application card: security and quality AI features](https://docs.github.com/en/code-security/code-scanning/managing-code-scanning-alerts/responsible-use-autofix-code-scanning),
  [About secret scanning](https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning),
  [About push protection](https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection),
  [About Dependabot alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts/about-dependabot-alerts),
  [About dependency review](https://docs.github.com/en/code-security/supply-chain-security/understanding-your-software-supply-chain/about-dependency-review).
- GitHub, read 2026-11-12:
  [GitHub security features](https://docs.github.com/en/code-security/getting-started/github-security-features),
  [About security campaigns](https://docs.github.com/en/code-security/concepts/security-at-scale/about-security-campaigns).
- GitLab, read 2026-11-12:
  [SAST](https://docs.gitlab.com/user/application_security/sast/),
  [dependency scanning](https://docs.gitlab.com/user/application_security/dependency_scanning/),
  [secret detection](https://docs.gitlab.com/user/application_security/secret_detection/),
  [GitLab Duo in merge requests](https://docs.gitlab.com/user/project/merge_requests/duo_in_merge_requests/),
  [Explain vulnerabilities with AI](https://docs.gitlab.com/user/application_security/analyze/duo/),
  [GitLab Duo feature summary](https://docs.gitlab.com/user/gitlab_duo/feature_summary/).
- Independent tools, read 2026-11-12:
  [CodeRabbit docs](https://docs.coderabbit.ai/),
  [CodeRabbit review overview](https://docs.coderabbit.ai/guides/code-review-overview),
  [SonarQube](https://www.sonarsource.com/products/sonarqube/),
  [SonarQube Cloud quality gates](https://docs.sonarsource.com/sonarqube-cloud/standards/managing-quality-gates/introduction-to-quality-gates),
  [Semgrep docs](https://docs.semgrep.dev/), [semgrep/semgrep](https://github.com/semgrep/semgrep),
  [aquasecurity/trivy](https://github.com/aquasecurity/trivy), [gitleaks/gitleaks](https://github.com/gitleaks/gitleaks),
  [zizmor docs](https://docs.zizmor.sh/).
- Not opened, so not used for a fact: GitLab's own Vulnerability Resolution page (its add-on stays "to verify");
  actionlint's own page (named here only as the harness's choice).
