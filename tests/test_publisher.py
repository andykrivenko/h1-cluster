"""
H1 Test Publisher — End-to-end NATS connectivity test
Usage: python test_publisher.py
Requires: .env with NATS_SERVERS and NATS_TOKEN
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
NATS_SERVERS = [s.strip() for s in NATS_SERVERS_STR.split(',')]
NATS_TOKEN = os.getenv("NATS_TOKEN", "")


async def main():
    print(f"[*] Connecting to NATS: {NATS_SERVERS}")

    options = {"servers": NATS_SERVERS, "connect_timeout": 10, "name": "H1-TestPublisher"}
    if NATS_TOKEN:
        options["token"] = NATS_TOKEN

    nc = await nats.connect(**options)
    print(f"[+] Connected to {nc.connected_url.netloc}")

    # Test 1: Pub/Sub
    print("\n[Test 1] Pub/Sub on h1.system.events...")
    received = []
    sub = await nc.subscribe("h1.system.events", cb=lambda m: received.append(m))
    await nc.publish("h1.system.events", json.dumps({"type": "test", "source": "test_publisher"}).encode())
    await asyncio.sleep(1)
    await sub.unsubscribe()
    print(f"  Result: {'PASS' if received else 'FAIL'} ({len(received)} messages)")

    # Test 2: Request/Reply to Orchestrator
    print("\n[Test 2] Request/Reply on intents.mcp...")
    intent = {"action": "ping_test", "target": "orchestrator", "details": "test_publisher check"}
    try:
        msg = await nc.request("intents.mcp", json.dumps(intent).encode(), timeout=5.0)
        response = json.loads(msg.data.decode())
        print(f"  Result: PASS")
        print(f"  Received reply: {json.dumps(response, indent=2)}")
    except NatsTimeout:
        print(f"  Result: FAIL (timeout — Orchestrator not running?)")
    except Exception as e:
        print(f"  Result: FAIL ({type(e).__name__}: {e})")

    await nc.drain()
    print("\n[*] Test complete.")


if __name__ == '__main__':
    asyncio.run(main())
