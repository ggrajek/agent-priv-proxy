import httpx
import json

BASE_URL = "http://127.0.0.1:8000"

def test_pipeline():
    client = httpx.Client(base_url=BASE_URL)

    # 1. Health check
    print("\n--- 1. Testing Health Endpoint ---")
    resp = client.get("/health")
    print(f"Health Response: {resp.json()}")

    # 2. Test Low-Risk Tool (Auto-approved + Ephemeral Token)
    print("\n--- 2. Executing Low-Risk Action (get_user_profile) ---")
    low_risk_payload = {
        "agent_id": "secops-triage-copilot-01",
        "tool_name": "get_user_profile",
        "parameters": {"user_id": "user-4892"},
        "user_session_id": "sess-live-9921"
    }
    resp = client.post("/tool/execute", json=low_risk_payload)
    print("Response:")
    print(json.dumps(resp.json(), indent=2))

    # 3. Test High-Risk Tool (HITL Intercepted)
    print("\n--- 3. Executing High-Risk Action (reset_user_password) ---")
    high_risk_payload = {
        "agent_id": "tier2-support-agent-02",
        "tool_name": "reset_user_password",
        "parameters": {"target_account": "admin@contoso.com", "force_mfa": True},
        "user_session_id": "sess-live-9921"
    }
    resp = client.post("/tool/execute", json=high_risk_payload)
    intercepted_data = resp.json()
    print("Response:")
    print(json.dumps(intercepted_data, indent=2))

    request_id = intercepted_data.get("request_id")
    if not request_id:
        print("[-] Interception failed or request_id missing.")
        return

    # 4. Check Pending Approval Queue
    print("\n--- 4. Checking Pending HITL Queue ---")
    resp = client.get("/approval/pending")
    print("Pending Queue:")
    print(json.dumps(resp.json(), indent=2))

    # 5. Simulate Human Approver Decision
    print(f"\n--- 5. Simulating Human Sign-Off for Request ID: {request_id} ---")
    approval_payload = {
        "request_id": request_id,
        "approved": True,
        "approver": "secops-admin@contoso.com"
    }
    resp = client.post("/approval/decision", json=approval_payload)
    print("Approval Response:")
    print(json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    test_pipeline()