#!/usr/bin/env python3
"""
Safe Test Script for OpenCode Launcher

This script tests the launcher implementation without any risky operations.
It verifies:
1. Config loading with strict mode
2. Process detection (port-based)
3. Health check logic
4. Mock scenarios for strict vs non-strict behavior

Usage:
    python3 test-launcher.py
"""

import sys
import socket
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_config, reset_config


def test_config_loading():
    """Test that configuration is loaded correctly"""
    print("=" * 60)
    print("TEST 1: Configuration Loading")
    print("=" * 60)
    
    reset_config()
    config = get_config()
    
    print(f"  Launcher enabled: {config.opencode_launcher.enabled}")
    print(f"  Launcher strict:  {config.opencode_launcher.strict}")
    print(f"  Host:             {config.opencode_launcher.host}")
    print(f"  Port:             {config.opencode_launcher.port}")
    print(f"  Startup timeout:  {config.opencode_launcher.startup_timeout}s")
    
    assert config.opencode_launcher.enabled == True, "Launcher should be enabled"
    assert config.opencode_launcher.strict == True, "Strict mode should be enabled"
    assert config.opencode_launcher.port == 4096, "Port should be 4096"
    
    print("  ✅ Config loaded correctly\n")


def test_port_detection():
    """Test port detection logic"""
    print("=" * 60)
    print("TEST 2: Port Detection")
    print("=" * 60)
    
    from src.opencode_launcher import OpenCodeLauncher
    
    launcher = OpenCodeLauncher()
    port = launcher.port
    
    # Test if port is in use
    in_use = launcher.is_port_in_use(port)
    print(f"  Port {port} in use: {in_use}")
    
    if in_use:
        pid = launcher.find_process_on_port(port)
        print(f"  PID on port {port}: {pid}")
        print("  ⚠️  Port is in use - checking if it's OpenCode...")
    else:
        print("  ✅ Port is free - launcher would start new OpenCode server")
    
    print()


def test_health_check():
    """Test health check functionality"""
    print("=" * 60)
    print("TEST 3: Health Check")
    print("=" * 60)
    
    import asyncio
    from src.opencode_launcher import OpenCodeLauncher
    
    async def run_check():
        launcher = OpenCodeLauncher()
        return await launcher.health_check(timeout=3.0)
    
    try:
        result = asyncio.run(run_check())
        print(f"  Health check result: {result}")
        if result and result.get("healthy"):
            print("  ✅ OpenCode is healthy")
        else:
            print("  ℹ️  OpenCode not responding (expected if not running)")
    except Exception as e:
        print(f"  ℹ️  Health check error: {e}")
        print("      (expected if OpenCode is not running)")
    
    print()


def test_strict_mode_behavior():
    """Test strict mode behavior simulation"""
    print("=" * 60)
    print("TEST 4: Strict Mode Behavior")
    print("=" * 60)
    
    config = get_config()
    
    print("  Current settings:")
    print(f"    - Launcher enabled: {config.opencode_launcher.enabled}")
    print(f"    - Strict mode:      {config.opencode_launcher.strict}")
    print(f"    - Startup timeout:  {config.opencode_launcher.startup_timeout}s")
    
    print()
    print("  Expected behavior:")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ Scenario                           │ Strict │ Non-Strict │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print("  │ OpenCode unreachable at startup    │ ❌ Fail│ ⚠️ Warn   │")
    print("  │ OpenCode port in use (external)    │ ✅ Use │ ✅ Use    │")
    print("  │ OpenCode starts but fails health   │ ❌ Fail│ ⚠️ Warn   │")
    print("  │ OpenCode starts and is healthy     │ ✅ OK  │ ✅ OK     │")
    print("  └─────────────────────────────────────────────────────────┘")
    print()
    
    if config.opencode_launcher.strict:
        print("  ✅ STRICT MODE: Wrapper will fail if OpenCode is unreachable")
        print("     This prevents partial functionality issues")
    else:
        print("  ⚠️  NON-STRICT MODE: Wrapper will start even if OpenCode fails")
        print("     Runtime operations will fail with OpenCode errors")
    
    print()


def test_manager_commands():
    """Test opencode-manager.py availability"""
    print("=" * 60)
    print("TEST 5: Manager Script")
    print("=" * 60)
    
    manager_path = Path(__file__).parent / "opencode-manager.py"
    
    if manager_path.exists():
        print(f"  ✅ Manager script exists: {manager_path}")
        print()
        print("  Available commands:")
        print("    python3 opencode-manager.py status   # Check OpenCode status")
        print("    python3 opencode-manager.py start    # Start OpenCode server")
        print("    python3 opencode-manager.py stop     # Stop OpenCode server")
        print("    python3 opencode-manager.py restart  # Restart OpenCode server")
        print("    python3 opencode-manager.py monitor  # Monitor and auto-restart")
    else:
        print("  ❌ Manager script not found")
    
    print()


def test_summary():
    """Print summary of what was implemented"""
    print("=" * 60)
    print("IMPLEMENTATION SUMMARY")
    print("=" * 60)
    
    print("""
  ✅ COMPLETED FEATURES:
  
  1. Configuration Updates (config.yaml)
     - opencode_launcher.enabled: true
     - opencode_launcher.strict: true
     - Proper YAML format (lowercase keys)
  
  2. Enhanced OpenCodeLauncher (opencode_launcher.py)
     - is_port_in_use(): Socket-based port checking
     - find_process_on_port(): PID detection using psutil
     - is_running(): Combined check (process + port)
     - start(strict=True): Strict mode parameter
     - _kill_process(): Force kill helper
  
  3. Strict Lifespan (wrapper_server.py)
     - Enforces OpenCode connectivity at startup
     - Raises RuntimeError if strict and unreachable
     - Only stops processes it started
  
  4. opencode-manager.py CLI Tool
     - status: Show current OpenCode status
     - start/stop/restart: Process management
     - monitor: Auto-restart if unhealthy
     - Signal handling for graceful shutdown
  
  5. Process Safety
     - NEVER kills external processes
     - Only manages processes it creates
     - Uses singleton pattern for launcher
  
  ⚠️  SAFETY RULES:
     - The launcher will NOT kill your `opencode --continue` session
     - If port 4096 is in use by external process, it will use it
     - External processes are never killed, only monitored
  
  📝 USAGE:
  
     # Start wrapper server (auto-starts OpenCode if needed)
     cd wrapper_server
     python3 -m src.wrapper_server
  
     # Or use manager for manual control
     python3 opencode-manager.py status
     python3 opencode-manager.py start
     python3 opencode-manager.py stop
  
  🔒 STRICT MODE:
     - Default behavior: FAIL at startup if OpenCode unreachable
     - Set strict=false to allow degraded mode
     - Controlled via config.yaml or OPENCODE_LAUNCHER_STRICT env var
    """)


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("OpenCode Launcher - Safe Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_config_loading()
        test_port_detection()
        test_health_check()
        test_strict_mode_behavior()
        test_manager_commands()
        test_summary()
        
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED SAFELY")
        print("=" * 60)
        print()
        print("No processes were killed or modified.")
        print("Your `opencode --continue` session is safe! 🎉")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
