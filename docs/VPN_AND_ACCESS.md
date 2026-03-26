# VPN and Network Access

## Overview

H1 servers are located in a private subnet (e.g., `192.168.99.0/24`).  
To access them from a client machine, a VPN with split-tunneling is required.

## VPN Setup (Windows — SSTP)

The admin provides a `VPN.cmd` script. Run it once to create the VPN profile:

```cmd
VPN.cmd
```

This creates a VPN connection named `H1-<ClientName>` with:
- Server: `H1-host-<domain>.example.com`
- Protocol: SSTP (SSL/TLS, port 443)
- Split-tunnel route: `192.168.99.0/24` only

### Connect manually

```cmd
rasdial "H1-<ClientName>" VPN_LOGIN VPN_PASSWORD
```

### Disconnect

```cmd
rasdial "H1-<ClientName>" /disconnect
```

### Check connection

```cmd
rasdial
ipconfig | findstr 192.168.99
route print 192.168.99.*
```

## VPN Setup (macOS/Linux — OpenVPN)

The admin provides an `.ovpn` profile file.

1. Install OpenVPN Connect: https://openvpn.net/client/
2. Import the `.ovpn` file
3. Connect using VPN credentials

## Network Topology

```
Client machine (192.168.1.x or any)
    |
    | SSTP/OpenVPN tunnel
    |
VPN Gateway (public IP)
    |
    | Internal routing
    |
Heavy-1: 192.168.99.11  (NATS :4222, monitoring :8222)
Heavy-2: 192.168.99.12  (NATS :4222, monitoring :8222)
Light-1: 192.168.99.13  (worker)
Light-2: 192.168.99.14  (worker)
```

## Required from Admin

To set up VPN access, the admin needs to provide:
- VPN server hostname/IP
- VPN credentials (login + password)
- Target subnet (e.g., `192.168.99.0/24`)
- VPN profile file (`.ovpn` for OpenVPN or `VPN.cmd` for SSTP)

## Firewall Requirements

On Heavy servers, the following ports must be accessible from VPN clients:

| Port | Protocol | Service |
|------|----------|---------|
| 4222 | TCP | NATS clients |
| 8222 | TCP | NATS HTTP monitoring |
| 3389 | TCP | RDP (admin access) |

## Verify Connectivity

After VPN connection:

```cmd
:: Ping Heavy servers
ping 192.168.99.11
ping 192.168.99.12

:: Check NATS port
powershell -Command "Test-NetConnection 192.168.99.11 -Port 4222"

:: Check NATS monitoring
curl http://192.168.99.11:8222/healthz
```
