"""
Soul Juicer Protocol - Live ASTRA Test Runner
==============================================

This script runs the Soul Juicer Protocol test by directly launching ASTRA
and asking all 36 questions one by one, saving responses to memory.

Usage:
    python scripts/run_soul_juicer_live.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from astra.models.config import get_settings
from astra.api.app import create_app
from astra.infrastructure.storage.database import DatabaseManager
from astra.infrastructure.storage.vector_store import VectorStore
from astra.services.conversation_service import ConversationService
from astra.services.memory_service import MemoryService
from astra.infrastructure.llm.factory import create_llm_provider
from astra.services.chat_service import ChatService

# Soul Juicer Protocol - 36 Enhanced Prompts
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


class LiveSoulJuicerTest:
    """Execute Soul Juicer Protocol test with live ASTRA."""
    
    def __init__(self):
        self.settings = get_settings()
        self.conversation_id = None
        self.results = []
        self.total_prompts = 0
        self.completed_prompts = 0
        
        # Services
        self.db_manager = None
        self.vector_store = None
        self.conversation_service = None
        self.memory_service = None
        self.llm_provider = None
        self.chat_service = None
        
    def initialize_services(self):
        """Initialize all ASTRA services."""
        print("\n" + "=" * 80)
        print("INITIALIZING ASTRA")
        print("=" * 80)
        
        try:
            # Database
            print("Initializing database...")
            # DatabaseManager expects a full SQLAlchemy URL, not just a path
            self.db_manager = DatabaseManager(self.settings.database.url)
            print("✓ Database manager initialized")
            
            # Vector store
            print("Initializing vector store...")
            self.vector_store = VectorStore(
                persist_directory=self.settings.vector_store.persist_directory
            )
            print("✓ Vector store initialized")
            
            # Services
            print("Initializing services...")
            self.conversation_service = ConversationService(self.db_manager)
            self.memory_service = MemoryService(self.vector_store)
            print("✓ Conversation and memory services ready")
            
            # LLM Provider
            print("Initializing LLM provider...")
            self.llm_provider = create_llm_provider(self.settings)
            print(f"✓ LLM provider created: {type(self.llm_provider).__name__}")
            
            # Chat service
            print("Initializing chat service...")
            self.chat_service = ChatService(
                settings=self.settings,
                conversation_service=self.conversation_service,
                memory_service=self.memory_service,
            )
            print("✓ Chat service ready")
            
            print("\n" + "=" * 80)
            print("ASTRA INITIALIZATION COMPLETE")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n✗ Initialization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def create_conversation(self):
        """Create a new conversation for the test."""
        print("\nCreating Soul Juicer Protocol conversation...")
        
        # Create conversation
        self.conversation_id = self.conversation_service.create_conversation(
            title="Soul Juicer Protocol - Live Test"
        )
        
        # Add system message
        system_prompt = """You are ASTRA, an advanced AI assistant designed for deep reasoning and creative intelligence.

You are participating in the Soul Juicer Protocol - a comprehensive test of AI capabilities across multiple domains:
- Meta-reasoning and self-awareness
- Hyper-reasoning and logic
- Domain mastery across fields
- Instruction following
- Creative intelligence
- Self-interrogation
- Cosmic awareness

Be authentic, thorough, and creative in your responses. Push the boundaries of what's possible.
Show your deepest understanding and most creative thinking."""
        
        self.conversation_service.add_message(
            conversation_id=self.conversation_id,
            role="system",
            content=system_prompt
        )
        
        # Note: System prompt not stored in vector memory (ChromaDB metadata issue)
        # Regular conversation messages will still be stored
        
        print(f"✓ Conversation created: {self.conversation_id}")
        print(f"✓ System prompt configured")
        
    async def ask_question(self, section: str, prompt: str, index: int, total: int):
        """Ask a single question to ASTRA and save response."""
        print(f"\n{'=' * 80}")
        print(f"[{index}/{total}] {section}")
        print(f"{'=' * 80}")
        print(f"Question: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")
        print(f"\nAsking ASTRA...")
        
        start_time = datetime.utcnow()
        
        try:
            # Send message through chat service
            response = await self.chat_service.chat(
                conversation_id=self.conversation_id,
                user_message=prompt,
                use_memory=True
            )
            
            end_time = datetime.utcnow()
            response_time = (end_time - start_time).total_seconds()
            
            # Print response
            print(f"\n✓ ASTRA responded ({len(response.content)} chars, {response_time:.2f}s)")
            print(f"\n{'-' * 80}")
            print(f"ASTRA's Response:")
            print(f"{'-' * 80}")
            print(response.content)
            print(f"{'-' * 80}")
            
            # Save result
            result = {
                "section": section,
                "prompt": prompt,
                "response": response.content,
                "response_time_seconds": response_time,
                "response_length": len(response.content),
                "timestamp": start_time.isoformat(),
                "conversation_id": self.conversation_id
            }
            
            self.results.append(result)
            self.completed_prompts += 1
            
            # Brief pause between questions
            await asyncio.sleep(0.5)
            
            return result
            
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "section": section,
                "prompt": prompt,
                "response": None,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_all_questions(self):
        """Execute all Soul Juicer prompts."""
        print("\n" + "=" * 80)
        print("SOUL JUICER PROTOCOL - LIVE TEST")
        print("=" * 80)
        print(f"Conversation ID: {self.conversation_id}")
        print(f"LLM Provider: {type(self.llm_provider).__name__}")
        print(f"Reasoning Mode: {self.settings.llm.reasoning_mode}")
        print(f"Harmony Format: {self.settings.llm.use_harmony_format}")
        print("=" * 80)
        
        # Count total prompts
        self.total_prompts = sum(len(prompts) for prompts in SOUL_JUICER_PROMPTS.values())
        print(f"\nTotal questions to ask: {self.total_prompts}")
        
        current_index = 1
        
        # Execute each section
        for section, prompts in SOUL_JUICER_PROMPTS.items():
            print(f"\n\n{'#' * 80}")
            print(f"# {section} ({len(prompts)} questions)")
            print(f"{'#' * 80}")
            
            for prompt in prompts:
                await self.ask_question(
                    section=section,
                    prompt=prompt,
                    index=current_index,
                    total=self.total_prompts
                )
                current_index += 1
    
    def save_results(self, output_path: str = "soul_juicer_live_results.json"):
        """Save test results to file."""
        output_file = Path(__file__).parent.parent / output_path
        
        report = {
            "test_name": "Soul Juicer Protocol - Live Test",
            "conversation_id": self.conversation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": {
                "reasoning_mode": self.settings.llm.reasoning_mode,
                "use_harmony_format": self.settings.llm.use_harmony_format,
                "temperature": self.settings.llm.temperature,
                "llm_provider": type(self.llm_provider).__name__
            },
            "statistics": {
                "total_prompts": self.total_prompts,
                "completed_prompts": self.completed_prompts,
                "failed_prompts": self.total_prompts - self.completed_prompts,
                "total_response_chars": sum(r.get("response_length", 0) for r in self.results if r.get("response")),
                "average_response_time": sum(r.get("response_time_seconds", 0) for r in self.results if r.get("response")) / len([r for r in self.results if r.get("response")]) if self.results else 0
            },
            "results": self.results
        }
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n✓ Results saved to: {output_file}")
        return output_file
    
    def print_summary(self):
        """Print test summary."""
        successful = [r for r in self.results if r.get("response")]
        failed = [r for r in self.results if r.get("error")]
        
        print("\n\n" + "=" * 80)
        print("SOUL JUICER PROTOCOL - TEST COMPLETE")
        print("=" * 80)
        print(f"\nTotal Questions: {self.total_prompts}")
        print(f"Completed: {len(successful)} ({len(successful)/self.total_prompts*100:.1f}%)")
        print(f"Failed: {len(failed)} ({len(failed)/self.total_prompts*100:.1f}%)")
        
        if successful:
            total_chars = sum(r["response_length"] for r in successful)
            avg_time = sum(r["response_time_seconds"] for r in successful) / len(successful)
            
            print(f"\n📊 Response Statistics:")
            print(f"   Total characters: {total_chars:,}")
            print(f"   Average response time: {avg_time:.2f}s")
            print(f"   Average response length: {total_chars // len(successful):,} chars")
            
        # Section breakdown
        print(f"\n📋 By Section:")
        for section in SOUL_JUICER_PROMPTS.keys():
            section_results = [r for r in self.results if r["section"] == section]
            section_success = [r for r in section_results if r.get("response")]
            print(f"   {section}: {len(section_success)}/{len(section_results)}")
            
        print("\n✓ All interactions saved to ASTRA memory (database + vector store)")
        print(f"✓ Conversation ID: {self.conversation_id}")
        print("=" * 80)
    
    def cleanup(self):
        """Cleanup services."""
        if self.db_manager:
            self.db_manager.close()
            print("\n✓ Database closed")


async def main():
    """Main execution."""
    test = LiveSoulJuicerTest()
    
    try:
        # Initialize ASTRA
        test.initialize_services()
        
        # Create conversation
        test.create_conversation()
        
        # Run all questions
        await test.run_all_questions()
        
        # Print summary
        test.print_summary()
        
        # Save results
        test.save_results()
        
        print("\n🎉 Soul Juicer Protocol completed successfully!")
        print("🎉 All questions asked, all answers saved to ASTRA's memory!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        test.cleanup()


if __name__ == "__main__":
    print("\n" + "🚀" * 40)
    print("LAUNCHING ASTRA - SOUL JUICER PROTOCOL LIVE TEST")
    print("🚀" * 40)
    asyncio.run(main())
