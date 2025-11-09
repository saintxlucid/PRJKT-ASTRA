"""
ASTRA Secure Launch System
"""
import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from core import (
    get_secure_boot,
    get_divine_lock,
    BootState,
    SecurityProfile
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("astra.launch")

async def launch_astra(config: Dict[str, Any]) -> bool:
    """Launch ASTRA with security"""
    try:
        # Initialize secure boot
        secure_boot = get_secure_boot()
        if not await secure_boot.initialize(config):
            logger.error("Secure boot initialization failed")
            return False
            
        # Enter awakening state
        await secure_boot.change_state(BootState.AWAKENING)
        
        # Verify creator if password provided
        if "creator_password" in config:
            if not await secure_boot.verify_creator(config["creator_password"]):
                logger.error("Creator verification failed")
                await secure_boot.enter_emergency_state(
                    "Creator verification failed"
                )
                return False
                
            # Enter sovereign state
            await secure_boot.change_state(BootState.SOVEREIGN)
            
        else:
            # Enter protected state
            await secure_boot.change_state(BootState.PROTECTED)
            
        return True
        
    except Exception as e:
        logger.error(f"ASTRA launch failed: {str(e)}")
        return False

def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="ASTRA Secure Launch")
    
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Start in offline mode"
    )
    
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable GUI"
    )
    
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore from backup"
    )
    
    parser.add_argument(
        "--creator-password",
        type=str,
        help="Creator password for verification"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    return parser.parse_args()

async def main() -> None:
    """Main entry point"""
    try:
        args = parse_args()
        
        # Build config
        config = {
            "offline_mode": args.offline,
            "gui_enabled": not args.no_gui,
            "debug_mode": args.debug,
            "allowed_plugins": not args.offline,
            "max_memory_mb": 1024 if args.offline else 4096
        }
        
        if args.creator_password:
            config["creator_password"] = args.creator_password
            
        # Launch ASTRA
        if not await launch_astra(config):
            sys.exit(1)
            
        # Keep alive until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("ASTRA shutdown requested")
        divine_lock = get_divine_lock()
        await divine_lock.activate_lock("Manual shutdown")
        
    except Exception as e:
        logger.error(f"ASTRA main loop failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())