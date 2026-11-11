# The layers of AI: a guide in parts

**TL;DR**: "we use Claude", "we approved Codex", "we have Gemini" mean little on their own. An AI product is a stack
of four layers: where you talk to it, what decides and acts, where it acts, and which model answers, sold and operated
by whom. Each layer is a separate choice, with its own risks and its own contract. This guide takes the layers apart,
one audience at a time.

![The four layers of an AI product as rows (presentation, agent, execution, inference), one question each, for three products as columns: a chatbot, an agent on your behalf in a vendor's cloud, an agent on your behalf on your machine. Presentation differs per product. The chatbot has no action loop; both agents run the same loop. Execution is the split: the chatbot runs in its vendor's cloud with none of your files, only what you paste; the cloud agent works in a vendor's container on a copy of the repository, with its own build and test tools and only what it was given; the local agent works on your machine with your files and repositories, build and test tools, your network and every credential already there. Inference is the same in all three: the model usually runs on a provider's servers, and who sells and operates it sets the contract on your data. On your machine the agent acts as you, and permissions are the only guardrail](../diagrams/ai-stack.svg)

| Part | For whom | Status |
|---|---|---|
| General public: chatbot, assistant, agent | anyone who uses a chat app | planned |
| Agents at home: personal assistants that act for you | individuals | planned |
| [Apps and CLIs: the agent that works on your behalf](obo-agents.md) | developers, tech leads, security, and the managers who approve these tools | 🟢 available |
| Managers and executives: what your teams are talking about | managers, executives, buyers | planned |
| Autonomous agents: no human at the keyboard | platform and security teams | planned |

Words used in every part:

- **OBO** (*on behalf of*): an agent that works for a person, with that person's files, accounts and rights, while
  the person stays in charge (asks, watches, approves).
- **Inference**: the computation of the model's answer, on the provider's servers; it is what you pay per token or
  per seat.
- **Harness**: the program around the model that turns its answers into actions (read a file, run a command) and
  enforces permissions. Belayline is a method and a set of rules on top of such harnesses.
