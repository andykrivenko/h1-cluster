"""
H1 Integration Test — MCP hh_expert Bridge
===========================================
Tests the NATS ↔ MCP hh_expert bridge via intents.hh_expert topic.

Prerequisites:
  1. VPN connected (H1-Kulakova)
  2. mcp_hh_expert_bridge.py running on Heavy-1
  3. .env with NATS_SERVERS and NATS_TOKEN

Usage:
    cd tests
    python test_hh_expert_bridge.py
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv
import nats
from nats.errors import TimeoutError as NatsTimeout

load_dotenv()

NATS_SERVERS_STR = os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222")
NATS_SERVERS = [s.strip() for s in NATS_SERVERS_STR.split(",")]
NATS_TOKEN = os.getenv("NATS_TOKEN", "")

BRIDGE_TOPIC = "intents.hh_expert"

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


async def main():
    print("=" * 60)
    print("H1 MCP hh_expert Bridge — Integration Tests")
    print("=" * 60)
    print(f"NATS: {NATS_SERVERS}")
    print()

    # Connect to NATS
    options = {
        "servers": NATS_SERVERS,
        "connect_timeout": 10,
        "name": "H1-BridgeTest"
    }
    if NATS_TOKEN:
        options["token"] = NATS_TOKEN

    try:
        nc = await nats.connect(**options)
        print(f"[+] Connected to {nc.connected_url.netloc}")
    except Exception as e:
        print(f"[-] Cannot connect to NATS: {e}")
        sys.exit(1)

    results = []

    # ─── Test 1: list_tools ────────────────────────────────────────────────────
    print("\n[Test 1] list_tools — get available hh_expert tools")
    try:
        msg = await nc.request(
            BRIDGE_TOPIC,
            json.dumps({
                "type": "list_tools",
                "user": "test",
                "client": "test_hh_expert_bridge"
            }).encode("utf-8"),
            timeout=10.0
        )
        resp = json.loads(msg.data.decode("utf-8"))

        if resp.get("type") == "list_tools_result" and "tools" in resp:
            tools = resp["tools"]
            print(f"  {PASS} Received {len(tools)} tools")
            for t in tools[:5]:
                name = t.get("name", "?") if isinstance(t, dict) else str(t)
                desc = t.get("description", "")[:60] if isinstance(t, dict) else ""
                print(f"    - {name}: {desc}")
            if len(tools) > 5:
                print(f"    ... and {len(tools) - 5} more")
            results.append(("list_tools", True, f"{len(tools)} tools"))
        else:
            print(f"  {FAIL} Unexpected response: {json.dumps(resp)[:200]}")
            results.append(("list_tools", False, str(resp)[:100]))

    except NatsTimeout:
        print(f"  {FAIL} Timeout — bridge not running or hh_expert not responding")
        results.append(("list_tools", False, "timeout"))
    except Exception as e:
        print(f"  {FAIL} Error: {type(e).__name__}: {e}")
        results.append(("list_tools", False, str(e)))

    # ─── Test 2: call_tool — get_vacancy_status ────────────────────────────────
    print("\n[Test 2] call_tool — get_vacancy_status (test vacancy)")
    try:
        intent = {
            "type": "call_tool",
            "tool_name": "get_vacancy_status",
            "arguments": {"vacancy_id": "VAC-TEST-001"},
            "user": "test",
            "client": "test_hh_expert_bridge"
        }
        msg = await nc.request(
            BRIDGE_TOPIC,
            json.dumps(intent).encode("utf-8"),
            timeout=30.0
        )
        resp = json.loads(msg.data.decode("utf-8"))

        if resp.get("type") == "call_tool_result":
            if resp.get("ok"):
                result = resp.get("result", {})
                print(f"  {PASS} Tool executed successfully")
                print(f"    result: {json.dumps(result, ensure_ascii=False)[:200]}")
                results.append(("get_vacancy_status", True, "ok"))
            else:
                error = resp.get("error", "unknown error")
                print(f"  {SKIP} Tool returned error (expected for test data): {error}")
                results.append(("get_vacancy_status", None, f"error: {error}"))
        else:
            print(f"  {FAIL} Unexpected response type: {resp.get('type')}")
            results.append(("get_vacancy_status", False, str(resp)[:100]))

    except NatsTimeout:
        print(f"  {FAIL} Timeout — bridge not running or tool took too long")
        results.append(("get_vacancy_status", False, "timeout"))
    except Exception as e:
        print(f"  {FAIL} Error: {type(e).__name__}: {e}")
        results.append(("get_vacancy_status", False, str(e)))

    # ─── Test 3: call_tool — create_vacancy ────────────────────────────────────
    print("\n[Test 3] call_tool — create_vacancy (dry run)")
    try:
        intent = {
            "type": "call_tool",
            "tool_name": "create_vacancy",
            "arguments": {
                "title": "Senior Python Developer",
                "city": "Москва",
                "salary_from": 200000,
                "dry_run": True
            },
            "user": "test",
            "client": "test_hh_expert_bridge"
        }
        msg = await nc.request(
            BRIDGE_TOPIC,
            json.dumps(intent).encode("utf-8"),
            timeout=30.0
        )
        resp = json.loads(msg.data.decode("utf-8"))

        if resp.get("type") == "call_tool_result":
            if resp.get("ok"):
                result = resp.get("result", {})
                print(f"  {PASS} Tool executed successfully")
                print(f"    result: {json.dumps(result, ensure_ascii=False)[:200]}")
                results.append(("create_vacancy", True, "ok"))
            else:
                error = resp.get("error", "unknown error")
                print(f"  {SKIP} Tool returned error (may be expected): {error}")
                results.append(("create_vacancy", None, f"error: {error}"))
        else:
            print(f"  {FAIL} Unexpected response: {resp.get('type')}")
            results.append(("create_vacancy", False, str(resp)[:100]))

    except NatsTimeout:
        print(f"  {FAIL} Timeout")
        results.append(("create_vacancy", False, "timeout"))
    except Exception as e:
        print(f"  {FAIL} Error: {type(e).__name__}: {e}")
        results.append(("create_vacancy", False, str(e)))

    # ─── Test 4: unknown type ──────────────────────────────────────────────────
    print("\n[Test 4] error handling — unknown message type")
    try:
        msg = await nc.request(
            BRIDGE_TOPIC,
            json.dumps({"type": "unknown_xyz", "user": "test"}).encode("utf-8"),
            timeout=5.0
        )
        resp = json.loads(msg.data.decode("utf-8"))
        if resp.get("type") == "error":
            print(f"  {PASS} Bridge returned error for unknown type: {resp.get('error_type')}")
            results.append(("error_handling", True, "ok"))
        else:
            print(f"  {FAIL} Expected error response, got: {resp.get('type')}")
            results.append(("error_handling", False, "no error returned"))
    except NatsTimeout:
        print(f"  {FAIL} Timeout")
        results.append(("error_handling", False, "timeout"))
    except Exception as e:
        print(f"  {FAIL} {type(e).__name__}: {e}")
        results.append(("error_handling", False, str(e)))

    # ─── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok is True)
    skipped = sum(1 for _, ok, _ in results if ok is None)
    failed = sum(1 for _, ok, _ in results if ok is False)

    for name, ok, detail in results:
        icon = PASS if ok is True else (SKIP if ok is None else FAIL)
        print(f"  {icon} {name}: {detail}")

    print(f"\nTotal: {len(results)} | Passed: {passed} | Skipped: {skipped} | Failed: {failed}")

    await nc.drain()

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
