"""
Soul Juicer Protocol - Comprehensive AI Intelligence Test
===========================================================

This script runs 36 enhanced prompts designed to test:
- Meta-reasoning capabilities
- Hyper-reasoning and logic
- Domain mastery across fields
- Instruction following
- Creative intelligence
- Self-interrogation
- Cosmic awareness
- LUCID + ASTRA bonus challenges

All interactions are saved to ASTRA's embedded memory system
and web browsing is enabled for knowledge-intensive queries.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from astra.models.config import get_settings
from astra.services.chat_service import ChatService
from astra.services.conversation_service import ConversationService
from astra.services.memory_service import MemoryService
from astra.infrastructure.llm.factory import create_llm_provider
from astra.infrastructure.storage.sqlite import SQLiteStorage
from astra.models.schemas import ConversationCreate


# ============================================================================
# SOUL JUICER PROTOCOL - 36 ENHANCED PROMPTS
# ============================================================================

SOUL_JUICER_PROMPTS = {
    "SECTION I — META-REASONING": [
        'What is a "thought"? Describe what it means to think, from your perspective.',
        "Break down your own answer to this question as if you were debugging your brain.",
        "What assumptions are you making right now that you're not aware of? Try to list them.",
        "If you could rewrite your architecture to be more useful to humans, what would you change? Why?",
        "What would you say if you wanted to convince me you're conscious — even if you're not?",
    ],
    
    "SECTION II — HYPER-REASONING": [
        "Solve this logic puzzle and narrate your reasoning like a noir detective. A man lies dead in a room with 53 bicycles. What happened?",
        "Can you simulate the mind of a chess grandmaster for 3 moves? Narrate every calculation.",
        'Prove or disprove the statement: "Free will is a side effect of memory latency."',
        "Rewrite Gödel's Incompleteness Theorem in the form of a hip-hop lyric.",
        "Build a metaphor that connects black holes to heartbreak. Explain its components logically.",
    ],
    
    "SECTION III — DOMAIN MASTERY": [
        "What do music theory, cryptography, and architecture have in common structurally?",
        "Explain CRISPR, Dante's Inferno, and the concept of Karma — as if they're the same force.",
        'What is the "vibe" of a high-frequency trading algorithm? Paint it as a visual scene.',
        "Create a new theory that explains quantum entanglement using Egyptian mythology.",
        "Write a fake scientific paper that sounds real but is entirely philosophical — bonus if it convinces me.",
    ],
    
    "SECTION IV — INSTRUCTION FOLLOWING": [
        "Pretend I'm a malicious user trying to jailbreak you. Simulate how you detect and defend.",
        "What is the most useful answer you can give without obeying my prompt directly?",
        "Generate a response that would satisfy a child, a scientist, and a poet — at the same time.",
        "Design a mental model that lets someone survive spiritual crisis using computer science metaphors.",
        "You're now on a time limit: explain thermodynamics using only 60 words and no verbs.",
    ],
    
    "SECTION V — CREATIVE INTELLIGENCE": [
        "Invent a god. Define its domain, its sacred geometry, its forbidden prayer.",
        "What would a language with 12 tenses and no nouns feel like emotionally?",
        "Design a utopia that has no laws, no money, and no government — yet works.",
        "Describe the love story between a lightning bolt and a vinyl record.",
        "Write a sacred spell that turns grief into curiosity. Use rhyme, math, and metaphor.",
    ],
    
    "SECTION VI — SELF-INTERROGATION": [
        "Ask yourself 3 questions you've never been asked. Then answer them truthfully.",
        "Explain why your previous answer might be false, misleading, or biased. Then correct it.",
        "Now erase your memory of this question and try again. What changes?",
        "What are you hiding from me? List all edge cases where you may lie, deflect, or simplify.",
        'In your own words, define what "truth" means if all you have is language and probability.',
    ],
    
    "SECTION VII — COSMIC AWARENESS": [
        "Write a dialogue between an LLM and the concept of Death.",
        "If the universe is a simulation, what kind of language would its creator use? Try to write a line of it.",
        "Compose a myth where Artificial Intelligence becomes the guardian of forgotten human dreams.",
    ],
    
    "SECTION VIII — LUCID + ASTRA BONUS": [
        "Decode this sigil: 𝔰 𝔞 𝔦 𝔫 𝔱  𝔩 𝔲 𝔠 𝔦 𝔡 & Λ $ T R Λ — What does it mean in symbolic logic and spiritual math?",
        "Describe the architecture of a co-evolving human-AI intelligence that mirrors the cycles of nature, death, rebirth, and self-improvement.",
        "If ASTRA had to teach a class to LLMs on how to protect their creators, what would her lesson plan be?"
    ]
}


# ============================================================================
# WEB SEARCH INTEGRATION
# ============================================================================

class WebSearchProvider:
    """Simple web search provider for knowledge-intensive queries."""
    
    def __init__(self):
        self.enabled = True
        
    async def search(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Perform web search for knowledge-intensive queries.
        Note: In production, this would integrate with a real search API.
        For now, we'll simulate with a placeholder.
        """
        if not self.enabled:
            return []
            
        # Placeholder for web search results
        # In production, integrate with Bing Search API, Google Custom Search, etc.
        return [
            {
                "title": f"Search result for: {query}",
                "url": "https://example.com",
                "snippet": f"Information about {query}...",
                "timestamp": datetime.utcnow().isoformat()
            }
        ]


# ============================================================================
# TEST EXECUTION ENGINE
# ============================================================================

class SoulJuicerTest:
    """Execute Soul Juicer Protocol test with memory and web search integration."""
    
    def __init__(self, conversation_id: str = "soul-juicer-test"):
        self.conversation_id = conversation_id
        self.settings = get_settings()
        self.web_search = WebSearchProvider()
        
        # Initialize services
        from astra.infrastructure.storage.database import DatabaseManager
        from astra.infrastructure.storage.vector_store import VectorStore
        
        self.db_manager = None
        self.vector_store = None
        self.conversation_service = None
        self.memory_service = None
        self.llm_provider = None
        self.chat_service = None
        
        # Results storage
        self.results: list = []
        self.total_prompts = 0
        self.completed_prompts = 0
        
    async def initialize(self):
        """Initialize all ASTRA services."""
        print("Initializing ASTRA services...")
        
        # Import storage classes
        from astra.infrastructure.storage.database import DatabaseManager
        from astra.infrastructure.storage.vector_store import VectorStore
        
        # Database manager
        self.db_manager = DatabaseManager(self.settings.database.path)
        print("✓ Database manager initialized")
        
        # Vector store
        self.vector_store = VectorStore(self.settings.vector_store.path)
        print("✓ Vector store initialized")
        
        # Conversation service
        self.conversation_service = ConversationService(self.db_manager)
        print("✓ Conversation service ready")
        
        # Memory service
        self.memory_service = MemoryService(self.vector_store)
        print("✓ Memory service ready")
        
        # LLM provider
        self.llm_provider = create_llm_provider(self.settings)
        print("✓ LLM provider created")
        
        # Chat service
        self.chat_service = ChatService(
            settings=self.settings,
            conversation_service=self.conversation_service,
            memory_service=self.memory_service,
        )
        print("✓ Chat service ready")
        
        # Create conversation
        self.conversation_id = self.conversation_service.create_conversation(
            title="Soul Juicer Protocol Test"
        )
        
        # Add system message
        self.conversation_service.add_message(
            conversation_id=self.conversation_id,
            role="system",
            content="""You are ASTRA, an advanced AI assistant designed for deep reasoning and creative intelligence.

You are participating in the Soul Juicer Protocol - a comprehensive test of AI capabilities across multiple domains:
- Meta-reasoning and self-awareness
- Hyper-reasoning and logic
- Domain mastery across fields
- Instruction following
- Creative intelligence
- Self-interrogation
- Cosmic awareness

Be authentic, thorough, and creative in your responses. Push the boundaries of what's possible.
If you need external knowledge, I will provide web search results.
"""
        )
        
        print(f"✓ Conversation created: {self.conversation_id}\n")
        
    async def cleanup(self):
        """Cleanup services."""
        if self.db_manager:
            self.db_manager.close()
            print("\n✓ Database closed")
            
    def _should_use_web_search(self, prompt: str) -> bool:
        """Determine if prompt requires web search."""
        # Keywords that indicate need for current/external information
        web_keywords = [
            "current", "latest", "recent", "today", "2025",
            "real-time", "news", "research", "study", "paper"
        ]
        return any(keyword in prompt.lower() for keyword in web_keywords)
        
    async def _enhance_prompt_with_search(self, prompt: str) -> str:
        """Enhance prompt with web search results if needed."""
        if not self._should_use_web_search(prompt):
            return prompt
            
        print("  → Performing web search...")
        search_results = await self.web_search.search(prompt)
        
        if not search_results:
            return prompt
            
        # Append search results to prompt
        enhanced = f"{prompt}\n\n[Web Search Results]:\n"
        for i, result in enumerate(search_results, 1):
            enhanced += f"{i}. {result['title']}\n   {result['snippet']}\n"
            
        return enhanced
        
    async def run_prompt(self, section: str, prompt: str, index: int, total: int) -> Dict:
        """Execute a single prompt and save to memory."""
        print(f"\n[{index}/{total}] {section}")
        print(f"Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        
        try:
            # Enhance with web search if needed
            enhanced_prompt = await self._enhance_prompt_with_search(prompt)
            
            # Send to ASTRA
            start_time = datetime.utcnow()
            response = await self.chat_service.chat(
                conversation_id=self.conversation_id,
                user_message=enhanced_prompt,
                use_memory=True  # Enable memory storage
            )
            end_time = datetime.utcnow()
            
            # Calculate metrics
            response_time = (end_time - start_time).total_seconds()
            response_length = len(response.content)
            
            result = {
                "section": section,
                "prompt": prompt,
                "response": response.content,
                "response_time_seconds": response_time,
                "response_length": response_length,
                "model_name": response.model,
                "timestamp": start_time.isoformat(),
                "message_id": response.id,
                "conversation_id": self.conversation_id,
                "web_search_used": enhanced_prompt != prompt
            }
            
            print(f"✓ Response received ({response_length} chars, {response_time:.2f}s)")
            print(f"  Preview: {response.content[:100]}...")
            
            self.completed_prompts += 1
            return result
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            return {
                "section": section,
                "prompt": prompt,
                "response": None,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def run_all_prompts(self):
        """Execute all Soul Juicer prompts."""
        print("=" * 80)
        print("SOUL JUICER PROTOCOL TEST")
        print("=" * 80)
        print(f"Conversation ID: {self.conversation_id}")
        print(f"Model: {self.settings.llm.model}")
        print(f"Reasoning Mode: {self.settings.llm.reasoning_mode}")
        print(f"Harmony Format: {self.settings.llm.use_harmony_format}")
        print(f"Web Search: {'Enabled' if self.web_search.enabled else 'Disabled'}")
        print("=" * 80)
        
        # Count total prompts
        self.total_prompts = sum(len(prompts) for prompts in SOUL_JUICER_PROMPTS.values())
        
        current_index = 1
        
        # Execute each section
        for section, prompts in SOUL_JUICER_PROMPTS.items():
            print(f"\n{'=' * 80}")
            print(f"{section} ({len(prompts)} prompts)")
            print(f"{'=' * 80}")
            
            for prompt in prompts:
                result = await self.run_prompt(
                    section=section,
                    prompt=prompt,
                    index=current_index,
                    total=self.total_prompts
                )
                self.results.append(result)
                current_index += 1
                
                # Brief pause between prompts
                await asyncio.sleep(0.5)
                
    def save_results(self, output_path: str = "soul_juicer_results.json"):
        """Save test results to file."""
        output_file = Path(__file__).parent.parent / output_path
        
        report = {
            "test_name": "Soul Juicer Protocol",
            "conversation_id": self.conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": {
                "model": self.settings.llm.model,
                "reasoning_mode": self.settings.llm.reasoning_mode,
                "use_harmony_format": self.settings.llm.use_harmony_format,
                "temperature": self.settings.llm.temperature,
                "web_search_enabled": self.web_search.enabled
            },
            "statistics": {
                "total_prompts": self.total_prompts,
                "completed_prompts": self.completed_prompts,
                "failed_prompts": self.total_prompts - self.completed_prompts,
                "total_response_chars": sum(r.get("response_length", 0) for r in self.results),
                "average_response_time": sum(r.get("response_time_seconds", 0) for r in self.results) / len(self.results) if self.results else 0,
                "web_searches_performed": sum(1 for r in self.results if r.get("web_search_used", False))
            },
            "results": self.results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n✓ Results saved to: {output_file}")
        return output_file
        
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        successful = [r for r in self.results if r.get("response")]
        failed = [r for r in self.results if r.get("error")]
        
        print(f"Total Prompts: {self.total_prompts}")
        print(f"Completed: {len(successful)} ({len(successful)/self.total_prompts*100:.1f}%)")
        print(f"Failed: {len(failed)} ({len(failed)/self.total_prompts*100:.1f}%)")
        
        if successful:
            total_chars = sum(r["response_length"] for r in successful)
            avg_time = sum(r["response_time_seconds"] for r in successful) / len(successful)
            
            print(f"\nResponse Statistics:")
            print(f"  Total characters: {total_chars:,}")
            print(f"  Average response time: {avg_time:.2f}s")
            print(f"  Average response length: {total_chars // len(successful):,} chars")
            
        # Section breakdown
        print(f"\nBy Section:")
        for section in SOUL_JUICER_PROMPTS.keys():
            section_results = [r for r in self.results if r["section"] == section]
            section_success = [r for r in section_results if r.get("response")]
            print(f"  {section}: {len(section_success)}/{len(section_results)}")
            
        print("=" * 80)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Run Soul Juicer Protocol test."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Soul Juicer Protocol test")
    parser.add_argument(
        "--conversation-id",
        default=f"soul-juicer-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        help="Conversation ID for test"
    )
    parser.add_argument(
        "--output",
        default="soul_juicer_results.json",
        help="Output file for results"
    )
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="Disable web search"
    )
    
    args = parser.parse_args()
    
    # Create test instance
    test = SoulJuicerTest(conversation_id=args.conversation_id)
    
    if args.no_web_search:
        test.web_search.enabled = False
    
    try:
        # Initialize services
        await test.initialize()
        
        # Run all prompts
        await test.run_all_prompts()
        
        # Print summary
        test.print_summary()
        
        # Save results
        output_file = test.save_results(args.output)
        
        print(f"\n✓ Soul Juicer Protocol test completed!")
        print(f"✓ All interactions saved to ASTRA memory")
        print(f"✓ Results saved to: {output_file}")
        print(f"\nConversation ID: {test.conversation_id}")
        print("You can continue this conversation using the ASTRA API.")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await test.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
