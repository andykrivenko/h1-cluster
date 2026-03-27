"""
H1 MCP hh_expert Bridge
========================
Connects H1 NATS cluster to the local hh_expert MCP server (stdio).

Listens on NATS topic: intents.hh_expert
Supports message types:
  - list_tools  → calls MCP list_tools, returns tools list
  - call_tool   → calls MCP tool, returns result

All config from .env — no hardcoded addresses or tokens.

Usage:
    python mcp_hh_expert_bridge.py

.env variables:
    NATS_SERVERS=nats://192.168.XX.11:4222,nats://192.168.XX.12:4222
    NATS_TOKEN=your_secret_token_here
    HH_EXPERT_PY=C:\\path\\to\\hh_expert\\server.py
    HH_EXPERT_PYTHON=python
    HH_EXPERT_WORKDIR=C:\\path\\to\\hh_expert
"""

import asyncio
import json
import logging
import os
import queue
import subprocess
import sys
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
import nats

# ─── Configuration ────────────────────────────────────────────────────────────

load_dotenv()

NATS_SERVERS_STR = os.getenv("NATS_SERVERS", "nats://127.0.0.1:4222")
NATS_SERVERS = [s.strip() for s in NATS_SERVERS_STR.split(",")]
NATS_TOKEN = os.getenv("NATS_TOKEN", "")

HH_EXPERT_PY = os.getenv("HH_EXPERT_PY", "server.py")
HH_EXPERT_PYTHON = os.getenv("HH_EXPERT_PYTHON", "python")
HH_EXPERT_WORKDIR = os.getenv("HH_EXPERT_WORKDIR", ".")

LISTEN_TOPIC = "intents.hh_expert"
RESPONSE_TOPIC = "intents.hh_expert.responses"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── Logging ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp_bridge")


# ─── MCP Client (stdio) ───────────────────────────────────────────────────────

class MCPClient:
    """
    Manages a subprocess running hh_expert/server.py via stdio.
    Sends JSON lines, receives JSON lines.
    """

    def __init__(self, cmd: list, cwd: str):
        logger.info(f"Starting MCP process: {' '.join(cmd)} (cwd={cwd})")
        self.proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1
        )
        self._out_queue: queue.Queue = queue.Queue()
        self._err_queue: queue.Queue = queue.Queue()

        self._stdout_thread = threading.Thread(
            target=self._read_stdout, daemon=True, name="mcp-stdout"
        )
        self._stderr_thread = threading.Thread(
            target=self._read_stderr, daemon=True, name="mcp-stderr"
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        logger.info(f"MCP process started (PID={self.proc.pid})")

    def _read_stdout(self):
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if line:
                    self._out_queue.put(line)
        except Exception as e:
            logger.error(f"MCP stdout reader error: {e}")

    def _read_stderr(self):
        try:
            for line in self.proc.stderr:
                line = line.strip()
                if line:
                    logger.debug(f"[MCP stderr] {line}")
                    self._err_queue.put(line)
        except Exception as e:
            logger.error(f"MCP stderr reader error: {e}")

    def send(self, payload: dict) -> None:
        """Send a JSON message to MCP server stdin."""
        data = json.dumps(payload, ensure_ascii=False)
        logger.debug(f"MCP → {data[:200]}")
        self.proc.stdin.write(data + "\n")
        self.proc.stdin.flush()

    def recv(self, timeout: float = 10.0) -> dict:
        """Receive a JSON response from MCP server stdout."""
        try:
            line = self._out_queue.get(timeout=timeout)
            logger.debug(f"MCP ← {line[:200]}")
            return json.loads(line)
        except queue.Empty:
            raise TimeoutError(f"MCP server did not respond within {timeout}s")
        except json.JSONDecodeError as e:
            raise ValueError(f"MCP server returned invalid JSON: {e}")

    def is_alive(self) -> bool:
        return self.proc.poll() is None

    def terminate(self):
        if self.is_alive():
            self.proc.terminate()
            logger.info("MCP process terminated")


# ─── Bridge Logic ─────────────────────────────────────────────────────────────

class HHExpertBridge:
    def __init__(self):
        self.mcp: MCPClient | None = None
        self.nc = None
        self._lock = asyncio.Lock()

    def _start_mcp(self):
        cmd = [HH_EXPERT_PYTHON, HH_EXPERT_PY]
        self.mcp = MCPClient(cmd=cmd, cwd=HH_EXPERT_WORKDIR)

    def _ensure_mcp(self):
        """Restart MCP process if it died."""
        if self.mcp is None or not self.mcp.is_alive():
            logger.warning("MCP process not running, restarting...")
            self._start_mcp()

    async def handle_message(self, msg):
        """Handle incoming NATS message."""
        reply_subject = msg.reply or RESPONSE_TOPIC

        try:
            data = json.loads(msg.data.decode("utf-8"))
        except Exception as e:
            logger.error(f"Failed to parse message: {e}")
            await self._send_error(reply_subject, "parse_error", str(e))
            return

        msg_type = data.get("type", "unknown")
        user = data.get("user", "unknown")
        client = data.get("client", "unknown")
        logger.info(f"[{msg_type}] from user={user} client={client}")

        async with self._lock:
            try:
                self._ensure_mcp()

                if msg_type == "list_tools":
                    await self._handle_list_tools(reply_subject, data)

                elif msg_type == "call_tool":
                    await self._handle_call_tool(reply_subject, data)

                else:
                    logger.warning(f"Unknown message type: {msg_type}")
                    await self._send_error(
                        reply_subject, "unknown_type",
                        f"Unknown message type: {msg_type}"
                    )

            except TimeoutError as e:
                logger.error(f"MCP timeout: {e}")
                await self._send_error(reply_subject, "timeout", str(e))
            except Exception as e:
                logger.error(f"Bridge error: {e}", exc_info=True)
                await self._send_error(reply_subject, "bridge_error", str(e))

    async def _handle_list_tools(self, reply_subject: str, data: dict):
        """Handle list_tools request."""
        self.mcp.send({"type": "list_tools"})
        resp = self.mcp.recv(timeout=10.0)

        out = {
            "type": "list_tools_result",
            "tools": resp.get("tools", []),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.nc.publish(
            reply_subject,
            json.dumps(out, ensure_ascii=False).encode("utf-8")
        )
        logger.info(f"list_tools: returned {len(out['tools'])} tools")

    async def _handle_call_tool(self, reply_subject: str, data: dict):
        """Handle call_tool request."""
        tool_name = data.get("tool_name")
        arguments = data.get("arguments", {})
        user = data.get("user", "unknown")

        if not tool_name:
            await self._send_error(reply_subject, "missing_tool_name", "tool_name is required")
            return

        logger.info(f"call_tool: {tool_name} args={json.dumps(arguments)[:100]}")

        self.mcp.send({
            "type": "call_tool",
            "tool_name": tool_name,
            "arguments": arguments,
            "user": user
        })
        resp = self.mcp.recv(timeout=30.0)

        out = {
            "type": "call_tool_result",
            "tool_name": tool_name,
            "ok": resp.get("ok", True),
            "result": resp.get("result"),
            "error": resp.get("error"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self.nc.publish(
            reply_subject,
            json.dumps(out, ensure_ascii=False).encode("utf-8")
        )
        status = "ok" if out["ok"] else f"error: {out['error']}"
        logger.info(f"call_tool {tool_name}: {status}")

    async def _send_error(self, reply_subject: str, error_type: str, message: str):
        """Send error response."""
        out = {
            "type": "error",
            "error_type": error_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        try:
            await self.nc.publish(
                reply_subject,
                json.dumps(out, ensure_ascii=False).encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Failed to send error response: {e}")

    async def run(self):
        """Main bridge loop."""
        logger.info("=" * 60)
        logger.info("H1 MCP hh_expert Bridge starting...")
        logger.info(f"NATS servers: {NATS_SERVERS}")
        logger.info(f"Listen topic: {LISTEN_TOPIC}")
        logger.info(f"MCP command: {HH_EXPERT_PYTHON} {HH_EXPERT_PY}")
        logger.info(f"MCP workdir: {HH_EXPERT_WORKDIR}")
        logger.info("=" * 60)

        # Start MCP process
        self._start_mcp()

        # Connect to NATS
        options = {
            "servers": NATS_SERVERS,
            "connect_timeout": 10,
            "name": "H1-MCP-hh_expert-Bridge"
        }
        if NATS_TOKEN:
            options["token"] = NATS_TOKEN

        self.nc = await nats.connect(**options)
        logger.info(f"Connected to NATS: {self.nc.connected_url.netloc}")

        # Subscribe
        sub = await self.nc.subscribe(LISTEN_TOPIC, cb=self.handle_message)
        logger.info(f"Subscribed to '{LISTEN_TOPIC}'. Ready.")

        # Keep alive
        try:
            while True:
                await asyncio.sleep(5)
                # Health check: restart MCP if died
                if not self.mcp.is_alive():
                    logger.warning("MCP process died, restarting...")
                    self._start_mcp()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await sub.unsubscribe()
            if self.mcp:
                self.mcp.terminate()
            await self.nc.drain()
            logger.info("Bridge stopped.")


# ─── Entry Point ──────────────────────────────────────────────────────────────

async def main():
    bridge = HHExpertBridge()
    await bridge.run()


if __name__ == "__main__":
    asyncio.run(main())
