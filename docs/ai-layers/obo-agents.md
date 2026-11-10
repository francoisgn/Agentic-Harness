# Apps and CLIs: the AI agent that works on your behalf

Part of [The layers of AI](README.md). For developers, tech leads, security teams, and the managers who approve these
tools.

> **Last checked: 2026-11-10.** Products, plans and terms change every few months. Every product fact below cites
> the vendor page it comes from, with the date it was read. Re-check them before you decide anything.

**TL;DR**

- A **chatbot** answers. An **agent** acts: it reads and changes files and runs commands, with the rights of the
  person it works for. That is an agent *on behalf of* someone: **OBO**.
- Four layers, one question each:
  1. Where do I talk to it?
  2. What decides and acts?
  3. Where does it act?
  4. Where does the model run, and who bills it?
- "Claude Code", "Codex", "Antigravity" and "Copilot" are mostly **layer 2**, the agent. You reach each one through
  several screens (layer 1). It acts on your laptop or in a vendor's cloud (layer 3). It can be paid through several
  contracts (layer 4).
- **Your data is governed by the contract with whoever sells and operates the inference, and by the type of plan.**
  The same model, bought three ways, comes with three different contracts.
- So **"we approved tool X" says almost nothing** until each layer is decided ([§7](#7-we-approved-x-why-the-sentence-says-nothing)).

## 1. Chatbot or agent

| | Chatbot | Agent working on your behalf (OBO) |
|---|---|---|
| What it does | Answers in text; may run code in a sandbox of its own | Runs a loop: the model asks for an action, a tool performs it, the result goes back to the model, again and again |
| What it can reach | What you paste into the conversation | Your files and repository, a shell, the network, and the accounts its environment is logged into |
| Its limits | The conversation | **Permissions**: which tools it may use, which actions need your approval, which folders and hosts it can reach |
| Who answers for the result | You, when you copy the answer | You, for every change it made in your name: review it like a colleague's work |

The difference is not the model; the same model can sit behind both. What makes an agent is the program around the
model, often called the **harness**. The harness turns the model's requests into actions and enforces the
permissions.

## 2. The four layers

![The four layers of an AI coding agent: presentation (where do I talk to it), agent (who decides and acts), execution (where do tools act), inference (where does the model run); an OBO agent is layers 2 and 3 acting in your files with your rights, a chatbot only has layers 1 and 4](../diagrams/ai-layers.svg)

| Layer | Question | Typical answers | What changes for you |
|---|---|---|---|
| 1. Presentation | Where do I talk to it? | Terminal (CLI), IDE extension, desktop app, web app, mobile app, a mention in GitHub, Slack or Linear | Comfort and reach: a phone can start work that runs elsewhere |
| 2. Agent | What decides and acts? | Claude Code, Codex, Antigravity CLI, Gemini CLI, Copilot agent, Cursor agent | Which tools exist, how permissions work, which models it can use |
| 3. Execution | Where do the tools act? | Your machine, or a vendor's cloud container or VM; sometimes split between the two | What the agent can touch: your laptop and everything logged in on it, or only what a cloud box was given |
| 4. Inference | Where does the model run, and who bills it? | Vendor subscription, vendor API key, or a cloud platform (Amazon Bedrock, Google's Gemini Enterprise Agent Platform, Microsoft Foundry) | The contract that governs your data, the price model, the models on offer, the region |

A product name rarely names a single layer. "Claude Code" is an agent (layer 2) with several screens (layer 1). It
runs on your machine or in Anthropic's cloud (layer 3), and its inference can be paid in four ways (layer 4)
([Claude Code overview](https://code.claude.com/docs/en/overview), [third-party integrations](https://code.claude.com/docs/en/third-party-integrations)).

## 3. Layer 3: where the agent acts

| Where | What it can reach | Examples (sourced in §5) |
|---|---|---|
| **Your machine** | Your files, your network, and every credential already on the machine (SSH keys, cloud CLI logins, browser sessions). The permission settings are the only guardrail | Claude Code in a terminal or IDE; Codex CLI; Gemini CLI; Gemini Code Assist agent mode; Copilot agent mode in VS Code; Copilot CLI |
| **A vendor's cloud** | A container or VM with a copy of the repository, plus only what it was given: a repository token, allowed hosts, secrets. It keeps working while you are away | Claude Code on the web; Copilot cloud agent; Cursor cloud agents |
| **Split** | The loop runs in the vendor's cloud, while the tools run on a machine you provide, or the other way round | Cursor self-hosted machines (tools on your hardware, loop in Cursor's cloud); Claude Code Remote Control (runs on your machine, steered from a phone or browser) |

Inference is almost never local. Even when the agent runs on your laptop, every prompt, and the file extracts it
reads, is sent to the model provider. "It runs locally" describes layer 3, never layer 4.

## 4. Layer 4: paying for the model, and the contract that comes with it

### Three ways to pay

![Same model, three ways to buy it, three contracts: a coding agent calls a model through the model vendor (subscription or API key, vendor terms), a cloud platform (Bedrock, Agent Platform, Foundry: cloud terms plus model terms) or a tool vendor plan (Copilot, Cursor: the tool vendor's terms)](../diagrams/ai-contracts.svg)

| Way | Who bills | Price model | Contract that governs your data |
|---|---|---|---|
| **Vendor subscription** | The vendor (Anthropic, OpenAI, Google, GitHub, Cursor) | Per seat, with usage limits | **Consumer** terms for individual plans (Free, Pro, Max, Plus…); **commercial** terms for business plans (Team, Business, Enterprise) |
| **Vendor API key** | The vendor | Per token | The vendor's commercial or API terms |
| **Cloud platform** | Your cloud provider (AWS, Google Cloud, Microsoft) | Per token, on your cloud bill | The cloud's terms, plus the model provider's terms. **How they combine depends on the platform** (below) |

### Same vendor, different plan: different terms

| Vendor | Individual plans | Business plans and API | Source |
|---|---|---|---|
| Anthropic | Consumer Terms (Free, Pro, Max, Ultra, and Claude Code used on those accounts). Data is used for training only if you allow it. Retention is 5 years if you allow it, 30 days if not | Commercial Terms (Team, Enterprise, API). No training by default. Retention is 30 days. Zero data retention is available on approval | [Claude Code data usage](https://code.claude.com/docs/en/data-usage), [Privacy Center](https://privacy.claude.com/en/articles/10023580-is-my-data-used-for-model-training) |
| GitHub Copilot | Free, Pro, Pro+: from 2026-04-24, interaction data may be used for training unless you opt out | Business, Enterprise: not used for training (Data Protection Agreement) | [GitHub changelog 2026-03-25](https://github.blog/changelog/2026-03-25-updates-to-our-privacy-statement-and-terms-of-service-how-we-use-your-data/) |
| Google | Code Assist for individuals, Google AI Pro, Google AI Ultra: these stopped serving IDE and Gemini CLI requests on 2026-06-18 (users are sent to Antigravity) | Gemini Code Assist Standard and Enterprise: prompts and responses are not used for training | [Privacy notice, individuals](https://developers.google.com/gemini-code-assist/resources/privacy-notice-gemini-code-assist-individuals), [Gemini for Google Cloud data governance](https://docs.cloud.google.com/gemini/docs/discover/data-governance) |
| OpenAI | ChatGPT Free, Go, Plus, Pro: training default *not verified* (the help pages could not be read) | Business, Edu, Enterprise: no training on business data by default. API: not used for training unless you opt in. Codex follows the workspace settings with ChatGPT sign-in, the API organisation's with a key | [Codex pricing](https://learn.chatgpt.com/docs/pricing), [Codex sign-in](https://learn.chatgpt.com/docs/auth), [OpenAI API: your data](https://developers.openai.com/api/docs/guides/your-data) |

### One model, three platforms, three arrangements

The cloud platforms do not treat a partner model the same way. Taking Claude as the example:

| Platform | Arrangement | Source |
|---|---|---|
| Amazon Bedrock | Model providers have no access to customer prompts and completions. Content is not shared with them and is not used to improve the base models | [Bedrock data protection](https://docs.aws.amazon.com/bedrock/latest/userguide/data-protection.html), [Bedrock FAQ](https://aws.amazon.com/bedrock/faqs/) |
| Google Cloud, Google-managed Claude (Model Garden) | "Not a Google product". It falls under the "Separate Offerings" terms of Google's Service Specific Terms, plus the model card's own terms. Google's general "no training on customer data" statement does not name Claude | [Claude on Google Cloud](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/partner-models/claude), [data governance](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/data-governance) |
| Google Cloud, Anthropic-managed Claude | Needs an account with Anthropic. Anthropic's Commercial Terms apply in a **separate** Anthropic organisation: the settings of an existing Anthropic contract (zero retention, HIPAA) do not carry over | [Anthropic-managed Claude](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/partner-models/claude/anthropic-managed) |
| Microsoft Foundry | Anthropic sells and operates the model, as an independent data processor under its own DPA and Commercial Terms. Hosting is either on Azure (data stays on Azure) or on Anthropic's infrastructure (data may leave Azure) | [Claude in Foundry: data privacy](https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/claude-models/data-privacy) |

Google renamed Vertex AI to **Gemini Enterprise Agent Platform**
([Google Cloud docs](https://docs.cloud.google.com/vertex-ai/docs/start/introduction-unified-platform)). Anthropic's
docs call it "Google Cloud's Agent Platform" ([Claude Code on Google Cloud](https://code.claude.com/docs/en/google-vertex-ai)).
Older material, and some settings such as `CLAUDE_CODE_USE_VERTEX`, still say Vertex.

**Worked example.** "Our Google Cloud agreement says our data is not used for training, so it covers Claude through
Vertex AI." That is only partly true:

- The general statement covers the models Google manages. Its page does not name Claude, and Claude comes with
  separate terms.
- Read the "Separate Offerings" terms and the model card. If you use Anthropic-managed Claude, read Anthropic's
  Commercial Terms.
- A Claude **Pro or Max** subscription, by contrast, falls under Anthropic's Consumer Terms. No cloud agreement
  covers it.
- A company that wants an Anthropic contract signs up for Team or Enterprise, or uses the API with a commercial key.

## 5. The main tools, layer by layer

| Tool | Layer 1: screens | Layer 3: where tools act | Layer 4: how inference is bought | Models |
|---|---|---|---|---|
| **Claude Code** (Anthropic) | Terminal, VS Code and JetBrains, desktop app, web, mobile | Your machine (terminal, IDE, desktop); Anthropic's cloud for web sessions. Remote Control runs on your machine and is steered from elsewhere | Claude subscription (Pro, Max, Team, Enterprise), Console API key, Amazon Bedrock, Google Cloud Agent Platform, Microsoft Foundry, an LLM gateway. Web sessions need a Claude subscription | Claude only |
| **Codex** (OpenAI) | CLI, IDE extension, ChatGPT desktop app, web, iOS | Your machine (CLI, IDE, desktop); Codex Cloud: a cloud workspace per task, which keeps working while your computer sleeps | Sign in with ChatGPT (plans from Free to Enterprise), or an API key (no cloud features). Codex Cloud requires ChatGPT sign-in | OpenAI |
| **Gemini CLI** (Google) | Terminal; behind Gemini Code Assist agent mode in VS Code | Your machine | Gemini Code Assist Standard or Enterprise, Gemini API key, Google Cloud Agent Platform. Individual plans were moved to Antigravity CLI on 2026-06-18 | Gemini |
| **Antigravity** (Google: app, CLI, IDE, SDK) | Desktop app, terminal, IDE, remote control | Local agents (app); the CLI runs in local shells, remote cloud environments and SSH sessions | Free individual tier, Google AI Pro and Ultra, a Google Cloud business plan, API pay-as-you-go | Gemini, plus Claude and an open GPT model in the model picker (separate usage limits) |
| **Gemini Code Assist** (Google) | VS Code, IntelliJ | Your machine: agent mode uses the IDE's tools (files, terminal) and asks before changes unless always-allow is set | Standard or Enterprise edition | Gemini |
| **GitHub Copilot** | VS Code and other IDEs, Copilot CLI, github.com, the Copilot app | Your machine (agent mode, CLI). Cloud agent: a GitHub cloud sandbox, a GitHub Actions runner, or a remote environment you connect | Copilot plan; bring your own key in some surfaces. Claude and Codex agents on github.com run on the Copilot plan (public preview) | Several vendors |
| **Cursor** | Desktop editor, web, iOS, Slack, GitHub, Linear, API | Your machine (editor agent). Cloud agents: an isolated cloud VM. Self-hosted machines: tools on your hardware, loop in Cursor's cloud | Cursor plans. On Premium and above, cloud agents and third-party models are billed at API list price | Several vendors, plus Cursor's own |

Sources, read 2026-11-10:

- **Claude Code:** [overview](https://code.claude.com/docs/en/overview), [third-party integrations](https://code.claude.com/docs/en/third-party-integrations).
- **Codex:** [Codex Cloud](https://learn.chatgpt.com/docs/cloud), [pricing](https://learn.chatgpt.com/docs/pricing), [sign-in](https://learn.chatgpt.com/docs/auth).
- **Gemini CLI and Antigravity:**
  - [Gemini CLI README](https://github.com/google-gemini/gemini-cli)
  - [Gemini CLI → Antigravity CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)
  - [Gemini Code Assist agent mode](https://docs.cloud.google.com/gemini/docs/codeassist/agent-mode)
  - [Antigravity](https://antigravity.google/), [plans](https://antigravity.google/pricing), [models](https://antigravity.google/docs/models)
- **GitHub Copilot:**
  - [Copilot cloud agent](https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent)
  - [third-party agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-agents)
  - [Copilot CLI](https://docs.github.com/en/copilot/concepts/agents/about-copilot-cli)
- **Cursor:**
  - [Cursor cloud agents](https://cursor.com/docs/cloud-agent)
  - [runtimes](https://cursor.com/docs/cloud-agent/choose-runtime)
  - [models and pricing](https://cursor.com/docs/models-and-pricing)

## 6. What does not combine

- **A subscription belongs to its vendor's tools.** Anthropic's subscription sign-in is "intended exclusively" for
  Claude Code and Anthropic's own apps. A third-party tool must use an API key or a cloud platform
  ([Claude Code legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)).
- **An agent is tied to its model family.**
  - Claude Code calls Claude models: from Anthropic, Bedrock, Google Cloud or Foundry, or through a gateway that
    speaks Anthropic's API. Pointing it at Vertex does not give it Gemini
    ([third-party integrations](https://code.claude.com/docs/en/third-party-integrations)).
  - In the other direction, Gemini CLI cannot drive Claude on Google Cloud. The request was closed as "not planned"
    on 2026-08-05 ([gemini-cli #25579](https://github.com/google-gemini/gemini-cli/issues/25579)).
  - Google's newer agent, Antigravity, does offer Claude models in its own model picker, under Google's plan and
    limits ([Antigravity models](https://antigravity.google/docs/models)). Whether a tool can use a model is a
    property of the tool, not of the model's family.
- **Multi-vendor tools resell the models under their own contract.** Claude and Codex agents in GitHub Copilot run
  on the Copilot plan, not on your Anthropic or OpenAI account
  ([third-party agents](https://docs.github.com/en/copilot/concepts/agents/about-third-party-agents)). Cursor bills
  third-party models itself ([models and pricing](https://cursor.com/docs/models-and-pricing)).
- **Same model, different contract.** Claude through a Max subscription, through Copilot Business and through
  Bedrock is the same family of models. The three contracts behind them differ: Anthropic consumer, GitHub business,
  AWS.

## 7. "We approved X": why the sentence says nothing

"We approved Claude Code", or Codex, or Copilot, sounds like a decision. In fact it leaves every layer open. It does
not say:

- whether the terminal is allowed, or only the IDE extension;
- whether the agent may work in the vendor's cloud with a copy of your code;
- which contract pays for the model;
- which models are allowed;
- what the agent is allowed to run.

Two teams can both "use the approved tool" while one runs it on personal Pro accounts, under consumer terms that may
allow training, and the other runs it through the company's cloud contract.

An approval that means something answers one question per layer, plus two about people:

| Layer | Question to settle | Examples of answers |
|---|---|---|
| 1. Presentation | Which surfaces? | CLI and IDE extension: yes; web and mobile: no; GitHub mentions: only on these repositories |
| 2. Agent | What may it do on its own? | Edits: yes; shell commands: on approval; network: these hosts; connectors (MCP): this list |
| 3. Execution | Where may it run? | Company laptops only; vendor cloud allowed for these repositories, with these secrets and this network allowlist |
| 4. Inference | Through which contract, which models, which region? | Company Enterprise plan or cloud platform, never a personal subscription; models on this list; this region; zero retention if available |
| Identity | Whose account? | Company account with SSO, never a personal login |
| Accountability | Who answers for a change? | The person on whose behalf the agent worked; the usual review before merge |

Rewritten, the sentence becomes:

> Approved: the coding agent's CLI and IDE extension, on company laptops, signed in with SSO to our Enterprise plan
> (commercial terms, no training). Models from the plan's list only. No vendor-cloud sessions. Shell commands need
> approval.

## 8. Common misreadings

| What is often said | What is true |
|---|---|
| "Claude Code is a model" | It is an agent (a harness). The model behind it is Claude |
| "It runs locally, so our code stays here" | The tools run locally. The prompts and the file extracts the agent reads go to the model provider |
| "Through Vertex, Claude Code can use Gemini" | No. Claude Code calls Claude models, wherever they are hosted |
| "A Google tool cannot use Claude" | It depends on the tool. Gemini CLI cannot; Antigravity offers Claude in its model picker, under Google's plan |
| "Our Google contract covers Claude on Vertex" | Partly at most. Google-managed Claude has its own terms, and Anthropic-managed Claude is under Anthropic's |
| "My Claude Max subscription can power any tool" | No. A subscription is for the vendor's own apps; other tools need an API key or a cloud platform |
| "Copilot with Claude falls under our Anthropic contract" | No. It runs on the Copilot plan, under GitHub's terms |
| "Same model, same privacy" | No. The contract follows whoever sells and operates the inference, and the type of plan |
