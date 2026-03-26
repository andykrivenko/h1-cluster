# H1 Light Worker — Installation Guide

## Requirements

- **OS**: Windows 10/11
- **Python**: 3.10+ (install to `C:\Python\`)
- **Network**: Access to Heavy server(s) on port 4222
- **RAM**: 4 GB minimum (Playwright needs memory)

## Step 1: Prepare the worker

1. Create directory `C:\H1_Node\`
2. Copy all files from `h1_light_worker/` to `C:\H1_Node\`

## Step 2: Configure environment

1. Copy `.env.example` to `.env`:
   ```cmd
   copy C:\H1_Node\.env.example C:\H1_Node\.env
   ```

2. Edit `C:\H1_Node\.env`:
   ```env
   NATS_SERVERS=nats://192.168.XX.11:4222,nats://192.168.XX.12:4222
   NATS_TOKEN=your_secret_token_here
   WORKER_ID=light-worker-1
   LOG_LEVEL=INFO
   LOG_FILE=C:\H1_Node\logs\worker.log
   ```

## Step 3: Install dependencies

Run as Administrator:
```cmd
cd C:\H1_Node
install_dependencies.bat
```

This installs:
- Python packages (`nats-py`, `playwright`, etc.)
- Playwright Chromium browser

## Step 4: Install service

Run as Administrator:
```cmd
cd C:\H1_Node
install_service.bat
```

Creates scheduled task `H1_Worker` that starts on boot.

## Step 5: Verify installation

```cmd
:: Check task status
schtasks /query /tn "H1_Worker"

:: Check worker log
type C:\H1_Node\logs\worker.log
```

Expected in log:
```
[INFO] H1 Light Worker 'light-worker-1' starting...
[INFO] Connected to NATS: 192.168.XX.11:4222
[INFO] Subscribed to 'tasks.hhparse'. Ready for tasks...
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cannot connect to NATS | Check VPN/network, verify Heavy server IP and port 4222 |
| Auth error | Verify `NATS_TOKEN` matches Heavy server config |
| Playwright not found | Run `install_dependencies.bat` again |
| Worker crashes | Check `worker.log` for Python errors |
