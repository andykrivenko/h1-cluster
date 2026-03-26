"""
H1 Test Worker Task — end-to-end test: publish task to tasks.hhparse, wait for result
"""
import asyncio
import json
import sys
import time
import uuid

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import nats
from nats.errors import TimeoutError as NatsTimeout

SERVERS = ['nats://192.168.99.11:4222', 'nats://192.168.99.12:4222']
TOKEN = 'h1_secret_token'

TASK_TOPIC = 'tasks.hhparse'
RESULT_TOPIC = 'tasks.results'


async def main():
    print("=" * 60)
    print("H1 WORKER TASK TEST")
    print("=" * 60)

    nc = await nats.connect(
        servers=SERVERS,
        token=TOKEN,
        connect_timeout=10,
        name='H1-TaskTest'
    )
    print(f"[+] Connected to {nc.connected_url.netloc}")

    task_id = str(uuid.uuid4())[:8]
    task = {
        "task_id": task_id,
        "type": "hhparse",
        "url": "https://hh.ru/vacancy/test",
        "source": "H1-TaskTest",
        "timestamp": time.time()
    }

    print(f"\n[1] Publishing task to '{TASK_TOPIC}':")
    print(f"    task_id={task_id}")
    print(f"    type={task['type']}")

    # Subscribe to results first
    results = []
    async def result_handler(msg):
        try:
            data = json.loads(msg.data.decode('utf-8', errors='replace'))
            if data.get('task_id') == task_id:
                results.append(data)
                print(f"\n[+] RESULT RECEIVED from worker!")
                print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"    Result parse error: {e}")

    sub_results = await nc.subscribe(RESULT_TOPIC, cb=result_handler)

    # Test 1: Publish (fire-and-forget)
    await nc.publish(TASK_TOPIC, json.dumps(task).encode())
    print(f"    Published! Waiting 3s for result on '{RESULT_TOPIC}'...")
    await asyncio.sleep(3)

    if results:
        print(f"\n[+] Test 1 PASS: Worker processed task and sent result")
        worker_host = results[0].get('worker_id', results[0].get('worker_host', 'unknown'))
        print(f"    Processed by: {worker_host}")
    else:
        print(f"\n[!] Test 1: No result received (worker may not publish to {RESULT_TOPIC})")

    # Test 2: Request/Reply
    print(f"\n[2] Request/Reply to '{TASK_TOPIC}'...")
    task2 = {**task, "task_id": str(uuid.uuid4())[:8], "type": "ping"}
    try:
        msg = await nc.request(TASK_TOPIC, json.dumps(task2).encode(), timeout=5.0)
        reply = json.loads(msg.data.decode('utf-8', errors='replace'))
        print(f"[+] Test 2 PASS: Worker replied!")
        print(json.dumps(reply, indent=2, ensure_ascii=False))
    except NatsTimeout:
        print(f"[!] Test 2: No reply (timeout) — worker may not support request/reply yet")
    except Exception as e:
        print(f"[!] Test 2 ERROR: {type(e).__name__}: {e}")

    await sub_results.unsubscribe()
    await nc.drain()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    asyncio.run(main())
