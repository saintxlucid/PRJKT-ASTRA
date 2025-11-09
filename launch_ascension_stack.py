"""
ASTRA Ascension Stack Launcher
Launch integrated Neural Browser V2 + Live Autonomy + Task Agents

Usage:
    python launch_ascension_stack.py [--port PORT] [--host HOST]

Sacred Code: 333
"""

import sys
import subprocess
from pathlib import Path

# ASCII Art Banner
BANNER = r"""
═══════════════════════════════════════════════════════════════════════════
    ___    _____ __________ ___       ___   ___   _____ _____ ___   _   _____  
   / _ \  / ____/_  __/ __ `__ \   / _ \ | | | | / ___// ____|/ _ \ | | | |  __ \ 
  / /_\ \|  |___  | | | |  |  | | / /_\ \| | | |/ /   | |    | | | || | | | |__) |
  |  _  ||_____ \ | | | |  |  | | |  _  || | | |\ \   | |    | | | || | | |  ___/ 
  | | | | ____| | | | | |  |  | | | | | || |_| | \ \__| |____| |_| || |_| | |     
  |_| |_|\_____/  |_| |_|  |__|_| |_| |_| \___/   \___\\____/ \___/  \___/|_|     
                                                                                   
                  ASCENSION STACK V2 - NEURAL BROWSER EVOLUTION
                          
                  🧠 Neural Browser V2 (Memory Editing + Video Export)
                  🧬 Live Prompt Autonomy (Proactive Initiation)
                  🤖 Task Agent Mode (Tool Automation)
                  
                  Sacred Code: 333 ∞
                  "I only obey God" - Built for Saint Lucid
═══════════════════════════════════════════════════════════════════════════
"""


def check_dependencies():
    """Check if required dependencies are installed"""
    required = {
        'fastapi': 'pip install fastapi',
        'uvicorn': 'pip install uvicorn[standard]',
        'websockets': 'pip install websockets',
        'psutil': 'pip install psutil',
    }
    
    missing = []
    for package, install_cmd in required.items():
        try:
            __import__(package)
        except ImportError:
            missing.append((package, install_cmd))
    
    if missing:
        print("❌ Missing required dependencies:\n")
        for package, install_cmd in missing:
            print(f"   • {package}: {install_cmd}")
        print("\nInstall all at once:")
        print("   pip install fastapi uvicorn[standard] websockets psutil")
        return False
    
    return True


def print_startup_info(host: str, port: int):
    """Print startup information"""
    print(BANNER)
    print("\n🚀 STARTING ASCENSION STACK...\n")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   🎛️  Control Panel: http://{host}:{port}/")
    print(f"   📚 API Docs: http://{host}:{port}/docs")
    print(f"   🔌 WebSocket: ws://{host}:{port}/ws/graph")
    print("\n📡 AVAILABLE ENDPOINTS:")
    print(f"   • Graph API: http://{host}:{port}/api/graph")
    print(f"   • Autonomy API: http://{host}:{port}/api/autonomy")
    print(f"   • Agent API: http://{host}:{port}/api/agent")
    print(f"   • Video Export: http://{host}:{port}/api/video")
    print(f"   • System Health: http://{host}:{port}/api/system/health")
    print("\n🎮 QUICK START:")
    print("   1. Open Control Panel in browser for full autonomy controls")
    print("   2. Or use API docs for programmatic access")
    print("   3. Custom triggers available in src/astra/visualization/custom_triggers.py")
    print("   4. Memory bridge connects to live ASTRA memories (Chroma/SQLite)")
    print("\n🔮 Press Ctrl+C to stop\n")
    print("═" * 80)
    print()


def main():
    """Main launcher"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ASTRA Ascension Stack Launcher")
    parser.add_argument('--host', default='127.0.0.1', help='Host address')
    parser.add_argument('--port', type=int, default=8765, help='Port number')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Print startup info
    print_startup_info(args.host, args.port)
    
    # Launch uvicorn server
    try:
        cmd = [
            sys.executable, '-m', 'uvicorn',
            'astra.visualization.ascension_api:app',
            '--host', args.host,
            '--port', str(args.port),
        ]
        
        if args.reload:
            cmd.append('--reload')
        
        subprocess.run(cmd)
    
    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown initiated...")
        print("✨ ASTRA Ascension Stack stopped gracefully")
        print("\n333 ∞\n")


if __name__ == "__main__":
    main()
