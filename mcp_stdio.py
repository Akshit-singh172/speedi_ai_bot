from __future__ import annotations

from dotenv import load_dotenv
from pathlib import Path
import json
import os
import queue
import shutil
import subprocess
import threading
from typing import Any

load_dotenv()


def _resolve_command(command: str) -> str:
    value = (command or "").strip()
    if not value:
        return value

    # Explicit path provided
    if any(sep in value for sep in ("\\", "/")):
        return value

    found = shutil.which(value)
    if found:
        # On Windows, prefer the `.cmd` shim when both exist.
        if os.name == "nt":
            p = Path(found)
            if p.suffix == "":
                cmd_variant = p.with_suffix(".cmd")
                if cmd_variant.exists():
                    return str(cmd_variant)
        return found

    if os.name != "nt":
        return value

    base_names = [value, f"{value}.cmd", f"{value}.exe", f"{value}.bat"]
    dirs: list[Path] = []

    appdata = os.getenv("APPDATA")
    if appdata:
        dirs.append(Path(appdata) / "npm")
    nvm_symlink = os.getenv("NVM_SYMLINK")
    if nvm_symlink:
        dirs.append(Path(nvm_symlink))
    program_files = os.getenv("ProgramFiles")
    if program_files:
        dirs.append(Path(program_files) / "nodejs")
    program_files_x86 = os.getenv("ProgramFiles(x86)")
    if program_files_x86:
        dirs.append(Path(program_files_x86) / "nodejs")

    for directory in dirs:
        for name in base_names:
            candidate = directory / name
            try:
                if candidate.exists():
                    return str(candidate)
            except PermissionError:
                # If existence can't be checked due to policy, return the candidate path anyway.
                return str(candidate)

    return value


def _parse_args(raw: str) -> list[str]:
    value = (raw or "").strip()
    if not value:
        return []
    if value.startswith("["):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                return parsed
        except json.JSONDecodeError:
            pass
    return value.split()


def _subprocess_env() -> dict[str, str]:
    env = dict(os.environ)
    # ImageGen MCP server expects GOOGLE_API_KEY, but this project uses GEMINI_API_KEY.
    if not env.get("GOOGLE_API_KEY") and env.get("GEMINI_API_KEY"):
        env["GOOGLE_API_KEY"] = env["GEMINI_API_KEY"]
    return env


class McpStdioClient:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._next_id = 1
        self._pending: dict[int, "queue.Queue[dict[str, Any]]"] = {}
        self._pending_lock = threading.Lock()
        self._op_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._initialized = False
        self._reader_thread: threading.Thread | None = None
        self._stderr_thread: threading.Thread | None = None

    def _cmd(self) -> list[str]:
        command = _resolve_command(os.getenv("IMAGEGEN_MCP_COMMAND", "imagegen-mcp-server"))
        args = _parse_args(os.getenv("IMAGEGEN_MCP_ARGS", ""))
        return [command, *args]

    def _start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return

        cmd = self._cmd()
        cwd = os.getenv("IMAGEGEN_MCP_CWD") or None

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=cwd,
                env=_subprocess_env(),
            )
        except FileNotFoundError as e:
            raise Exception(
                f"ImageGen MCP server not found. Tried to run: {cmd}. "
                "Install it (`npm i -g imagegen-mcp-server`) or set IMAGEGEN_MCP_COMMAND/IMAGEGEN_MCP_ARGS."
            ) from e

        self._initialized = False
        self._reader_thread = threading.Thread(target=self._read_stdout_loop, daemon=True)
        self._reader_thread.start()
        self._stderr_thread = threading.Thread(target=self._drain_stderr_loop, daemon=True)
        self._stderr_thread.start()

    def _drain_stderr_loop(self) -> None:
        if not self._proc or not self._proc.stderr:
            return
        try:
            for _ in self._proc.stderr:
                pass
        except Exception:
            return

    def _read_stdout_loop(self) -> None:
        if not self._proc or not self._proc.stdout:
            return
        try:
            for line in self._proc.stdout:
                raw = (line or "").strip()
                if not raw:
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_id = msg.get("id")
                if msg_id is None:
                    continue

                with self._pending_lock:
                    q = self._pending.get(int(msg_id))
                if q:
                    try:
                        q.put_nowait(msg)
                    except Exception:
                        pass
        except Exception:
            return

    def _send(self, payload: dict[str, Any]) -> None:
        if not self._proc or not self._proc.stdin:
            raise Exception("MCP process is not running")
        line = json.dumps(payload, separators=(",", ":"))
        with self._write_lock:
            self._proc.stdin.write(line + "\n")
            self._proc.stdin.flush()

    def _request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._start()

        req_id = self._next_id
        self._next_id += 1

        q: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._pending[req_id] = q

        timeout_s = float(os.getenv("IMAGEGEN_MCP_TIMEOUT_S", "180"))

        try:
            payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params is not None:
                payload["params"] = params
            self._send(payload)

            msg = q.get(timeout=timeout_s)
            if "error" in msg:
                err = msg.get("error") or {}
                raise Exception(err.get("message") or str(err))
            return msg.get("result") or {}
        except queue.Empty as e:
            raise Exception(f"MCP request timed out calling {method}") from e
        finally:
            with self._pending_lock:
                self._pending.pop(req_id, None)

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "speedi-ai-bot", "version": "1.0.0"},
            },
        )
        if not result.get("protocolVersion"):
            raise Exception("MCP initialize failed (no protocolVersion)")
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self._initialized = True

    def list_tools(self) -> list[dict[str, Any]]:
        with self._op_lock:
            self._ensure_initialized()
            result = self._request("tools/list", {})
        tools = result.get("tools") or []
        if isinstance(tools, list):
            return [t for t in tools if isinstance(t, dict)]
        return []

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._op_lock:
            self._ensure_initialized()
            return self._request("tools/call", {"name": name, "arguments": arguments or {}})


_MCP: McpStdioClient | None = None
_MCP_LOCK = threading.Lock()


def mcp_client() -> McpStdioClient:
    global _MCP
    with _MCP_LOCK:
        if _MCP is None:
            _MCP = McpStdioClient()
        return _MCP

