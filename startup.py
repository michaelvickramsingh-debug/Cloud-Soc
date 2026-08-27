#!/usr/bin/env python3
"""
CloudGuard Startup Script
One-click launcher for the full stack (Backend + Frontend)

Usage:
    python startup.py

This will:
    1. Kill any existing backend/frontend processes
    2. Start Flask backend on http://127.0.0.1:5001
    3. Start Vite frontend on http://127.0.0.1:3000
    4. Open the dashboard in your default browser
    5. Display a status page
"""

import os
import sys
import subprocess
import time
import webbrowser
import signal
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Ports
BACKEND_PORT = 5001
FRONTEND_PORT = 3000

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_banner():
    """Print startup banner"""
    banner = f"""
{Colors.BOLD}{Colors.CYAN}
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                     🚀 CLOUDGUARD STARTUP SEQUENCE                        ║
║                 Cloud Detection & Response Survival Guide                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
"""
    print(banner)

def cleanup_processes():
    """Kill any existing backend/frontend processes"""
    print(f"{Colors.YELLOW}🧹 Cleaning up old processes...{Colors.ENDC}")

    os.system("killall -9 python python3 node npm 2>/dev/null")
    time.sleep(2)
    print(f"{Colors.GREEN}   ✓ Old processes terminated{Colors.ENDC}\n")

def start_backend():
    """Start Flask backend server"""
    print(f"{Colors.BLUE}⚙️  Starting Backend (Flask)...{Colors.ENDC}")

    venv_python = BACKEND_DIR / "venv" / "bin" / "python"

    if not venv_python.exists():
        print(f"{Colors.RED}   ✗ Python venv not found. Run: cd backend && python -m venv venv{Colors.ENDC}")
        return False

    env = os.environ.copy()
    env['PORT'] = str(BACKEND_PORT)

    backend_log = open("/tmp/cloudguard_backend.log", "w")

    try:
        subprocess.Popen(
            [str(venv_python), str(BACKEND_DIR / "app.py")],
            cwd=str(BACKEND_DIR),
            stdout=backend_log,
            stderr=backend_log,
            env=env,
            preexec_fn=os.setsid  # Create new process group
        )
        time.sleep(4)
        print(f"{Colors.GREEN}   ✓ Backend started on http://127.0.0.1:{BACKEND_PORT}{Colors.ENDC}\n")
        return True
    except Exception as e:
        print(f"{Colors.RED}   ✗ Failed to start backend: {e}{Colors.ENDC}")
        return False

def start_frontend():
    """Start Vite frontend server"""
    print(f"{Colors.BLUE}⚙️  Starting Frontend (React/Vite)...{Colors.ENDC}")

    frontend_log = open("/tmp/cloudguard_frontend.log", "w")

    try:
        subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            stdout=frontend_log,
            stderr=frontend_log,
            preexec_fn=os.setsid  # Create new process group
        )
        time.sleep(5)
        print(f"{Colors.GREEN}   ✓ Frontend started on http://127.0.0.1:{FRONTEND_PORT}{Colors.ENDC}\n")
        return True
    except Exception as e:
        print(f"{Colors.RED}   ✗ Failed to start frontend: {e}{Colors.ENDC}")
        return False

def verify_services():
    """Verify both services are responding"""
    print(f"{Colors.BLUE}✅ Verifying services...{Colors.ENDC}")

    import urllib.request

    # Check backend
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{BACKEND_PORT}/api/stats", timeout=3)
        print(f"{Colors.GREEN}   ✓ Backend responding{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.RED}   ✗ Backend not responding: {e}{Colors.ENDC}")
        return False

    # Check frontend
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{FRONTEND_PORT}", timeout=3)
        print(f"{Colors.GREEN}   ✓ Frontend responding{Colors.ENDC}\n")
    except Exception as e:
        print(f"{Colors.RED}   ✗ Frontend not responding: {e}{Colors.ENDC}")
        return False

    return True

def open_dashboard():
    """Open dashboard in default browser"""
    dashboard_url = f"http://127.0.0.1:{FRONTEND_PORT}"
    print(f"{Colors.BLUE}🌐 Opening dashboard in browser...{Colors.ENDC}")

    try:
        webbrowser.open(dashboard_url)
        print(f"{Colors.GREEN}   ✓ Browser opened to {dashboard_url}{Colors.ENDC}\n")
    except Exception as e:
        print(f"{Colors.YELLOW}   ⚠ Could not open browser: {e}{Colors.ENDC}")
        print(f"   Open manually: {dashboard_url}\n")

def print_status():
    """Print service status"""
    status_box = f"""{Colors.BOLD}{Colors.CYAN}
╔════════════════════════════════════════════════════════════════════════════╗
║                       ✅ CLOUDGUARD IS RUNNING                            ║
╚════════════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
    print(status_box)

    print(f"{Colors.GREEN}📊 Dashboard:{Colors.ENDC}")
    print(f"   {Colors.BOLD}http://127.0.0.1:{FRONTEND_PORT}{Colors.ENDC}")

    print(f"\n{Colors.GREEN}⚙️  Backend API:{Colors.ENDC}")
    print(f"   {Colors.BOLD}http://127.0.0.1:{BACKEND_PORT}/api{Colors.ENDC}")

    print(f"\n{Colors.GREEN}📁 Project Root:{Colors.ENDC}")
    print(f"   {Colors.BOLD}{PROJECT_ROOT}{Colors.ENDC}")

    print(f"\n{Colors.YELLOW}📝 Logs:{Colors.ENDC}")
    print(f"   Backend:  /tmp/cloudguard_backend.log")
    print(f"   Frontend: /tmp/cloudguard_frontend.log")

    print(f"\n{Colors.CYAN}Commands:{Colors.ENDC}")
    print(f"   Stop servers:  Press Ctrl+C")
    print(f"   View backend logs:  tail -f /tmp/cloudguard_backend.log")
    print(f"   View frontend logs: tail -f /tmp/cloudguard_frontend.log")

    shutdown_box = f"""{Colors.BOLD}{Colors.CYAN}
╔════════════════════════════════════════════════════════════════════════════╗
║  Press Ctrl+C to stop the servers                                          ║
╚════════════════════════════════════════════════════════════════════════════╝
{Colors.ENDC}"""
    print(f"\n{shutdown_box}\n")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print(f"\n\n{Colors.YELLOW}🛑 Shutting down CloudGuard...{Colors.ENDC}")
    os.system("killall -9 python python3 node npm 2>/dev/null")
    print(f"{Colors.GREEN}   ✓ All services stopped{Colors.ENDC}\n")
    sys.exit(0)

def main():
    """Main startup sequence"""
    print_banner()

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Cleanup old processes
    cleanup_processes()

    # Start services
    if not start_backend():
        sys.exit(1)

    if not start_frontend():
        sys.exit(1)

    # Verify services
    if not verify_services():
        print(f"{Colors.YELLOW}⚠️  Services started but not responding yet. Waiting...{Colors.ENDC}")
        time.sleep(3)
        if not verify_services():
            print(f"{Colors.RED}✗ Services failed to start properly{Colors.ENDC}")
            sys.exit(1)

    # Open browser
    open_dashboard()

    # Print status
    print_status()

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
