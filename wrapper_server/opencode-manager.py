#!/usr/bin/env python3
"""
OpenCode Process Manager

A standalone script to manage the OpenCode server process independently
from the wrapper server. Useful for manual operations, debugging, and
automation.

Usage:
    python opencode-manager.py status   # Show current status
    python opencode-manager.py start    # Start OpenCode server
    python opencode-manager.py stop     # Stop OpenCode server
    python opencode-manager.py restart  # Restart OpenCode server
    python opencode-manager.py monitor  # Monitor and restart if needed

Features:
- Check if OpenCode is running on configured port
- Start OpenCode server with proper configuration
- Graceful shutdown with SIGTERM, force kill with SIGKILL
- Monitor mode: automatically restart if process dies
- Proper signal handling for clean shutdown
"""

import asyncio
import os
import signal
import socket
import sys
import time
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.opencode_launcher import get_launcher, reset_launcher


class OpenCodeManager:
    """Manage OpenCode server process"""
    
    def __init__(self):
        self.config = get_config()
        self.launcher = None
        self.monitor_task = None
        self.shutdown_event = asyncio.Event()
    
    def is_port_in_use(self, port: int = None) -> bool:
        """Check if a port is already in use"""
        port = port or self.config.opencode_launcher.port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect(("127.0.0.1", port))
                return True
            except ConnectionRefusedError:
                return False
            except Exception:
                return False
    
    def find_pid_on_port(self, port: int = None) -> Optional[int]:
        """Find PID of process using a port"""
        import psutil
        port = port or self.config.opencode_launcher.port
        try:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    for conn in proc.info.get("connections", []):
                        if conn.laddr.port == port:
                            return proc.info["pid"]
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        return None
    
    async def check_health(self, timeout: float = 5.0) -> bool:
        """Check if OpenCode is healthy"""
        self.launcher = get_launcher(
            host=self.config.opencode_launcher.host,
            port=self.config.opencode_launcher.port,
            password=self.config.opencode_launcher.password,
            opencode_path=self.config.opencode_launcher.opencode_path or None,
        )
        return await self.launcher.health_check(timeout=timeout)
    
    def status(self) -> bool:
        """Show current status"""
        port = self.config.opencode_launcher.port
        host = self.config.opencode_launcher.host
        
        print(f"\n{'='*60}")
        print(f"OpenCode Status - {host}:{port}")
        print(f"{'='*60}")
        
        # Check port
        port_in_use = self.is_port_in_use(port)
        pid = self.find_pid_on_port(port) if port_in_use else None
        
        print(f"Port {port} in use: {'Yes' if port_in_use else 'No'}")
        if pid:
            print(f"Process PID: {pid}")
        
        # Check health
        if port_in_use:
            print("\nChecking health...")
            try:
                # Use synchronous check for status command
                import httpx
                with httpx.Client(timeout=3.0) as client:
                    response = client.get(f"http://{host}:{port}/global/health")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("healthy"):
                            print("✅ OpenCode is HEALTHY")
                            return True
                print("❌ OpenCode is UNHEALTHY (not responding)")
                return False
            except Exception as e:
                print(f"❌ Health check failed: {e}")
                return False
        else:
            print("❌ OpenCode is NOT RUNNING")
            return False
    
    async def start(self, wait: bool = True) -> bool:
        """Start OpenCode server"""
        print(f"\nStarting OpenCode server on {self.config.opencode_launcher.host}:{self.config.opencode_launcher.port}...")
        
        self.launcher = get_launcher(
            host=self.config.opencode_launcher.host,
            port=self.config.opencode_launcher.port,
            password=self.config.opencode_launcher.password,
            opencode_path=self.config.opencode_launcher.opencode_path or None,
        )
        
        # Check if already running
        if self.launcher.is_running():
            print("OpenCode is already running")
            return await self.check_health()
        
        # Start
        started = await self.launcher.start(
            wait_for_healthy=wait,
            timeout=self.config.opencode_launcher.startup_timeout,
            strict=True,  # Manager always uses strict mode
        )
        
        if started:
            print("✅ OpenCode started successfully")
        else:
            print("❌ Failed to start OpenCode")
        
        return started
    
    def stop(self, force: bool = False) -> bool:
        """Stop OpenCode server"""
        print(f"\nStopping OpenCode server...")
        
        if self.launcher is None:
            self.launcher = get_launcher(
                host=self.config.opencode_launcher.host,
                port=self.config.opencode_launcher.port,
                password=self.config.opencode_launcher.password,
                opencode_path=self.config.opencode_launcher.opencode_path or None,
            )
        
        if not self.launcher.is_running():
            print("OpenCode is not running")
            return True
        
        # Check if we started it (has process reference)
        if self.launcher._process is None:
            # External process - do NOT kill it
            pid = self.find_pid_on_port()
            if pid:
                print(f"Found external OpenCode process (PID: {pid})")
                print("⚠️  Process was not started by this instance. Refusing to stop it.")
                print("   If you want to stop it, use 'kill <pid>' manually.")
                return False
            else:
                print("Could not find OpenCode process")
                return False
        
        # We started it - use launcher stop
        success = self.launcher.stop()
        if success:
            print("✅ OpenCode stopped")
        else:
            print("❌ Failed to stop OpenCode")
        
        return success
    
    async def restart(self, wait: bool = True) -> bool:
        """Restart OpenCode server"""
        print("\nRestarting OpenCode server...")
        self.stop(force=True)
        await asyncio.sleep(1)
        return await self.start(wait=wait)
    
    async def monitor(self, interval: float = 5.0):
        """Monitor OpenCode and restart if needed"""
        print(f"\nStarting monitor mode (checking every {interval}s)...")
        print("Press Ctrl+C to stop\n")
        
        async def monitor_loop():
            while not self.shutdown_event.is_set():
                try:
                    if not await self.check_health(timeout=3.0):
                        print("\n⚠️ OpenCode is unhealthy, restarting...")
                        if await self.start(wait=True):
                            print("✅ OpenCode restarted successfully")
                        else:
                            print("❌ Failed to restart OpenCode")
                except Exception as e:
                    print(f"\n❌ Monitor error: {e}")
                
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=interval)
                    break
                except asyncio.TimeoutExpired:
                    continue
        
        await monitor_loop()
        print("\nMonitor stopped")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            print("\n\nReceived shutdown signal...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def run_manager(args):
    """Run the manager with given arguments"""
    manager = OpenCodeManager()
    manager.setup_signal_handlers()
    
    if args.command == "status":
        return manager.status()
    
    elif args.command == "start":
        return await manager.start()
    
    elif args.command == "stop":
        return manager.stop(force=args.force)
    
    elif args.command == "restart":
        return await manager.restart()
    
    elif args.command == "monitor":
        await manager.monitor()
        return True
    
    else:
        print(f"Unknown command: {args.command}")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OpenCode Process Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python opencode-manager.py status    # Show current status
    python opencode-manager.py start     # Start OpenCode server
    python opencode-manager.py stop      # Stop OpenCode server
    python opencode-manager.py restart   # Restart OpenCode server
    python opencode-manager.py monitor   # Monitor and auto-restart
        """
    )
    
    parser.add_argument(
        "command",
        choices=["status", "start", "stop", "restart", "monitor"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force kill (for stop command)"
    )
    
    args = parser.parse_args()
    
    try:
        success = asyncio.run(run_manager(args))
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
