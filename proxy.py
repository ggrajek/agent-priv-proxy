import json
import uuid
import datetime
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="Agent Privilege & Guardrail Proxy", version="1.0.0")

# Load operational boundary policies
with open("policy.json", "r") as f:
    POLICIES = {p["tool_name"]: p for p in json.load(f)["policies"]}

class ToolExecutionRequest(BaseModel):
    agent_id: str
    tool_name: str
    parameters: Dict[str, Any]
    user_session_id: Optional[str] = None

class ApprovalDecisionRequest(BaseModel):
    request_id: str
    approved: bool
    approver: str

# In-memory store for pending HITL requests
PENDING_APPROVALS: Dict[str, Dict[str, Any]] = {}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "agent-priv-proxy", "policies_loaded": len(POLICIES)}

@app.post("/tool/execute")
def intercept_tool_call(
    req: ToolExecutionRequest,
    x_forwarded_session: Optional[str] = Header(None)
):
    session_id = req.user_session_id or x_forwarded_session or "UNATTRIBUTED_SESSION"

    # 1. Enforce Operational Boundary: Check if tool is recognized
    if req.tool_name not in POLICIES:
        raise HTTPException(
            status_code=403, 
            detail=f"[VIOLATION] Tool '{req.tool_name}' is not authorized in execution boundary."
        )

    policy = POLICIES[req.tool_name]
    req_id = str(uuid.uuid4())

    # 2. Enforce Human-in-the-Loop (HITL) for HIGH/CRITICAL actions
    if policy["requires_hitl"]:
        PENDING_APPROVALS[req_id] = {
            "request_id": req_id,
            "agent_id": req.agent_id,
            "tool_name": req.tool_name,
            "parameters": req.parameters,
            "session_id": session_id,
            "risk_level": policy["risk_level"],
            "status": "PENDING_APPROVAL",
            "created_at": datetime.datetime.utcnow().isoformat()
        }
        return {
            "status": "INTERCEPTED",
            "message": f"Action requires Human-in-the-Loop (HITL) authorization due to {policy['risk_level']} risk.",
            "request_id": req_id,
            "required_approval_endpoint": f"/approval/{req_id}"
        }

    # 3. Mint short-lived ephemeral token for low-risk actions
    ephemeral_token = f"ephem_{uuid.uuid4().hex[:12]}_{policy['max_token_ttl_seconds']}s"

    return {
        "status": "APPROVED_AUTO",
        "action": "EXECUTING",
        "agent_id": req.agent_id,
        "tool_name": req.tool_name,
        "session_attribution": session_id,
        "ephemeral_token": ephemeral_token,
        "ttl_seconds": policy["max_token_ttl_seconds"],
        "result": f"Successfully simulated execution of {req.tool_name} with parameters: {req.parameters}"
    }

@app.get("/approval/pending")
def list_pending_approvals():
    return {"pending_count": len(PENDING_APPROVALS), "requests": list(PENDING_APPROVALS.values())}

@app.post("/approval/decision")
def process_approval(decision: ApprovalDecisionRequest):
    if decision.request_id not in PENDING_APPROVALS:
        raise HTTPException(status_code=404, detail="Approval request not found.")

    record = PENDING_APPROVALS[decision.request_id]
    if not decision.approved:
        record["status"] = "REJECTED"
        record["decision_by"] = decision.approver
        return {"status": "BLOCKED", "detail": f"Execution rejected by {decision.approver}."}

    record["status"] = "APPROVED_BY_HUMAN"
    record["decision_by"] = decision.approver

    # Mint elevated ephemeral token
    ephemeral_token = f"ephem_hitl_{uuid.uuid4().hex[:12]}_60s"
    return {
        "status": "APPROVED",
        "detail": f"Human approval granted by {decision.approver}. Ephemeral credential minted.",
        "ephemeral_token": ephemeral_token,
        "executing_tool": record["tool_name"],
        "parameters": record["parameters"]
    }
