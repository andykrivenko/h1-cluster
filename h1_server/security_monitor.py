"""
H1 Security Monitor — Heavy Server Component
Subscribes to h1.system.events and logs all security events.
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
LOG_FILE = os.getenv("LOG_FILE", "C:\\H1_Server\\logs\\security.log")

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

LISTEN_TOPIC = "h1.system.events"


async def handle_event(msg):
    """Handle incoming security events"""
    try:
        data = json.loads(msg.data.decode('utf-8'))
        event_type = data.get('type', 'unknown')
        source = data.get('source', 'unknown')
        logger.info(f"[EVENT] type={event_type} source={source} data={json.dumps(data)}")
    except Exception as e:
        logger.error(f"Error handling event: {e}, raw: {msg.data[:200]}")


async def main():
    logger.info("H1 Security Monitor starting...")
    logger.info(f"NATS servers: {NATS_SERVERS}")
    logger.info(f"Listen topic: {LISTEN_TOPIC}")

    options = {
        "servers": NATS_SERVERS,
        "connect_timeout": 10,
        "name": "H1-SecurityMonitor"
    }
    if NATS_TOKEN:
        options["token"] = NATS_TOKEN

    try:
        nc = await nats.connect(**options)
        logger.info(f"Connected to NATS: {nc.connected_url.netloc}")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}")
        raise

    sub = await nc.subscribe(LISTEN_TOPIC, cb=handle_event)
    logger.info(f"Subscribed to '{LISTEN_TOPIC}'. Monitoring...")

    # Publish startup event
    startup_event = {
        "type": "monitor_started",
        "source": "H1-SecurityMonitor",
        "timestamp": datetime.utcnow().isoformat(),
        "server": os.environ.get("COMPUTERNAME", "unknown")
    }
    await nc.publish(LISTEN_TOPIC, json.dumps(startup_event).encode())

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
