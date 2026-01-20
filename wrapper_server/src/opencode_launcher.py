"""
OpenCode Server Launcher

Automatically starts and manages the OpenCode server process.
Supports auto-start on wrapper server startup.
"""

import asyncio
import os
import shutil
import signal
import socket
import subprocess
from pathlib import Path
from typing import Optional

from loguru import logger


class OpenCodeLauncher:
    """
    Manages the OpenCode server process.

    Can:
    - Detect if OpenCode is installed
    - Start the OpenCode server
    - Check if OpenCode is running
    - Stop the OpenCode server
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 4096,
        password: str = "",
        opencode_path: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.opencode_path = opencode_path or self._find_opencode()
        self._process: Optional[subprocess.Popen] = None
        self._we_started: bool = False

    def _find_opencode(self) -> str:
        """Find the opencode executable path"""
        # Check environment variable first
        env_path = os.environ.get("OPENCODE_PATH")
        if env_path and shutil.which(env_path):
            return env_path

        # Check if opencode is in PATH
        path = shutil.which("opencode")
        if path:
            return path

        # Common installation paths
        common_paths = [
            "/usr/local/bin/opencode",
            "/usr/bin/opencode",
            str(Path.home() / ".local/bin/opencode"),
        ]
        for p in common_paths:
            if Path(p).exists():
                return p

        return "opencode"  # Fall back to PATH lookup

    def is_installed(self) -> bool:
        """Check if OpenCode is installed"""
        return shutil.which(self.opencode_path) is not None or Path(self.opencode_path).exists()

    def is_port_in_use(self, port: int = None) -> bool:
        """Check if a port is already in use"""
        port = port or self.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(("127.0.0.1", port))
                return True
            except ConnectionRefusedError:
                return False
            except Exception as e:
                logger.debug(f"Error checking port {port}: {e}")
                return False

    def find_process_on_port(self, port: int = None) -> Optional[int]:
        """
        Find the PID of the process using a specific port.
        
        Returns:
            PID if found, None otherwise
        """
        import psutil  # Lazy import to avoid dependency if not needed
        
        port = port or self.port
        try:
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    for conn in proc.info.get("connections", []):
                        if conn.laddr.port == port:
                            return proc.info["pid"]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.debug(f"Error finding process on port {port}: {e}")
        return None

    def is_running(self) -> bool:
        """
        Check if OpenCode server is currently running.
        
        Checks both:
        1. Internal process tracking (if we started it)
        2. Port availability (if something else started it)
        """
        # Check if our tracked process is running
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None  # Process died
            self._we_started = False
        
        # Check if port is in use (could be external OpenCode)
        if self.is_port_in_use():
            return True
        
        return False

    async def health_check(self, timeout: float = 5.0) -> bool:
        """Check if OpenCode server is healthy and responding"""
        import httpx

        # Try /global/health first
        endpoints = [
            ("/global/health", "json"),
            ("/session", "json"),  # Fallback: session list should always work
        ]

        for endpoint, expected_type in endpoints:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(f"http://{self.host}:{self.port}{endpoint}")
                    if response.status_code == 200:
                        if expected_type == "json":
                            try:
                                data = response.json()
                                # For /session, any response means healthy
                                if endpoint == "/session":
                                    logger.debug(f"OpenCode health check (via {endpoint}): OK")
                                    return True
                                # For /global.health, check for healthy flag
                                if data.get("healthy", False):
                                    logger.info(f"OpenCode health check passed: {data}")
                                    return True
                            except Exception:
                                # Response is not JSON, continue to next endpoint
                                continue
            except Exception as e:
                logger.debug(f"OpenCode health check ({endpoint}) failed: {e}")

        return False

    def _build_command(self) -> list:
        """Build the opencode serve command"""
        cmd = [self.opencode_path, "serve"]

        # Add port and host
        cmd.extend(["--port", str(self.port)])
        cmd.extend(["--hostname", self.host])

        # Add password if configured
        if self.password:
            cmd.extend(["--port", str(self.port)])  # Redundant but clear
            os.environ["OPENCODE_SERVER_PASSWORD"] = self.password

        return cmd

    async def start(
        self, 
        wait_for_healthy: bool = True, 
        timeout: float = 60.0,
        strict: bool = False
    ) -> bool:
        """
        Start the OpenCode server.

        Args:
            wait_for_healthy: Wait for the server to be healthy before returning
            timeout: Maximum time to wait for server to become healthy
            strict: If True, fail if OpenCode doesn't become healthy (raise exception)

        Returns:
            True if server started successfully

        Raises:
            RuntimeError: If strict mode and OpenCode fails to become healthy
        """
        # Check if already running
        if self.is_running():
            logger.info("OpenCode server is already running")
            return True

        # Check if installed
        if not self.is_installed():
            error_msg = f"OpenCode not found at: {self.opencode_path}"
            if strict:
                raise RuntimeError(error_msg)
            logger.error(error_msg)
            logger.error("Please install OpenCode or set OPENCODE_PATH environment variable")
            return False

        # Check if port is in use by another process
        if self.is_port_in_use():
            pid = self.find_process_on_port()
            if pid:
                logger.warning(f"Port {self.port} is in use by PID {pid}")
                logger.warning("Assuming external OpenCode server is running")
                
                # Verify the process is actually responding
                if await self.health_check(timeout=5.0):
                    logger.success(f"External OpenCode server on port {self.port} is healthy")
                    self._we_started = False
                    return True
            
            error_msg = f"Port {self.port} is in use but OpenCode is not responding (PID: {pid})"
            if strict:
                raise RuntimeError(error_msg)
            logger.error(error_msg)
            logger.warning("Cannot start new OpenCode server because port is in use. Not killing external process.")
            return False

        logger.info(f"Starting OpenCode server: {' '.join(self._build_command())}")

        try:
            # Start the process
            env = os.environ.copy()
            if self.password:
                env["OPENCODE_SERVER_PASSWORD"] = self.password

            self._process = subprocess.Popen(
                self._build_command(),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            self._we_started = True

            # Wait for server to be healthy
            if wait_for_healthy:
                import time
                start_time = time.time()
                healthy = False
                
                while time.time() - start_time < timeout:
                    if await self.health_check(timeout=2.0):
                        healthy = True
                        break
                    await asyncio.sleep(0.5)

                if healthy:
                    logger.success(f"OpenCode server started on {self.host}:{self.port}")
                    return True
                else:
                    error_msg = f"OpenCode server failed to become healthy within {timeout}s"
                    if strict:
                        # Kill the process before raising
                        self._kill_process()
                        raise RuntimeError(error_msg)
                    logger.error(error_msg)
                    return False
            else:
                logger.info("OpenCode server started (not waiting for healthy)")
                return True

        except Exception as e:
            error_msg = f"Failed to start OpenCode server: {e}"
            if strict:
                raise RuntimeError(error_msg)
            logger.error(error_msg)
            return False

    def _kill_process(self) -> None:
        """Force kill the OpenCode process"""
        if self._process is None:
            return
        try:
            self._process.kill()
            self._process.wait(timeout=2)
            logger.debug("OpenCode process killed")
        except Exception as e:
            logger.warning(f"Failed to kill OpenCode process: {e}")
        finally:
            self._process = None

    def stop(self) -> bool:
        """Stop the OpenCode server"""
        if not self.is_running():
            logger.info("OpenCode server is not running")
            return True

        # Check if we started it
        if not self._we_started:
            logger.warning(f"OpenCode server on port {self.port} is managed externally. Not stopping.")
            return True

        if self._process is None:
            logger.warning("Process handle lost, but marked as started by us.")
            self._we_started = False
            return True

        try:
            # Send SIGTERM
            self._process.terminate()

            # Wait for graceful shutdown
            try:
                self._process.wait(timeout=5)
                logger.info("OpenCode server stopped gracefully")
            except subprocess.TimeoutExpired:
                # Force kill
                self._process.kill()
                logger.warning("OpenCode server killed forcefully")

            self._process = None
            self._we_started = False
            return True

        except Exception as e:
            logger.error(f"Failed to stop OpenCode server: {e}")
            return False

    async def restart(self) -> bool:
        """Restart the OpenCode server"""
        logger.info("Restarting OpenCode server...")
        self.stop()
        await asyncio.sleep(1)  # Brief pause
        return await self.start()


# Global launcher instance
_launcher: Optional[OpenCodeLauncher] = None


def get_launcher(
    host: str = "127.0.0.1",
    port: int = 4096,
    password: str = "",
    opencode_path: Optional[str] = None,
) -> OpenCodeLauncher:
    """Get global OpenCode launcher instance"""
    global _launcher
    if _launcher is None:
        _launcher = OpenCodeLauncher(
            host=host,
            port=port,
            password=password,
            opencode_path=opencode_path,
        )
    return _launcher


def reset_launcher() -> None:
    """Reset global launcher (useful for testing)"""
    global _launcher
    if _launcher:
        _launcher.stop()
    _launcher = None
