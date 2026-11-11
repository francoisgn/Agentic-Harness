# The layers of AI: a guide in parts

**TL;DR**: "we use Claude", "we approved Codex", "we have Gemini" mean little on their own. An AI product is a stack
of four layers: where you talk to it, what decides and acts, where it acts, and which model answers, sold and operated
by whom. Each layer is a separate choice, with its own risks and its own contract. This guide takes the layers apart,
one audience at a time.

![The four layers of an AI product, one question each, with a typical answer: presentation (where do I talk to it), agent (what decides and acts), execution (where does it act), inference (which model answers); an agent on your behalf (OBO) is layers 2 and 3 and acts with your rights, on your machine or in a cloud; who sells and operates the inference sets the contract on your data; a chatbot is layers 1 and 4: it answers, with no action loop and at most a sandbox of its own](../diagrams/ai-stack.svg)

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
