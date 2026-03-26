# H1 — Distributed Automation Cluster

> **Важно:** `NATS_SERVERS` и `NATS_TOKEN` берутся **только из `.env`** — ничего не нужно менять в коде при установке на новых Heavy или Light серверах. Достаточно заполнить `.env` по шаблону `.env.example`.

H1 is a distributed task automation system built on [NATS](https://nats.io/) messaging.  
It consists of **Heavy** servers (NATS + Orchestrator) and **Light** workers (Playwright executors).

## Quick Start

### 1. Connect to VPN
See [docs/VPN_AND_ACCESS.md](docs/VPN_AND_ACCESS.md)

### 2. Deploy Heavy Server
See [docs/INSTALL_HEAVY.md](docs/INSTALL_HEAVY.md)

### 3. Deploy Light Workers
See [docs/INSTALL_LIGHT.md](docs/INSTALL_LIGHT.md)

### 4. Run Tests
See [docs/TESTS.md](docs/TESTS.md)

## Architecture

```
Client → VPN → Heavy (NATS + Orchestrator) → Light Workers
```

See [docs/ARCHITECTURE_ONE_HEAVY.md](docs/ARCHITECTURE_ONE_HEAVY.md) for full diagram.

## Repository Structure

```
h1-repo/
├── h1_server/                  # Heavy server components
│   ├── orchestrator.py         # Intent router (intents.mcp)
│   ├── security_monitor.py     # Event logger (h1.system.events)
│   ├── nats-server.conf        # NATS configuration template
│   ├── requirements.txt        # Python dependencies
│   ├── install_service.bat     # Windows service installer
│   └── .env.example            # Environment template
│
├── h1_light_worker/            # Light worker components
│   ├── worker_playwright.py    # Playwright task executor
│   ├── requirements.txt        # Python dependencies
│   ├── install_dependencies.bat
│   ├── install_service.bat     # Windows service installer
│   └── .env.example            # Environment template
│
├── tests/                      # End-to-end tests
│   ├── test_publisher.py       # Basic connectivity test
│   └── test_orchestrator_reply.py  # Orchestrator Request/Reply test
│
└── docs/                       # Documentation
    ├── ARCHITECTURE_ONE_HEAVY.md
    ├── INSTALL_HEAVY.md
    ├── INSTALL_LIGHT.md
    ├── VPN_AND_ACCESS.md
    └── TESTS.md
```

## NATS Topics

| Topic | Description |
|-------|-------------|
| `intents.mcp` | Client → Orchestrator commands |
| `intents.responses` | Orchestrator → Client replies |
| `h1.system.events` | System events (security monitor) |
| `tasks.hhparse` | Orchestrator → Workers tasks |
| `tasks.results` | Workers → Orchestrator results |

## Requirements

- Windows 10/11 or Windows Server 2019+
- Python 3.10+
- NATS Server 2.10+ (`nats-server.exe`)
- VPN access to the H1 subnet

## Security Notes

- Never commit `.env` files with real tokens
- Use strong random tokens for `NATS_TOKEN`
- Keep `nats-server.conf` tokens in sync with `.env`
- All `.env` files are excluded via `.gitignore`
