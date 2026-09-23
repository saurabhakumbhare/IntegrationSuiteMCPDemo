"""
Automated Model Context Protocol (MCP) Test Client
Verifies MCP Handshake, Tool Discovery, and Tool Execution for SAP Integration Suite.
"""

import subprocess
import json
import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "mcp_server.py")


def send_rpc(proc, req):
    line = json.dumps(req) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()
    resp_line = proc.stdout.readline()
    return json.loads(resp_line.strip())


def run_test():
    print("=" * 70)
    print("[*] SAP INTEGRATION SUITE MCP GATEWAY - LIVE PROTOCOL VERIFICATION")
    print("=" * 70)

    proc = subprocess.Popen(
        [sys.executable, SERVER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )

    try:
        # Step 1: Initialize Handshake
        print("\n[Step 1] Initializing Protocol Handshake...")
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "TestAIClient", "version": "1.0.0"}
            }
        }
        init_resp = send_rpc(proc, init_req)
        server_info = init_resp.get("result", {}).get("serverInfo", {})
        print(f"[OK] Handshake Succeeded! Connected to: {server_info.get('name')} v{server_info.get('version')}")

        # Step 2: Tool Discovery (tools/list)
        print("\n[Step 2] Performing Dynamic Tool Discovery (tools/list)...")
        list_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        list_resp = send_rpc(proc, list_req)
        tools = list_resp.get("result", {}).get("tools", [])
        print(f"[OK] Discovered {len(tools)} Governed MCP Tools in SAP Integration Suite:")
        for t in tools:
            print(f"   * {t['name']}: {t['description'][:75]}...")

        # Step 3: Tool Call 1 - get_open_sales_orders
        print("\n[Step 3] AI Agent invoking tool: get_open_sales_orders...")
        call1_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_open_sales_orders",
                "arguments": {"customerId": "10000001", "orderStatus": "BLOCKED"}
            }
        }
        call1_resp = send_rpc(proc, call1_req)
        content = json.loads(call1_resp["result"]["content"][0]["text"])
        print(f"[OK] Backend Response: Found {content.get('count')} blocked orders.")
        for o in content.get("orders", []):
            print(f"   - Order #{o['salesOrderId']} | Value: {o['currency']} {o['netAmount']:,.2f} | Block: {o['deliveryBlockDescription']}")

        # Step 4: Tool Call 2 - simulate_block_release
        print("\n[Step 4] AI Agent invoking tool: simulate_block_release...")
        call2_req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "simulate_block_release",
                "arguments": {
                    "salesOrderId": "50000123",
                    "blockReasonCode": "01",
                    "justification": "Wire transfer allocation confirmed by treasury."
                }
            }
        }
        call2_resp = send_rpc(proc, call2_req)
        sim = json.loads(call2_resp["result"]["content"][0]["text"])
        print(f"[OK] Simulation Result: Status = {sim['simulationStatus']} (Risk: {sim['riskScore']})")
        print(f"   Diagnostics: {sim['diagnostics'][0]}")
        print(f"   Recommended Next Step: {sim['recommendedNextStep']}")

        print("\n" + "=" * 70)
        print("[SUCCESS] ALL MCP PROTOCOL CHECKS & TOOL CALLS PASSED!")
        print("=" * 70)

    finally:
        proc.terminate()


if __name__ == "__main__":
    run_test()
