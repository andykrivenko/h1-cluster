# H1 Tests — How to Run

## Prerequisites

1. VPN connected (see [VPN_AND_ACCESS.md](VPN_AND_ACCESS.md))
2. Python 3.10+ installed
3. Dependencies installed: `pip install nats-py python-dotenv`
4. `.env` file configured in `tests/` directory

## Setup

Create `tests/.env`:
```env
NATS_SERVERS=nats://192.168.XX.11:4222,nats://192.168.XX.12:4222
NATS_TOKEN=your_secret_token_here
```

## Test 1: Basic NATS connectivity (`test_publisher.py`)

Tests Pub/Sub and Request/Reply through the cluster.

```cmd
cd tests
python test_publisher.py
```

### Expected output (SUCCESS)

```
[*] Connecting to NATS: ['nats://192.168.XX.11:4222', ...]
[+] Connected to 192.168.XX.11:4222!

[Test 1] Pub/Sub on h1.system.events...
  Result: PASS (1 messages)

[Test 2] Request/Reply on intents.mcp...
  Result: PASS
  Received reply: {
    "status": "accepted",
    "message": "Intent 'ping_test' received and processed",
    "received_action": "ping_test",
    "received_target": "orchestrator",
    "orchestrator": "H1-Orchestrator",
    "server": "HEAVY-1"
  }

[*] Test complete.
```

## Test 2: Orchestrator reply (`test_orchestrator_reply.py`)

Direct test of the Orchestrator's Request/Reply.

```cmd
cd tests
python test_orchestrator_reply.py
```

### Expected output (SUCCESS)

```
[*] Connecting to NATS: [...]
[+] Connected to 192.168.XX.11:4222!
[*] Sending request to 'intents.mcp': {...}

[+] SUCCESS! Received reply from Orchestrator:
{
  "status": "accepted",
  "message": "Intent 'ping_test' received and processed",
  ...
}

[*] Done.
```

## Interpreting Results

| Result | Meaning |
|--------|---------|
| `PASS` / `SUCCESS` | Component working correctly |
| `FAIL (timeout)` | Orchestrator not running — check `schtasks /query /tn "H1_Orchestrator"` |
| `Authorization Violation` | Wrong `NATS_TOKEN` — check `.env` and `nats-server.conf` |
| `Connection refused` | NATS not running or VPN not connected |
| `NoRespondersError` | Orchestrator not subscribed to `intents.mcp` |

## NATS Monitoring (no auth required)

```cmd
:: Server health
curl http://192.168.XX.11:8222/healthz

:: Active connections and subscriptions
curl http://192.168.XX.11:8222/connz?subs=1

:: Server stats
curl http://192.168.XX.11:8222/varz
```
