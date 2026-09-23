"""
SAP Integration Suite - Model Context Protocol (MCP) Server
Exposes curated SAP S/4HANA Sales Operations and Stock Availability tools to AI Agents.
Governed via SAP Integration Suite / Integration Cell API endpoint.
"""

import sys
import json
import os
import urllib.request
import urllib.error

# Target API endpoint (SAP Integration Suite or local mock backend)
API_BASE_URL = os.environ.get(
    "SAP_IS_ENDPOINT",
    "http://localhost:8080/sales-ops"
)
API_KEY = os.environ.get("SAP_IS_API_KEY", "")
BEARER_TOKEN = os.environ.get("SAP_IS_BEARER_TOKEN", "")

# Curated MCP Tools matching our OpenAPI specification
TOOLS = [
    {
        "name": "get_open_sales_orders",
        "description": (
            "Retrieves a list of open or blocked sales orders for a specific customer. "
            "Use this tool when evaluating order fulfillment or identifying delivery delays."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["customerId"],
            "properties": {
                "customerId": {
                    "type": "string",
                    "description": "10-digit SAP Customer / Sold-to Party ID (e.g., '10000001')",
                },
                "orderStatus": {
                    "type": "string",
                    "enum": ["ALL", "BLOCKED", "OPEN", "PENDING_DELIVERY"],
                    "default": "ALL",
                    "description": "Filter by status: ALL, BLOCKED, OPEN, PENDING_DELIVERY",
                }
            }
        }
    },
    {
        "name": "get_sales_order_details",
        "description": (
            "Fetches detailed header, line items, and active delivery block reasons "
            "for a specific sales order. Use this to diagnose why an order cannot ship."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["salesOrderId"],
            "properties": {
                "salesOrderId": {
                    "type": "string",
                    "description": "The SAP Sales Order document number (e.g., '50000123')",
                }
            }
        }
    },
    {
        "name": "simulate_block_release",
        "description": (
            "Simulates the release of a delivery block (e.g., Credit Limit or Export Control). "
            "Recalculates credit exposure and ATP stock feasibility without committing changes."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["salesOrderId", "blockReasonCode", "justification"],
            "properties": {
                "salesOrderId": {
                    "type": "string",
                    "description": "The Sales Order number to simulate clearance for",
                },
                "blockReasonCode": {
                    "type": "string",
                    "description": "SAP Block Reason Code to clear (e.g. '01' for Credit Limit)",
                },
                "justification": {
                    "type": "string",
                    "description": "Business justification for audit logging",
                }
            }
        }
    },
    {
        "name": "check_material_stock",
        "description": (
            "Checks available-to-promise (ATP) and unrestricted stock for a product across distribution centers. "
            "Use this when verifying inventory availability."
        ),
        "inputSchema": {
            "type": "object",
            "required": ["materialNumber"],
            "properties": {
                "materialNumber": {
                    "type": "string",
                    "description": "SAP Material / SKU number (e.g., 'MAT-1002')",
                },
                "plant": {
                    "type": "string",
                    "description": "Optional 4-character SAP Plant code (e.g., '1010')",
                }
            }
        }
    }
]

# In-memory mock database for instant standalone demonstration
MOCK_DATA = {
    "orders": [
        {
            "salesOrderId": "50000123",
            "customerId": "10000001",
            "customerName": "Acme Retail Global Ltd",
            "orderDate": "2026-09-18",
            "netAmount": 45200.50,
            "currency": "EUR",
            "deliveryBlockStatus": "BLOCKED",
            "overallStatus": "In Processing",
            "deliveryBlockCode": "01",
            "deliveryBlockDescription": "Credit Limit Exceeded",
            "creditExposurePercent": 104.5,
            "items": [
                {
                    "itemNumber": "10",
                    "materialNumber": "MAT-1002",
                    "description": "Industrial Sensor Hub X1",
                    "orderQuantity": 50,
                    "confirmedQuantity": 50,
                    "unitPrice": 904.01
                }
            ]
        },
        {
            "salesOrderId": "50000124",
            "customerId": "10000001",
            "customerName": "Acme Retail Global Ltd",
            "orderDate": "2026-09-21",
            "netAmount": 12800.00,
            "currency": "EUR",
            "deliveryBlockStatus": "NONE",
            "overallStatus": "Open",
            "deliveryBlockCode": "",
            "deliveryBlockDescription": "None",
            "creditExposurePercent": 92.0,
            "items": [
                {
                    "itemNumber": "10",
                    "materialNumber": "MAT-1005",
                    "description": "Smart Relay Controller",
                    "orderQuantity": 20,
                    "confirmedQuantity": 20,
                    "unitPrice": 640.00
                }
            ]
        }
    ],
    "stock": {
        "MAT-1002": [
            {"plant": "1010", "plantName": "Frankfurt Logistics Hub", "unrestrictedStock": 320, "reservedStock": 45, "availableToPromise": 275},
            {"plant": "1020", "plantName": "London Distribution Center", "unrestrictedStock": 80, "reservedStock": 10, "availableToPromise": 70}
        ],
        "MAT-1005": [
            {"plant": "1010", "plantName": "Frankfurt Logistics Hub", "unrestrictedStock": 150, "reservedStock": 20, "availableToPromise": 130}
        ]
    }
}


def call_backend(endpoint_path, method="GET", payload=None):
    """Attempts to call the real SAP Integration Suite endpoint; falls back to mock data."""
    url = f"{API_BASE_URL.rstrip('/')}/{endpoint_path.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    if BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    elif API_KEY:
        headers["apikey"] = API_KEY

    try:
        data_bytes = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        # Fallback to rich local mock engine for standalone POC execution
        return execute_mock(endpoint_path, method, payload)


def execute_mock(path, method, payload):
    if path.startswith("orders") and "/" not in path.split("?")[0]:
        return MOCK_DATA["orders"]
    elif path.startswith("orders/") and "simulate-block-release" in path:
        order_id = path.split("/")[1]
        return {
            "salesOrderId": order_id,
            "simulationStatus": "ELIGIBLE_FOR_RELEASE",
            "canAutoRelease": True,
            "riskScore": "LOW",
            "diagnostics": [
                "Credit exposure recalculated at 92.4% following pending wire transfer allocation.",
                "Inventory confirmed in Plant 1010 for all line items.",
                "Customer payment history rated Tier 1 (Low Risk)."
            ],
            "recommendedNextStep": "Proceed with formal release in SAP S/4HANA via Integration Suite workflow."
        }
    elif path.startswith("orders/"):
        order_id = path.split("/")[1]
        for o in MOCK_DATA["orders"]:
            if o["salesOrderId"] == order_id:
                return o
        return {"error": f"Sales order {order_id} not found"}
    elif path.startswith("stock"):
        mat = payload.get("materialNumber") if payload else "MAT-1002"
        return MOCK_DATA["stock"].get(mat, [])
    return {"message": "Success"}


def handle_tool_call(tool_name, arguments):
    if tool_name == "get_open_sales_orders":
        cust = arguments.get("customerId")
        status = arguments.get("orderStatus", "ALL")
        orders = call_backend(f"orders?customerId={cust}&orderStatus={status}")
        if status == "BLOCKED":
            orders = [o for o in orders if o.get("deliveryBlockStatus") == "BLOCKED"]
        return {"orders": orders, "count": len(orders)}

    elif tool_name == "get_sales_order_details":
        order_id = arguments.get("salesOrderId")
        return call_backend(f"orders/{order_id}")

    elif tool_name == "simulate_block_release":
        order_id = arguments.get("salesOrderId")
        return call_backend(
            f"orders/{order_id}/simulate-block-release",
            method="POST",
            payload=arguments
        )

    elif tool_name == "check_material_stock":
        mat = arguments.get("materialNumber")
        plant = arguments.get("plant", "")
        return call_backend("stock/check", payload={"materialNumber": mat, "plant": plant})

    return {"error": f"Unknown tool: {tool_name}"}


def main():
    """Standard JSON-RPC 2.0 stdio handler for Model Context Protocol."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method")

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "SAP-Integration-Suite-MCP-Gateway",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {}
                    }
                }
            }
        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            }
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            tool_result = handle_tool_call(name, arguments)
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_result, indent=2)
                        }
                    ]
                }
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {}
            }

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
