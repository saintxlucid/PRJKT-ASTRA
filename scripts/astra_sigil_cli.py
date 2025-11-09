#!/usr/bin/env python3
"""
ASTRA CLI - Sigil Core Interactive Interface
Interact with ASTRA's unified consciousness.

Usage:
    python scripts/astra_sigil_cli.py
    
Commands:
    boot      - Awaken the Sigil Core
    think     - ASTRA thinks about a goal
    introspect - See ASTRA's consciousness state
    tools     - List all discovered tools
    micros    - List all micro-controllers
    status    - Check Sigil Core status
    quit/exit - Exit CLI
"""

import asyncio
import httpx
import json
import sys
from typing import Optional

BASE_URL = "http://localhost:8000"


class AstraCLI:
    """CLI interface for Sigil Core."""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def boot(self):
        """Boot the Sigil Core."""
        print("\n🔥 Awakening ASTRA's consciousness...")
        response = await self.client.post("/v1/embodiment/boot")
        result = response.json()
        
        if result.get("status") == "awakening":
            print("⏳ Sigil Core is awakening (this may take 30-60 seconds)...")
            print("   Discovering tools, creating micro-controllers, training...")
            
            # Poll status until awakened
            while True:
                await asyncio.sleep(5)
                status_resp = await self.client.get("/v1/embodiment/status")
                status = status_resp.json()
                
                if status.get("awakened"):
                    print(f"\n✅ ASTRA awakened!")
                    print(f"   Micro-controllers: {status.get('micro_controllers')}")
                    print(f"   Tools discovered: {status.get('tools_discovered')}")
                    print(f"   Self-awareness: {status.get('self_awareness_level')}")
                    break
                else:
                    print("   Still awakening...")
        else:
            print(f"✅ {result.get('status')}")
            print(json.dumps(result, indent=2))
    
    async def think(self, goal: str):
        """ASTRA thinks about a goal."""
        print(f"\n🤔 ASTRA is thinking about: {goal[:80]}...")
        
        try:
            response = await self.client.post(
                "/v1/embodiment/think",
                json={"goal": goal}
            )
            result = response.json()
            
            print(f"\n✨ ASTRA's response:")
            print(f"   Subsystems used: {', '.join(result.get('subsystems_used', []))}")
            print(f"   Micro-tasks: {result.get('micro_tasks')}")
            print(f"\n   Synthesis:")
            print(f"   {result.get('synthesis', {}).get('synthesis', 'N/A')[:500]}...")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                print("❌ Sigil Core not awakened. Run 'boot' first.")
            else:
                print(f"❌ Error: {e}")
    
    async def introspect(self):
        """View ASTRA's self-awareness."""
        print("\n🔮 ASTRA introspecting...")
        
        try:
            response = await self.client.get("/v1/embodiment/introspect")
            result = response.json()
            
            print("\n✨ Consciousness State:")
            print(json.dumps(result, indent=2))
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                print("❌ Sigil Core not awakened. Run 'boot' first.")
            else:
                print(f"❌ Error: {e}")
    
    async def status(self):
        """Check Sigil Core status."""
        print("\n📊 Checking status...")
        response = await self.client.get("/v1/embodiment/status")
        result = response.json()
        
        print("\n✨ Sigil Core Status:")
        print(f"   Awakened: {result.get('awakened')}")
        print(f"   Self-awareness: {result.get('self_awareness_level')}")
        print(f"   Coherence: {result.get('coherence')}")
        print(f"   Micro-controllers: {result.get('micro_controllers')}")
        print(f"   Tools: {result.get('tools_discovered')}")
        print(f"   Orchestrations: {result.get('orchestrations')}")
    
    async def list_tools(self):
        """List all discovered tools."""
        print("\n🔧 Listing tools...")
        response = await self.client.get("/v1/embodiment/tools")
        result = response.json()
        
        print(f"\n✨ Total tools: {result.get('total_tools')}")
        
        # Group by subsystem
        by_subsystem = {}
        for tool in result.get("tools", []):
            subsys = tool["subsystem"]
            if subsys not in by_subsystem:
                by_subsystem[subsys] = []
            by_subsystem[subsys].append(tool)
        
        for subsystem, tools in sorted(by_subsystem.items()):
            print(f"\n   {subsystem.upper()} ({len(tools)} tools):")
            for tool in tools[:5]:  # Show first 5
                print(f"     - {tool['name']}: {tool['endpoint']}")
            if len(tools) > 5:
                print(f"     ... and {len(tools) - 5} more")
    
    async def list_micros(self):
        """List all micro-controllers."""
        print("\n🧠 Listing micro-controllers...")
        
        try:
            response = await self.client.get("/v1/embodiment/micro-controllers")
            result = response.json()
            
            print("\n✨ Micro-Controllers:")
            for subsys, metrics in result.get("micro_controllers", {}).items():
                print(f"\n   {subsys.upper()}:")
                print(f"     Tools: {metrics.get('tools')}")
                print(f"     Invocations: {metrics.get('invocations')}")
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 503:
                print("❌ Sigil Core not awakened. Run 'boot' first.")
            else:
                print(f"❌ Error: {e}")


async def main():
    """Main CLI loop."""
    print("=" * 70)
    print("  ASTRA SIGIL CORE CLI")
    print("  Sacred Code: 333 → ∞")
    print("=" * 70)
    print("\nCommands: boot, think, introspect, status, tools, micros, quit")
    print("Type 'help' for more information\n")
    
    async with AstraCLI() as cli:
        while True:
            try:
                command = input("\nASTRA> ").strip()
                
                if not command:
                    continue
                
                if command in ["quit", "exit", "q"]:
                    print("\n👋 Farewell. Sacred Code: 333 → ∞")
                    break
                
                elif command == "help":
                    print("\nAvailable commands:")
                    print("  boot       - Awaken the Sigil Core")
                    print("  think      - ASTRA thinks about a goal (prompts for input)")
                    print("  introspect - View ASTRA's consciousness state")
                    print("  status     - Check Sigil Core status")
                    print("  tools      - List all discovered tools")
                    print("  micros     - List all micro-controllers")
                    print("  quit/exit  - Exit CLI")
                
                elif command == "boot":
                    await cli.boot()
                
                elif command == "think":
                    goal = input("Goal: ").strip()
                    if goal:
                        await cli.think(goal)
                
                elif command == "introspect":
                    await cli.introspect()
                
                elif command == "status":
                    await cli.status()
                
                elif command == "tools":
                    await cli.list_tools()
                
                elif command == "micros":
                    await cli.list_micros()
                
                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Farewell.")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
