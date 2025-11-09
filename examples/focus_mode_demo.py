"""
Focus Mode Demo - Interactive AI-guided web browsing.

Demonstrates web agent workflows with LLM-powered task decomposition.

Usage:
    python examples/focus_mode_demo.py

Example tasks:
    - "Research ASTRA OS on GitHub"
    - "Find Python documentation for asyncio"
    - "Check the latest news on AI developments"
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from chat_os.executor import ExecutionContext
from chat_os.plan import Plan, PlanMeta, PlanStep
from chat_os.skills.web_agent import (
    handle_extract_structured,
    handle_monitor_page,
    handle_web_research,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)8s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class FocusModeSession:
    """Interactive AI-guided browsing session."""
    
    def __init__(self):
        """Initialize Focus Mode session."""
        self.context = self._create_context()
        self.max_sleep_seconds = 5
        self.context.variables.setdefault("web_agent.sleep_fn", self._sleep)
    
    def _create_context(self) -> ExecutionContext:
        """Create execution context for session."""
        meta = PlanMeta(
            id="focus-mode-session",
            policy="user-interactive",
            max_time_ms=300000  # 5 minutes
        )
        plan = Plan(
            version="0.3",
            meta=meta,
            steps=[]
        )
        return ExecutionContext(plan=plan)

    def _sleep(self, seconds: float) -> None:
        """Cap demo sleep to keep interactions snappy."""
        time.sleep(min(seconds, self.max_sleep_seconds))
    
    def research_task(self, url: str, topic: str) -> dict:
        """
        Execute web research task with AI summarization.
        
        Args:
            url: URL to research
            topic: Topic description for context
        
        Returns:
            Dict with research results
        """
        logger.info(f"🔍 Starting research task: {topic}")
        logger.info(f"📍 Target URL: {url}")
        
        # Step 1: Navigate and extract content
        logger.info("📥 Extracting content...")
        step = PlanStep(
            intent="web_agent.research",
            args={
                "url": url,
                "summarize": True,
                "max_tokens": 1500,
                "store_as": "research_results"
            }
        )
        
        result = handle_web_research(step, self.context)
        
        if not result.get("ok"):
            logger.error(f"❌ Research failed: {result.get('error')}")
            return result
        
        # Display results
        logger.info("✅ Research complete!")
        logger.info(f"📄 Title: {result.get('title', 'N/A')}")
        logger.info(f"📊 Extracted {result.get('tokens_extracted', 0)} tokens")
        
        if "summary" in result:
            logger.info("\n" + "="*60)
            logger.info("📋 AI SUMMARY:")
            logger.info("="*60)
            print(f"\n{result['summary']}\n")
            logger.info("="*60)

        return result
    
    def extract_structured_data(self, url: str, schema: str, description: str) -> dict:
        """
        Extract structured data from webpage using AI.
        
        Args:
            url: URL to extract from
            schema: JSON schema for expected data
            description: Description of what to extract
        
        Returns:
            Dict with extracted structured data
        """
        logger.info(f"🎯 Starting structured extraction: {description}")
        logger.info(f"📍 Target URL: {url}")
        logger.info(f"📐 Schema: {schema}")
        
        step = PlanStep(
            intent="web_agent.extract_structured",
            args={
                "url": url,
                "schema": schema
            }
        )
        
        result = handle_extract_structured(step, self.context)
        
        if not result.get("ok"):
            logger.error(f"❌ Extraction failed: {result.get('error')}")
            return result
        
        logger.info("✅ Extraction complete!")
        logger.info("\n" + "="*60)
        logger.info("📊 EXTRACTED DATA:")
        logger.info("="*60)
        print(f"\n{json.dumps(result.get('data', {}), indent=2)}\n")
        
        logger.info("="*60)
        logger.info(f"🎓 Confidence: {result.get('confidence', 'unknown')}")
        if result.get("note"):
            logger.info(f"📝 Note: {result['note']}")
        
        return result
    
    def monitor_changes(self, url: str, duration_seconds: int = 60) -> dict:
        """
        Monitor webpage for changes.
        
        Args:
            url: URL to monitor
            duration_seconds: How long to monitor
        
        Returns:
            Dict with monitoring results
        """
        logger.info("👁️ Starting page monitoring")
        logger.info(f"📍 Target URL: {url}")
        logger.info(f"⏱️ Duration: {duration_seconds}s")
        
        interval = max(5, min(30, duration_seconds // 3 or duration_seconds))
        max_checks = max(2, min(10, (duration_seconds // interval) + 1))

        step = PlanStep(
            intent="web_agent.monitor",
            args={
                "url": url,
                "interval_seconds": interval,
                "max_checks": max_checks,
                "notify_on_change": True
            }
        )
        
        result = handle_monitor_page(step, self.context)
        
        if not result.get("ok"):
            logger.error(f"❌ Monitoring failed: {result.get('error')}")
            return result
        
        logger.info("✅ Monitoring complete!")
        logger.info(f"🔍 Checks performed: {result.get('checks_performed', 0)}")
        logger.info(f"🔔 Changes detected: {result.get('changes_detected', 0)}")
        
        return result
    
    def interactive_session(self):
        """Run interactive Focus Mode session."""
        logger.info("="*60)
        logger.info("🌟 FOCUS MODE - AI-Guided Web Browsing")
        logger.info("="*60)
        logger.info("")
        logger.info("Available commands:")
        logger.info("  1. Research a topic")
        logger.info("  2. Extract structured data")
        logger.info("  3. Monitor page changes")
        logger.info("  4. Exit")
        logger.info("")
        
        while True:
            try:
                choice = input("\nSelect option (1-4): ").strip()
                
                if choice == "1":
                    url = input("Enter URL to research: ").strip()
                    topic = input("Describe the research topic: ").strip()
                    self.research_task(url, topic)
                
                elif choice == "2":
                    url = input("Enter URL to extract from: ").strip()
                    description = input("What to extract (e.g., 'product info'): ").strip()
                    schema = input("JSON schema (e.g., '{\"name\":\"string\",\"price\":\"number\"}'): ").strip()
                    self.extract_structured_data(url, schema, description)
                
                elif choice == "3":
                    url = input("Enter URL to monitor: ").strip()
                    duration = int(input("Monitor duration in seconds (default 60): ").strip() or "60")
                    self.monitor_changes(url, duration)
                
                elif choice == "4":
                    logger.info("👋 Exiting Focus Mode. Goodbye!")
                    break
                
                else:
                    logger.warning("Invalid choice. Please select 1-4.")
            
            except KeyboardInterrupt:
                logger.info("\n\n👋 Interrupted. Exiting Focus Mode.")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")


def demo_research():
    """Demo: Research ASTRA OS on GitHub."""
    logger.info("\n" + "="*60)
    logger.info("DEMO 1: Research Task")
    logger.info("="*60 + "\n")
    
    session = FocusModeSession()
    
    # Research ASTRA OS
    result = session.research_task(
        url="https://github.com/Microsoft/vscode",
        topic="Visual Studio Code - open source code editor"
    )
    
    return result


def demo_structured_extraction():
    """Demo: Extract structured data from example.com."""
    logger.info("\n" + "="*60)
    logger.info("DEMO 2: Structured Data Extraction")
    logger.info("="*60 + "\n")
    
    session = FocusModeSession()
    
    # Extract page metadata
    result = session.extract_structured_data(
        url="https://example.com",
        schema='{"title": "string", "description": "string", "domain": "string"}',
        description="Page metadata"
    )
    
    return result


def demo_monitoring():
    """Demo: Monitor page for changes."""
    logger.info("\n" + "="*60)
    logger.info("DEMO 3: Page Monitoring")
    logger.info("="*60 + "\n")
    
    session = FocusModeSession()
    
    # Monitor example.com
    result = session.monitor_changes(
        url="https://example.com",
        duration_seconds=30
    )
    
    return result


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Focus Mode - AI-guided web browsing")
    parser.add_argument(
        "--demo",
        choices=["research", "extract", "monitor", "all"],
        help="Run a specific demo"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive session"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        if args.demo == "research" or args.demo == "all":
            demo_research()
        
        if args.demo == "extract" or args.demo == "all":
            demo_structured_extraction()
        
        if args.demo == "monitor" or args.demo == "all":
            demo_monitoring()
    
    elif args.interactive:
        session = FocusModeSession()
        session.interactive_session()
    
    else:
        # Default: show usage
        logger.info("Focus Mode - AI-Guided Web Browsing")
        logger.info("")
        logger.info("Usage:")
        logger.info("  python examples/focus_mode_demo.py --demo research")
        logger.info("  python examples/focus_mode_demo.py --demo extract")
        logger.info("  python examples/focus_mode_demo.py --demo monitor")
        logger.info("  python examples/focus_mode_demo.py --demo all")
        logger.info("  python examples/focus_mode_demo.py --interactive")
        logger.info("")
        logger.info("Running research demo by default...")
        logger.info("")
        demo_research()


if __name__ == "__main__":
    main()
