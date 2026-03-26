# H1 Heavy Server — Installation Guide

> **Ключевой принцип:** `NATS_SERVERS` и `NATS_TOKEN` берутся **только из `.env`** — ничего не нужно менять в коде (`orchestrator.py`, `security_monitor.py`) при установке на новых серверах. Заполни `.env` по шаблону `.env.example` — и всё готово.

## Requirements

- **OS**: Windows 10/11 or Windows Server 2019+
- **Python**: 3.10+ (install to `C:\Python\`)
- **Network**: Static IP in the target subnet
- **Ports**: 4222 (NATS), 8222 (NATS monitoring) — open in firewall
- **RAM**: 4 GB minimum
- **Disk**: 10 GB free

## Step 1: Prepare the server

1. Create directory `C:\H1_Server\`
2. Copy all files from `h1_server/` to `C:\H1_Server\`
3. Download NATS server binary:
   - Get `nats-server.exe` from https://github.com/nats-io/nats-server/releases
   - Place it in `C:\H1_Server\nats-server.exe`

## Step 2: Configure environment

1. Copy `.env.example` to `.env`:
   ```cmd
   copy C:\H1_Server\.env.example C:\H1_Server\.env
   ```

2. Edit `C:\H1_Server\.env`:
   ```env
   NATS_SERVERS=nats://127.0.0.1:4222
   NATS_TOKEN=your_strong_random_token
   LOG_LEVEL=INFO
   ```

3. Edit `C:\H1_Server\nats-server.conf` — set the same token:
   ```
   authorization {
     token: "your_strong_random_token"
   }
   ```

## Step 3: Install services

Run as Administrator:
```cmd
cd C:\H1_Server
install_service.bat
```

This creates 3 scheduled tasks:
- `H1_NATS` — NATS server
- `H1_Orchestrator` — Intent router
- `H1_SecurityMonitor` — Event logger

## Step 4: Verify installation

```cmd
:: Check task status
schtasks /query /tn "H1_NATS"
schtasks /query /tn "H1_Orchestrator"
schtasks /query /tn "H1_SecurityMonitor"

:: Check NATS is running
curl http://localhost:8222/healthz

:: Check logs
type C:\H1_Server\logs\nats.log
```

Expected output from `/healthz`:
```json
{"status": "ok"}
```

## Step 5: Check NATS connections

```cmd
curl http://localhost:8222/connz?subs=1
```

Should show 2 connections:
- `security_monitor.py` subscribed to `h1.system.events`
- `orchestrator.py` subscribed to `intents.mcp`

## Troubleshooting

| Problem | Solution |
|---------|----------|
| NATS won't start | Check `nats.log`, verify port 4222 is free |
| Orchestrator auth error | Verify `NATS_TOKEN` matches in `.env` and `nats-server.conf` |
| No connections in `/connz` | Check Python path, run scripts manually to see errors |
| Port 4222 blocked | Add firewall rule: `netsh advfirewall firewall add rule name="NATS" dir=in action=allow protocol=TCP localport=4222` |
