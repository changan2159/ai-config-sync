from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import threading
import time
from pathlib import Path

import httpx
import psutil
from filelock import FileLock

from serena_manager.config import ManagerConfig
from serena_manager.mcp_health import open_streamable_http_session
from serena_manager.state_store import ProjectState, StateStore


class StartupBlockedError(RuntimeError):
    """Raised when failure backoff prevents an immediate restart."""


class SerenaManager:
    def __init__(self, config: ManagerConfig) -> None:
        self.config = config
        self.store = StateStore(config.state_root)

    def ensure_instance(self, project_root: Path) -> ProjectState:
        project_root = project_root.resolve()
        self.store.ensure_project_dir(project_root)
        lock = FileLock(str(self.store.lock_path(project_root)))
        with lock:
            existing = self.store.load(project_root)
            if existing and self._state_matches_config(existing) and self.is_healthy(existing):
                self._log(project_root, f"reusing pid={existing.pid} endpoint={existing.endpoint_url}")
                return self.store.touch_activity(existing)

            if existing and self._is_in_failure_backoff(existing):
                self._log(project_root, f"startup blocked by backoff failure_count={existing.failure_count}")
                raise StartupBlockedError(existing.last_error or "Recent startup failures are backing off restarts")

            if existing:
                if not self._state_matches_config(existing):
                    self._log(
                        project_root,
                        "terminating stale "
                        f"pid={existing.pid} status={existing.status} "
                        f"context={existing.serena_context} expected={self.config.context}",
                    )
                else:
                    self._log(project_root, f"terminating stale pid={existing.pid} status={existing.status}")
                self._terminate_state(existing, delete_state=False)

            return self._start_instance(project_root, existing)

    def status(self) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        now = time.time()
        for state in self.store.list_states():
            result.append(
                {
                    "project_root": state.project_root,
                    "pid": state.pid,
                    "endpoint_url": state.endpoint_url,
                    "serena_context": state.serena_context,
                    "status": state.status,
                    "healthy": self.is_healthy(state),
                    "idle_seconds": max(0.0, now - state.last_active_at),
                }
            )
        return result

    def stop(self, project_root: Path) -> bool:
        state = self.store.load(project_root.resolve())
        if state is None:
            return False
        self._log(project_root.resolve(), f"stopping pid={state.pid}")
        self._terminate_state(state, delete_state=True)
        return True

    def cleanup(self) -> list[str]:
        removed: list[str] = []
        for state in self.store.list_states():
            root = Path(state.project_root)
            if not self.is_healthy(state):
                self._log(root, f"cleanup removing unhealthy pid={state.pid} status={state.status}")
                self._terminate_state(state, delete_state=True)
                removed.append(str(root))
        return removed

    def reap_idle(self) -> list[str]:
        removed: list[str] = []
        now = time.time()
        for state in self.store.list_states():
            if now - state.last_active_at >= self.config.idle_timeout_seconds:
                self._log(Path(state.project_root), f"reaping idle pid={state.pid}")
                self._terminate_state(state, delete_state=True)
                removed.append(state.project_root)
        return removed

    def doctor(self, project_root: Path | None = None) -> list[dict[str, object]]:
        states = [self.store.load(project_root.resolve())] if project_root else self.store.list_states()
        report: list[dict[str, object]] = []
        for state in states:
            if state is None:
                continue
            report.append(
                {
                    "project_root": state.project_root,
                    "pid_alive": self._pid_alive(state.pid),
                    "http_alive": self._http_alive(state.endpoint_url),
                    "mcp_alive": self._mcp_alive(state.endpoint_url),
                    "serena_context": state.serena_context,
                    "status": state.status,
                    "last_error": state.last_error,
                }
            )
        return report

    def is_healthy(self, state: ProjectState) -> bool:
        return self._pid_alive(state.pid) and self._http_alive(state.endpoint_url) and self._mcp_alive(state.endpoint_url)

    def _is_in_failure_backoff(self, state: ProjectState) -> bool:
        if state.failure_count <= 0:
            return False
        return time.time() - state.last_active_at < self.config.failure_backoff_seconds

    def _state_matches_config(self, state: ProjectState) -> bool:
        return state.serena_context == self.config.context

    def _start_instance(self, project_root: Path, previous: ProjectState | None) -> ProjectState:
        port = self._find_free_port()
        endpoint_url = f"http://{self.config.host}:{port}/mcp"
        now = time.time()
        project_hash = self.store.project_hash(project_root)
        failure_count = previous.failure_count if previous else 0

        state = ProjectState(
            project_root=str(project_root),
            project_hash=project_hash,
            transport="streamable-http",
            endpoint_url=endpoint_url,
            serena_context=self.config.context,
            pid=0,
            started_at=now,
            last_active_at=now,
            status="starting",
            failure_count=failure_count,
            last_error=previous.last_error if previous else "",
        )
        self.store.save(state)

        stdout_path = self.store.stdout_log_path(project_root)
        stderr_path = self.store.stderr_log_path(project_root)
        command = [
            self.config.serena_command,
            *self.config.serena_args,
            "--transport",
            "streamable-http",
            "--project",
            str(project_root),
            "--context",
            self.config.context,
            "--host",
            self.config.host,
            "--port",
            str(port),
            "--enable-web-dashboard",
            "false",
            "--open-web-dashboard",
            "false",
            "--enable-gui-log-window",
            "false",
        ]

        with stdout_path.open("ab") as stdout_handle, stderr_path.open("ab") as stderr_handle:
            process = subprocess.Popen(  # noqa: S603
                command,
                cwd=str(project_root),
                stdin=subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )

        state.pid = process.pid
        self.store.save(state)
        self._log(project_root, f"started pid={process.pid} endpoint={endpoint_url}")

        deadline = time.time() + self.config.startup_timeout_seconds
        while time.time() < deadline:
            if self.is_healthy(state):
                state.status = "running"
                state.failure_count = 0
                state.last_error = ""
                self.store.touch_activity(state)
                self._log(project_root, f"healthy pid={process.pid} endpoint={endpoint_url}")
                return state
            if process.poll() is not None:
                break
            time.sleep(0.5)

        state.status = "error"
        state.failure_count += 1
        state.last_error = f"Failed to start Serena daemon for {project_root}"
        state.last_active_at = time.time()
        self.store.save(state)
        self._log(project_root, state.last_error)
        self._terminate_state(state, delete_state=False)
        raise RuntimeError(state.last_error)

    def _pid_alive(self, pid: int) -> bool:
        return pid > 0 and psutil.pid_exists(pid)

    def _http_alive(self, endpoint_url: str) -> bool:
        try:
            response = httpx.get(endpoint_url, timeout=self.config.healthcheck_timeout_seconds)
            return response.status_code in {200, 400, 405, 406}
        except Exception:
            return False

    def _mcp_alive(self, endpoint_url: str) -> bool:
        try:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(self._ping_mcp(endpoint_url))
            else:
                result: dict[str, bool] = {"ok": False}
                error: list[BaseException] = []

                def runner() -> None:
                    try:
                        asyncio.run(self._ping_mcp(endpoint_url))
                        result["ok"] = True
                    except BaseException as exc:  # noqa: BLE001
                        error.append(exc)

                thread = threading.Thread(target=runner, daemon=True)
                thread.start()
                thread.join(timeout=self.config.healthcheck_timeout_seconds)
                if thread.is_alive():
                    return False
                if error:
                    raise error[0]
            return True
        except Exception:
            return False

    async def _ping_mcp(self, endpoint_url: str) -> None:
        async with open_streamable_http_session(endpoint_url) as session:
            await session.send_ping()

    def _terminate_state(self, state: ProjectState, delete_state: bool) -> None:
        if state.pid > 0 and psutil.pid_exists(state.pid):
            try:
                proc = psutil.Process(state.pid)
                children = proc.children(recursive=True)
                for child in children:
                    child.terminate()
                proc.terminate()
                _, alive = psutil.wait_procs([*children, proc], timeout=5)
                for survivor in alive:
                    survivor.kill()
            except psutil.Error:
                pass
        if delete_state:
            self.store.delete(Path(state.project_root))

    def _log(self, project_root: Path, message: str) -> None:
        log_path = self.store.manager_log_path(project_root)
        self.store.ensure_project_dir(project_root)
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} {message}\n")

    def _find_free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.config.host, 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            return int(sock.getsockname()[1])
