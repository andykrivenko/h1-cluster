# H1 — Architecture and Deployment Plan

> **Last updated:** 2026-03-27  
> **Repository:** https://github.com/andykrivenko/h1-cluster  
> **Status:** Production-ready cluster, hh_expert migration in progress

---

## 1. Architecture and Roles

### 1.1. Core Principles

H1 is a **decentralized, role-based** distributed automation system built on NATS messaging.

**Single codebase, single config:**
- All code lives in `h1-cluster` repository (GitHub)
- All nodes share the same `requirements.txt` and `.env` structure
- `NATS_SERVERS` and `NATS_TOKEN` are the only required config — **no hardcoded addresses or tokens in code**
- NATS topics are the universal API between all components

### 1.2. Server Roles

```
┌─────────────────────────────────────────────────────────────────┐
│                        H1 Cluster                               │
│                                                                 │
│  ┌──────────────────────────┐  ┌──────────────────────────┐    │
│  │       Heavy-1            │  │       Heavy-2            │    │
│  │   192.168.99.11          │  │   192.168.99.12          │    │
│  │                          │  │                          │    │
│  │  nats-server :4222/:8222 │  │  nats-server :4222/:8222 │    │
│  │  orchestrator.py         │  │  security_monitor.py     │    │
│  │    ← intents.mcp         │  │    ← h1.system.events    │    │
│  │  security_monitor.py     │  │                          │    │
│  │    ← h1.system.events    │  │  [DATADIR backup]        │    │
│  │  mcp_hh_expert_bridge.py │  │                          │    │
│  │    ← intents.hh_expert   │  └──────────────────────────┘    │
│  │  hh_expert/server.py     │                                   │
│  │  DATADIR (master)        │                                   │
│  └──────────────────────────┘                                   │
│                                                                 │
│  ┌──────────────────────────┐  ┌──────────────────────────┐    │
│  │       Light-1            │  │       Light-2            │    │
│  │   192.168.99.13          │  │   192.168.99.14          │    │
│  │                          │  │                          │    │
│  │  worker_playwright.py    │  │  worker_playwright.py    │    │
│  │    ← tasks.hhparse       │  │    ← tasks.hhparse       │    │
│  └──────────────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3. Component Responsibilities

| Server | IP | Components | NATS Topics |
|--------|----|------------|-------------|
| Heavy-1 | 192.168.99.11 | NATS broker 1, Orchestrator, Security Monitor, MCP Bridge, hh_expert DATADIR (master) | `intents.mcp`, `h1.system.events`, `intents.hh_expert` |
| Heavy-2 | 192.168.99.12 | NATS broker 2, Security Monitor (backup) | `h1.system.events` |
| Light-1 | 192.168.99.13 | Playwright Worker | `tasks.hhparse` |
| Light-2 | 192.168.99.14 | Playwright Worker | `tasks.hhparse` |

### 1.4. NATS Topics Reference

| Topic | Direction | Description |
|-------|-----------|-------------|
| `intents.mcp` | Client → Orchestrator | General intent routing |
| `intents.responses` | Orchestrator → Client | Intent responses |
| `h1.system.events` | Any → SecurityMonitor | System events, audit log |
| `tasks.hhparse` | Orchestrator → Workers | Browser automation tasks |
| `tasks.results` | Workers → Orchestrator | Task execution results |
| `intents.hh_expert` | Client → MCP Bridge | hh_expert tool calls |
| `intents.hh_expert.responses` | MCP Bridge → Client | hh_expert results (fallback) |

### 1.5. Agent Registry

The file `h1_server/config/agent_registry.json` serves as the **single map** of which agents run where:

```json
{
  "heavy-1": {
    "ip": "192.168.99.11",
    "agents": ["nats-server", "orchestrator", "security_monitor", "mcp_hh_expert_bridge"],
    "datadir": "C:\\H1_Server\\hh_expert_datadir"
  },
  "heavy-2": {
    "ip": "192.168.99.12",
    "agents": ["nats-server", "security_monitor"]
  },
  "light-1": {
    "ip": "192.168.99.13",
    "agents": ["worker_playwright"]
  },
  "light-2": {
    "ip": "192.168.99.14",
    "agents": ["worker_playwright"]
  }
}
```

---

## 2. Network and Cluster Health Checklist

Before any deployment or debugging, verify the cluster is healthy from your laptop.

### 2.1. VPN Connection

```cmd
:: Connect SSTP VPN
rasdial "H1-Kulakova" VPN_LOGIN VPN_PASSWORD

:: Verify route to cluster subnet
route print 192.168.99.*

:: Expected: route via H1-Kulakova interface
:: 192.168.99.0    255.255.255.0    On-link    192.168.100.251
```

### 2.2. NATS Availability

```cmd
:: Check NATS port (TCP)
powershell -Command "Test-NetConnection 192.168.99.11 -Port 4222"
powershell -Command "Test-NetConnection 192.168.99.12 -Port 4222"

:: Check NATS health (HTTP monitoring)
curl http://192.168.99.11:8222/healthz
curl http://192.168.99.12:8222/healthz
:: Expected: {"status": "ok"}

:: Check active connections and subscriptions
curl http://192.168.99.11:8222/connz?subs=1
:: Expected: connections with intents.mcp, h1.system.events, tasks.hhparse
```

### 2.3. End-to-End Tests (Python)

All tests require `.env` with `NATS_SERVERS` and `NATS_TOKEN`:

```cmd
cd c:\h1_network\workspace\h1-repo\tests
```

**Test 1: Orchestrator Request/Reply**
```cmd
python test_orchestrator_reply.py
```
Expected: `[+] SUCCESS! Received reply from Orchestrator: {"status": "accepted", ...}`

**Test 2: Heavy → Light Worker Task**
```cmd
python test_worker_task.py
```
Expected:
```
[+] Test 1 PASS: Worker processed task and sent result
    Processed by: LIGHT-1
[+] Test 2 PASS: Worker replied!
```

**Test 3: hh_expert MCP Bridge**
```cmd
python test_hh_expert_bridge.py
```
Expected:
```
[PASS] list_tools: N tools
[PASS] get_vacancy_status: ok
[PASS] create_vacancy: ok
[PASS] error_handling: ok
```

### 2.4. Quick Status Check Script

```python
# Quick cluster status (run from laptop with VPN)
import socket, json

def check(host, port, path="/healthz"):
    s = socket.socket(); s.settimeout(3)
    try:
        s.connect((host, port))
        s.sendall(f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            data += chunk
        body = data.decode().split("\r\n\r\n", 1)[1]
        return json.loads(body)
    except Exception as e:
        return {"error": str(e)}
    finally:
        s.close()

for name, host in [("Heavy-1", "192.168.99.11"), ("Heavy-2", "192.168.99.12")]:
    h = check(host, 8222, "/healthz")
    v = check(host, 8222, "/varz")
    c = check(host, 8222, "/connz?subs=1")
    conns = c.get("num_connections", "?")
    uptime = v.get("uptime", "?")
    print(f"{name}: status={h.get('status')} uptime={uptime} connections={conns}")
```

---

## 3. hh_expert Migration to Heavy-1 and Cherry Studio Integration

### Step 1: Prepare Heavy-1

**1.1. Clone hh_expert repository on Heavy-1**

Via RDP to Heavy-1 (192.168.99.11):
```cmd
cd C:\
git clone https://github.com/YOUR_ORG/hh_expert.git C:\hh_expert
```

**1.2. Create DATADIR**
```cmd
mkdir C:\H1_Server\hh_expert_datadir
```

**1.3. Install hh_expert dependencies**
```cmd
cd C:\hh_expert
pip install -r requirements.txt
```

**1.4. Configure `.env` on Heavy-1**

Add to `C:\H1_Server\.env`:
```env
HH_EXPERT_PY=C:\hh_expert\server.py
HH_EXPERT_PYTHON=C:\Python\python.exe
HH_EXPERT_WORKDIR=C:\hh_expert
```

### Step 2: Migrate Data

**One-time copy of local DATADIR from developer laptop to Heavy-1:**

```cmd
:: From developer laptop (with VPN connected):
:: Option A — via RDP file transfer (drag & drop)
:: Option B — via network share (if available)
:: Option C — via git (if DATADIR is versioned)

:: After copy, verify on Heavy-1:
dir C:\H1_Server\hh_expert_datadir
```

Set `DATADIR` in hh_expert config to point to `C:\H1_Server\hh_expert_datadir`.

### Step 3: Start MCP Bridge

**3.1. Install H1_HH_Expert_Bridge scheduled task on Heavy-1:**

```cmd
schtasks /create /tn "H1_HH_Expert_Bridge" ^
  /tr "C:\Python\python.exe C:\H1_Server\mcp_hh_expert_bridge.py" ^
  /sc onstart /ru SYSTEM /f

schtasks /run /tn "H1_HH_Expert_Bridge"
```

**3.2. Verify bridge is running:**

```cmd
:: Check NATS subscription
curl http://192.168.99.11:8222/connz?subs=1
:: Expected: connection with subs=['intents.hh_expert']

:: Run integration test from laptop
python tests/test_hh_expert_bridge.py
```

### Step 4: HTTP/MCP Gateway for Cherry Studio

Create `h1_server/h1_mcp_gateway.py` — a lightweight FastAPI/SSE server on Heavy-1 that:
- Listens on HTTP (e.g., port 8333)
- Proxies MCP protocol requests to NATS `intents.hh_expert`
- Returns responses via SSE (Server-Sent Events) for Cherry Studio compatibility

**Architecture:**
```
Cherry Studio (laptop)
    │
    │ HTTP/SSE  :8333
    ▼
h1_mcp_gateway.py (Heavy-1)
    │
    │ NATS intents.hh_expert
    ▼
mcp_hh_expert_bridge.py (Heavy-1)
    │
    │ stdio
    ▼
hh_expert/server.py (Heavy-1)
```

**Minimal gateway skeleton:**
```python
# h1_mcp_gateway.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio, json, nats

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(request: dict):
    nc = await nats.connect(servers=NATS_SERVERS, token=NATS_TOKEN)
    msg = await nc.request(
        "intents.hh_expert",
        json.dumps(request).encode(),
        timeout=30.0
    )
    await nc.drain()
    return json.loads(msg.data)

# Run: uvicorn h1_mcp_gateway:app --host 0.0.0.0 --port 8333
```

### Step 5: Connect Cherry Studio

**5.1. In Cherry Studio on developer laptop:**

1. Open Settings → MCP Servers
2. Add new server:
   - **Type:** Web / SSE (or HTTP)
   - **URL:** `http://192.168.99.11:8333/mcp`
   - **Name:** `H1 hh_expert`
3. Click "Connect" / "Refresh tools"

**5.2. Verify tools appear:**

Cherry Studio should show hh_expert tools:
- `create_vacancy`
- `get_vacancy_status`
- `run_pipeline`
- `get_report`
- ... (all tools from hh_expert/server.py)

**5.3. Test a tool call from Cherry:**

In Cherry Studio chat, invoke a tool:
```
Use hh_expert to get status of vacancy VAC-001
```

Expected: Cherry calls `get_vacancy_status` via MCP → Gateway → NATS → Bridge → hh_expert → response back to Cherry.

---

## 4. Deployment Checklist Summary

| Step | Action | Verify |
|------|--------|--------|
| 1 | Connect VPN H1-Kulakova | `route print 192.168.99.*` |
| 2 | Check NATS health | `curl http://192.168.99.11:8222/healthz` |
| 3 | Run orchestrator test | `python test_orchestrator_reply.py` → PASS |
| 4 | Run worker test | `python test_worker_task.py` → PASS |
| 5 | Clone hh_expert on Heavy-1 | `dir C:\hh_expert` |
| 6 | Migrate DATADIR | `dir C:\H1_Server\hh_expert_datadir` |
| 7 | Start MCP bridge | `schtasks /query /tn "H1_HH_Expert_Bridge"` |
| 8 | Run bridge test | `python test_hh_expert_bridge.py` → PASS |
| 9 | Start HTTP gateway | `curl http://192.168.99.11:8333/health` |
| 10 | Connect Cherry Studio | Tools visible in Cherry UI |

---

## 5. File Structure Reference

```
h1-cluster/
├── h1_server/                      # Heavy server components
│   ├── orchestrator.py             # Intent router (intents.mcp)
│   ├── security_monitor.py         # Event logger (h1.system.events)
│   ├── mcp_hh_expert_bridge.py     # NATS ↔ MCP hh_expert bridge
│   ├── h1_mcp_gateway.py           # HTTP/SSE gateway for Cherry [TODO]
│   ├── nats-server.conf            # NATS config template
│   ├── requirements.txt
│   ├── install_service.bat
│   ├── .env.example
│   └── config/
│       └── agent_registry.json     # Agent-to-server mapping
│
├── h1_light_worker/                # Light worker components
│   ├── worker_playwright.py        # Playwright task executor
│   ├── requirements.txt
│   ├── install_dependencies.bat
│   ├── install_service.bat
│   └── .env.example
│
├── tests/
│   ├── test_publisher.py           # Basic NATS connectivity
│   ├── test_orchestrator_reply.py  # Orchestrator Request/Reply
│   ├── test_worker_task.py         # Heavy → Light worker
│   └── test_hh_expert_bridge.py    # MCP hh_expert bridge
│
└── docs/
    ├── ARCHITECTURE_ONE_HEAVY.md
    ├── INSTALL_HEAVY.md
    ├── INSTALL_LIGHT.md
    ├── VPN_AND_ACCESS.md
    ├── TESTS.md
    └── H1_ARCHITECTURE_AND_DEPLOYMENT.md  ← this file
```
