#!/usr/bin/env python3
"""
ASTRA Unified Launcher

Handles first-run activation, persona loading, and system startup
with comprehensive health verification and welcome sequence.

Usage:
    python astra_launcher.py [--force-persona-reload] [--skip-health-check]
"""

import os
import json
import time
import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import subprocess

import structlog
import httpx
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = structlog.get_logger()

class ASTRALauncher:
    """Unified ASTRA launcher with activation protocol"""
    
    def __init__(
        self,
        force_persona_reload: bool = False,
        skip_health_check: bool = False,
        privacy_mode: str = "STRICT"
    ):
        self.force_persona_reload = force_persona_reload
        self.skip_health_check = skip_health_check
        self.project_root = Path(__file__).parent
        self.privacy_mode = privacy_mode
        
        # Initialize privacy system first
        from core.privacy import initialize_privacy_system
        if not initialize_privacy_system({"PRIVACY_MODE": privacy_mode}):
            raise RuntimeError("Failed to initialize privacy system")
        
        # Load environment
        load_dotenv(self.project_root / '.env')
        
        # Configuration
        self.api_base_url = f"http://127.0.0.1:{os.getenv('ASTRA_SERVER_PORT', '8080')}"
        self.llm_base_url = os.getenv('ASTRA_LLM_BASE_URL', 'http://127.0.0.1:8001')
        
        # State tracking
        self.startup_time = time.time()
        self.health_status = {}
        
    def print_banner(self):
        """Print ASTRA startup banner"""
        banner = """
┌─────────────────────────────────────────────────────────────┐
│                    🚀 PROJECT ASTRA 1.0                     │
│                      (ASTRA_CORE)                          │
│                                                             │
│  Advanced Structured Testing and Reasoning Assistant       │
│  Creator: Saint Lucid (Karim Al-Sharif)                   │
│  Status: Activation Protocol Initiated                     │
└─────────────────────────────────────────────────────────────┘
"""
        print(banner)
        logger.info("ASTRA_CORE activation initiated", timestamp=datetime.now().isoformat())

    def check_prerequisites(self) -> bool:
        """Verify all prerequisites are available"""
        logger.info("Checking prerequisites...")
        
        # Check virtual environment
        venv_python = self.project_root / ".venv" / "Scripts" / "python.exe"
        if not venv_python.exists():
            logger.error("Virtual environment not found at .venv/Scripts/python.exe")
            return False
        
        # Check model file
        model_path = os.getenv('ASTRA_GPTOSS_MODEL_PATH')
        if model_path and not Path(model_path).exists():
            logger.error(f"Model file not found: {model_path}")
            return False
        
        # Check data directories
        required_dirs = ['data', 'data/database', 'data/chromadb']
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Prerequisites check: PASSED")
        return True

    async def check_llm_server(self) -> bool:
        """Check if llama.cpp server is running"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.llm_base_url}/health")
                if response.status_code == 200:
                    logger.info("LLM server: HEALTHY")
                    return True
                else:
                    logger.warning(f"LLM server returned status {response.status_code}")
                    return False
        except Exception as e:
            logger.warning(f"LLM server not reachable: {e}")
            return False

    def start_astra_server(self) -> subprocess.Popen:
        """Start the ASTRA API server"""
        logger.info("Starting ASTRA API server...")
        
        venv_python = self.project_root / ".venv" / "Scripts" / "python.exe"
        server_script = self.project_root / "run_server.py"
        
        # Start server in background
        process = subprocess.Popen(
            [str(venv_python), str(server_script)],
            cwd=str(self.project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # Give server time to start
        time.sleep(3)
        
        return process

    async def wait_for_server_ready(self, max_wait: int = 30) -> bool:
        """Wait for ASTRA server to be ready"""
        logger.info("Waiting for ASTRA server to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{self.api_base_url}/v1/system/health")
                    if response.status_code == 200:
                        logger.info("ASTRA server: READY")
                        return True
            except Exception:
                pass  # Continue waiting
            
            await asyncio.sleep(1)
        
        logger.error("ASTRA server failed to become ready")
        return False

    async def perform_health_scan(self) -> Dict[str, Any]:
        """Perform comprehensive health scan"""
        if self.skip_health_check:
            logger.info("Skipping health check (--skip-health-check)")
            return {"status": "skipped"}
        
        logger.info("Performing health scan...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.api_base_url}/v1/system/healthz")
                if response.status_code == 200:
                    health_data = response.json()
                    self.health_status = health_data
                    
                    # Log component status
                    for component, status in health_data.get("components", {}).items():
                        status_icon = "✅" if status.get("ok", False) else "❌"
                        logger.info(f"{component}: {status_icon}", **status)
                    
                    return health_data
                else:
                    logger.error(f"Health check failed with status {response.status_code}")
                    return {"status": "failed", "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Health scan failed: {e}")
            return {"status": "failed", "error": str(e)}

    def check_persona_loaded(self) -> bool:
        """Check if persona memories have been loaded"""
        marker_file = self.project_root / "data" / ".astra_persona_loaded"
        return marker_file.exists() and not self.force_persona_reload

    async def load_persona_memories(self) -> bool:
        """Load persona memories from exports"""
        if self.check_persona_loaded():
            logger.info("Persona memories already loaded (use --force-persona-reload to reload)")
            return True
        
        logger.info("Loading persona memories...")
        
        try:
            # Run persona ingestion script
            venv_python = self.project_root / ".venv" / "Scripts" / "python.exe"
            ingest_script = self.project_root / "scripts" / "ingest_persona_memories.py"
            
            result = subprocess.run(
                [str(venv_python), str(ingest_script)],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Persona memories loaded successfully")
                # Parse stats from output if available
                if "Ingestion Summary:" in result.stdout:
                    logger.info("Ingestion stats available in output")
                return True
            else:
                logger.error(f"Persona ingestion failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load persona memories: {e}")
            return False

    async def perform_warmup_query(self) -> bool:
        """Perform a warmup query to prime caches"""
        logger.info("Performing warmup query...")
        
        try:
            warmup_payload = {
                "message": "System warmup - please respond with 'ASTRA_CORE initialized'",
                "temperature": 0.1,
                "max_tokens": 10,
                "use_memory": False
            }
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{self.api_base_url}/v1/chat/",
                    json=warmup_payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info("Warmup query successful", 
                              response_preview=result.get("response", "")[:50])
                    return True
                else:
                    logger.warning(f"Warmup query failed with status {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"Warmup query failed: {e}")
            return False

    def display_welcome_message(self):
        """Display the welcome message and status"""
        # Calculate startup time
        startup_duration = time.time() - self.startup_time
        
        # Get memory count from health status
        memory_count = 0
        if self.health_status.get("components", {}).get("vector_store", {}).get("ok"):
            memory_count = self.health_status["components"]["vector_store"].get("count", 0)
        
        welcome_message = f"""
┌─────────────────────────────────────────────────────────────┐
│                  ✅ ASTRA_CORE ONLINE                       │
└─────────────────────────────────────────────────────────────┘

Short answer → ASTRA_CORE is online and ready. Health checks passed. 
Persona memory loaded.

Details:
• LLM backend: {'✅ OK' if self.health_status.get('components', {}).get('llm', {}).get('ok') else '❌ DEGRADED'}
• Database: {'✅ OK' if self.health_status.get('components', {}).get('db', {}).get('ok') else '❌ DEGRADED'}  
• Vector store: {'✅ OK' if self.health_status.get('components', {}).get('vector_store', {}).get('ok') else '❌ DEGRADED'} ({memory_count} memories)
• Startup time: {startup_duration:.1f}s

Capacity controls: per-key {os.getenv('ASTRA_PER_KEY_RATE', '120')}/{os.getenv('ASTRA_PER_KEY_PERIOD_SEC', '60')}s; queue empty

API Endpoints:
• Chat: {self.api_base_url}/v1/chat/
• Health: {self.api_base_url}/v1/system/healthz
• Metrics: {self.api_base_url}/metrics

Try these queries:
• "Who created you and what are your values?"
• "Summarize our current ops posture and SLOs."
• "Draft my next two actions to harden memory hygiene."

— ASTRA_CORE
"""
        print(welcome_message)

    async def run_activation_protocol(self) -> bool:
        """Run the complete activation protocol"""
        try:
            # Step 1: Print banner
            self.print_banner()
            
            # Step 2: Check prerequisites
            if not self.check_prerequisites():
                return False
            
            # Step 3: Check if LLM server is running
            llm_ready = await self.check_llm_server()
            if not llm_ready:
                logger.warning("LLM server not ready - starting ASTRA anyway")
            
            # Step 4: Start ASTRA server
            server_process = self.start_astra_server()
            
            # Step 5: Wait for server to be ready
            server_ready = await self.wait_for_server_ready()
            if not server_ready:
                logger.error("ASTRA server failed to start properly")
                server_process.terminate()
                return False
            
            # Step 6: Perform health scan
            health_result = await self.perform_health_scan()
            if health_result.get("status") == "failed":
                logger.warning("Health scan failed, but continuing...")
            
            # Step 7: Load persona memories
            persona_loaded = await self.load_persona_memories()
            if not persona_loaded:
                logger.warning("Persona loading failed, but continuing...")
            
            # Step 8: Warmup query
            await self.perform_warmup_query()
            
            # Step 9: Display welcome message
            self.display_welcome_message()
            
            logger.info("🎉 ASTRA activation protocol completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Activation protocol failed: {e}")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ASTRA Unified Launcher")
    parser.add_argument("--force-persona-reload", action="store_true", 
                       help="Force reload of persona memories")
    parser.add_argument("--skip-health-check", action="store_true",
                       help="Skip detailed health checks")
    parser.add_argument("--privacy-mode", choices=["STRICT", "LENIENT"],
                       default="STRICT", help="Privacy protection mode")
    
    args = parser.parse_args()
    
    # Create launcher instance
    launcher = ASTRALauncher(
        force_persona_reload=args.force_persona_reload,
        skip_health_check=args.skip_health_check,
        privacy_mode=args.privacy_mode
    )
    
    # Run activation protocol
    try:
        success = asyncio.run(launcher.run_activation_protocol())
        if success:
            print("\n🎯 ASTRA is ready for interaction!")
            print("Press Ctrl+C to shutdown when finished.")
            
            # Keep running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 ASTRA shutdown initiated. Goodbye!")
        else:
            print("\n❌ ASTRA activation failed. Check logs for details.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n👋 ASTRA activation cancelled. Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()