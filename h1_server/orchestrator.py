import asyncio
import json
import os
import nats

# Читаем настройки из переменных окружения (или .env файла)
NATS_SERVERS_STR = os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222")
NATS_SERVERS = [s.strip() for s in NATS_SERVERS_STR.split(',')]
NATS_TOKEN = os.getenv("NATS_TOKEN", "")
LISTEN_TOPIC = "intents.mcp"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


async def handle_intent(msg):
    """Обработчик входящих intent-сообщений"""
    try:
        data = json.loads(msg.data.decode('utf-8'))
        action = data.get('action', 'unknown')
        target = data.get('target', 'unknown')
        details = data.get('details', '')

        print(f"[ORCHESTRATOR] Received intent: action={action}, target={target}, details={details}")

        # Формируем ответ
        response = {
            "status": "accepted",
            "message": f"Intent '{action}' received and processed",
            "received_action": action,
            "received_target": target,
            "orchestrator": "H1-Orchestrator",
            "server": os.environ.get("COMPUTERNAME", "Heavy-1")
        }

        # Отправляем ответ если есть reply subject
        if msg.reply:
            await msg.respond(json.dumps(response).encode('utf-8'))
            print(f"[ORCHESTRATOR] Sent reply to {msg.reply}")
        else:
            print(f"[ORCHESTRATOR] No reply subject, processed silently")

    except Exception as e:
        print(f"[ORCHESTRATOR] Error handling intent: {e}")
        if msg.reply:
            error_response = {"status": "error", "message": str(e)}
            await msg.respond(json.dumps(error_response).encode('utf-8'))


async def main():
    print(f"[ORCHESTRATOR] Starting H1 Orchestrator...")
    print(f"[ORCHESTRATOR] NATS servers: {NATS_SERVERS}")
    print(f"[ORCHESTRATOR] Listen topic: {LISTEN_TOPIC}")

    # Подключаемся к NATS с токеном
    options = {
        "servers": NATS_SERVERS,
        "token": NATS_TOKEN,
        "connect_timeout": 10,
        "name": "H1-Orchestrator"
    }

    try:
        nc = await nats.connect(**options)
        print(f"[ORCHESTRATOR] Connected to NATS: {nc.connected_url.netloc}")
    except Exception as e:
        print(f"[ORCHESTRATOR] Failed to connect to NATS: {e}")
        raise

    # Подписываемся на топик intents.mcp
    sub = await nc.subscribe(LISTEN_TOPIC, cb=handle_intent)
    print(f"[ORCHESTRATOR] Subscribed to '{LISTEN_TOPIC}'")
    print(f"[ORCHESTRATOR] Ready to process intents...")

    # Держим соединение открытым
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("[ORCHESTRATOR] Shutting down...")
    finally:
        await sub.unsubscribe()
        await nc.drain()
        print("[ORCHESTRATOR] Disconnected from NATS")


if __name__ == '__main__':
    asyncio.run(main())
