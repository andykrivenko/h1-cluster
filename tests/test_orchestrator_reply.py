import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from nats.aio.client import Client as NATS

async def main():
    nc = NATS()

    servers_str = os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222")
    servers = [s.strip() for s in servers_str.split(',')]
    token = os.getenv("NATS_TOKEN", "")

    print(f"[*] Connecting to NATS: {servers}")
    await nc.connect(servers=servers, token=token, connect_timeout=10)
    print(f"[+] Connected to {nc.connected_url.netloc}!")

    intent = {
        "action": "ping_test",
        "target": "orchestrator",
        "details": "Check end-to-end communication"
    }

    payload = json.dumps(intent).encode('utf-8')
    print(f"[*] Sending request to 'intents.mcp': {intent}")

    try:
        msg = await nc.request("intents.mcp", payload, timeout=5.0)
        response = json.loads(msg.data.decode('utf-8'))
        print("\n[+] SUCCESS! Received reply from Orchestrator:")
        print(json.dumps(response, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n[-] ERROR: {type(e).__name__}: {e}")

    await nc.close()
    print("\n[*] Done.")

if __name__ == '__main__':
    asyncio.run(main())
