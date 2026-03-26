"""
H1 Light Worker — Playwright-based task executor
Subscribes to task topics and executes browser automation tasks.
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import nats

# Load environment variables
load_dotenv()

NATS_SERVERS_STR = os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222")
NATS_SERVERS = [s.strip() for s in NATS_SERVERS_STR.split(',')]
NATS_TOKEN = os.getenv("NATS_TOKEN", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "C:\\H1_Node\\logs\\worker.log")
WORKER_ID = os.getenv("WORKER_ID", os.environ.get("COMPUTERNAME", "worker-1"))

# Configure logging
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

TASK_TOPIC = "tasks.hhparse"
RESULT_TOPIC = "tasks.results"
EVENTS_TOPIC = "h1.system.events"


async def handle_task(msg):
    """Handle incoming task"""
    try:
        task = json.loads(msg.data.decode('utf-8'))
        task_id = task.get('task_id', 'unknown')
        task_type = task.get('type', 'unknown')
        logger.info(f"[TASK] id={task_id} type={task_type}")

        # TODO: Implement actual Playwright task execution here
        # Example: await execute_playwright_task(task)

        result = {
            "task_id": task_id,
            "status": "completed",
            "worker_id": WORKER_ID,
            "timestamp": datetime.utcnow().isoformat(),
            "result": {}
        }

        # Send result back
        if msg.reply:
            await msg.respond(json.dumps(result).encode())
        else:
            # Publish to results topic
            nc = msg._client
            await nc.publish(RESULT_TOPIC, json.dumps(result).encode())

        logger.info(f"[TASK] id={task_id} completed")

    except Exception as e:
        logger.error(f"Error handling task: {e}")


async def main():
    logger.info(f"H1 Light Worker '{WORKER_ID}' starting...")
    logger.info(f"NATS servers: {NATS_SERVERS}")

    options = {
        "servers": NATS_SERVERS,
        "connect_timeout": 10,
        "reconnect_time_wait": 5,
        "max_reconnect_attempts": -1,  # Infinite reconnects
        "name": f"H1-Worker-{WORKER_ID}"
    }
    if NATS_TOKEN:
        options["token"] = NATS_TOKEN

    try:
        nc = await nats.connect(**options)
        logger.info(f"Connected to NATS: {nc.connected_url.netloc}")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")
        raise

    sub = await nc.subscribe(TASK_TOPIC, cb=handle_task)
    logger.info(f"Subscribed to '{TASK_TOPIC}'. Ready for tasks...")

    # Publish worker registration event
    reg_event = {
        "type": "worker_registered",
        "source": f"H1-Worker-{WORKER_ID}",
        "worker_id": WORKER_ID,
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": ["playwright", "hhparse"]
    }
    await nc.publish(EVENTS_TOPIC, json.dumps(reg_event).encode())

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await sub.unsubscribe()
        await nc.drain()
        logger.info("Disconnected from NATS")


if __name__ == '__main__':
    asyncio.run(main())
