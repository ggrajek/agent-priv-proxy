\# Agent Privilege \& Guardrail Proxy (`agent-priv-proxy`)



A zero-trust execution proxy and privilege boundary for autonomous AI agents and Non-Human Identities (NHIs).



\---



\## 1. Executive Summary \& Problem Statement



Autonomous agents frequently operate with overprivileged, static service principal credentials (e.g., broad Microsoft Entra ID or cloud IAM roles like `Directory.ReadWrite.All`). When AI agents execute tool calls autonomously without guardrails:



\* Standing broad privileges create immediate lateral movement paths if prompts are injected or context drifts.

\* Actions lack session-bound attribution, appearing in audit logs simply as the agent's service principal rather than the initiating human user.

\* Destructive actions execute without Human-in-the-Loop (HITL) authorization gates.



`agent-priv-proxy` serves as an inline, reverse-proxy enforcement layer between the AI agent orchestration framework (LangChain, AutoGen, CrewAI, Semantic Kernel) and upstream APIs.



\---



\## 2. Architectural Position in the GRC AI Trilogy



```mermaid

flowchart LR

&#x20;   A\["1. Posture Assessment<br><b>ai-grc-auditor</b><br>• Scans directory inventory<br>• Vector-audits controls<br>• Flags persistent secrets"] --> B\["2. Continuous Governance<br><b>agentic-iar</b><br>• Automated access reviews<br>• Flags privilege bloat<br>• Revokes stagnant access"]

&#x20;   B --> C\["3. Runtime Enforcement<br><b>agent-priv-proxy</b><br>• Inline tool-call proxy<br>• Enforces JIT elevation \& HITL<br>• Ephemeral token delegation"]

```



\---



\## 3. Runtime Architecture \& Execution Flow



```mermaid

sequenceDiagram

&#x20;   autonumber

&#x20;   actor User as User Session

&#x20;   participant Agent as Autonomous Agent

&#x20;   participant Proxy as agent-priv-proxy

&#x20;   participant Policy as policy.json

&#x20;   actor Human as Human Reviewer (HITL)

&#x20;   participant Upstream as Upstream API (Entra / DB)



&#x20;   User->>Agent: Prompt / Task Request

&#x20;   Agent->>Proxy: POST /tool/execute (Tool, Params, SessionID)

&#x20;   Proxy->>Policy: Evaluate Tool \& Risk Tier



&#x20;   alt Low Risk (e.g., READ)

&#x20;       Policy-->>Proxy: Approved (No HITL Required)

&#x20;       Proxy->>Proxy: Mint Ephemeral Token (TTL: 300s)

&#x20;       Proxy->>Upstream: Execute Tool Call with Session Attribution

&#x20;       Upstream-->>Proxy: Data Response

&#x20;       Proxy-->>Agent: Result Payload

&#x20;   else High / Critical Risk (e.g., WRITE / DELETE)

&#x20;       Policy-->>Proxy: Intercept (Requires HITL)

&#x20;       Proxy-->>Agent: 202 Intercepted (Pending Approval)

&#x20;       Proxy->>Human: Notification / Pending Queue

&#x20;       Human->>Proxy: POST /approval/decision (Approved)

&#x20;       Proxy->>Proxy: Mint Elevated JIT Token (TTL: 60s)

&#x20;       Proxy->>Upstream: Execute Authorized Action

&#x20;       Upstream-->>Proxy: Execution Result

&#x20;       Proxy-->>Agent: Tool Completed

&#x20;   end

```



\---



\## 4. Core Security Capabilities



1\. \*\*Policy-Based Operational Boundaries (NIST AI RMF MAP-1.5):\*\*

&#x20;  \* Predefined boundaries restrict agents to authorized tools. Unregistered tool calls trigger immediate `403 Forbidden` responses.

2\. \*\*Just-In-Time (JIT) Ephemeral Token Minting (Zero Trust ZT-NHI-AUTH-03):\*\*

&#x20;  \* Agents hold zero standing write credentials. Tokens are minted on-demand with minimal time-to-live (TTL) and discarded immediately after use.

3\. \*\*Human-in-the-Loop (HITL) Interception (NIST AI RMF GOVERN-1.2):\*\*

&#x20;  \* Destructive actions (`WRITE`, `DELETE`, password resets) are intercepted, frozen into a pending state, and gated until an authorized human issues approval.

4\. \*\*Session-Bound Identity Attribution:\*\*

&#x20;  \* Downstream requests trace back to the initiating user session (`x-forwarded-session`) rather than an anonymous, shared non-human service principal.



\---



\## 5. Policy Configuration Schema (`policy.json`)



Operational boundaries are declared in `policy.json`:



```json

{

&#x20; "policies": \[

&#x20;   {

&#x20;     "tool\_name": "get\_user\_profile",

&#x20;     "action": "READ",

&#x20;     "risk\_level": "LOW",

&#x20;     "requires\_hitl": false,

&#x20;     "max\_token\_ttl\_seconds": 300

&#x20;   },

&#x20;   {

&#x20;     "tool\_name": "list\_security\_alerts",

&#x20;     "action": "READ",

&#x20;     "risk\_level": "LOW",

&#x20;     "requires\_hitl": false,

&#x20;     "max\_token\_ttl\_seconds": 300

&#x20;   },

&#x20;   {

&#x20;     "tool\_name": "reset\_user\_password",

&#x20;     "action": "WRITE",

&#x20;     "risk\_level": "HIGH",

&#x20;     "requires\_hitl": true,

&#x20;     "max\_token\_ttl\_seconds": 60

&#x20;   },

&#x20;   {

&#x20;     "tool\_name": "delete\_database\_record",

&#x20;     "action": "DELETE",

&#x20;     "risk\_level": "CRITICAL",

&#x20;     "requires\_hitl": true,

&#x20;     "max\_token\_ttl\_seconds": 60

&#x20;   }

&#x20; ]

}

```



\---



\## 6. API Reference



| Endpoint | Method | Purpose |

| :--- | :--- | :--- |

| `/health` | `GET` | Health check and loaded policy count |

| `/tool/execute` | `POST` | Primary tool-call interceptor; returns execution result or HITL challenge |

| `/approval/pending` | `GET` | Lists actions awaiting human sign-off |

| `/approval/decision` | `POST` | Authorizes or rejects a pending intercepted action |



\---



\## 7. Quickstart



\### Prerequisites

\* Python 3.10+

\* Virtual environment (`venv`)



\### Setup \& Run

```powershell

\# Clone the repository

git clone \[https://github.com/ggrajek/agent-priv-proxy.git](https://github.com/ggrajek/agent-priv-proxy.git)

cd agent-priv-proxy



\# Set up environment

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

pip install -r requirements.txt



\# Start the proxy gateway

uvicorn proxy:app --reload --port 8000

```

