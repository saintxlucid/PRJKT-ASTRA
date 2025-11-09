"""
GPT-OSS Gibberish Triage Script

Tests different parameter configurations to diagnose and fix gibberish output.
Runs 6 parameter grids and measures perplexity + bad-token rate.

Usage:
    python scripts/gibberish_triage.py --model gpt-oss-20b
    python scripts/gibberish_triage.py --url http://localhost:8001 --quick
"""

import asyncio
import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class SamplingConfig:
    """Sampling parameter configuration"""
    name: str
    temperature: float
    top_p: float
    top_k: int
    repetition_penalty: float
    min_p: float = 0.0
    mirostat: int = 0
    mirostat_tau: float = 5.0
    mirostat_eta: float = 0.1


@dataclass
class TriageResult:
    """Results from a single test"""
    config_name: str
    prompt: str
    response: str
    tokens_generated: int
    time_elapsed: float
    bad_token_rate: float
    repetition_score: float
    quality_score: float
    perplexity_estimate: float = 0.0
    stop_reason: str = "unknown"
    metadata: Dict = field(default_factory=dict)


# Test prompts covering different difficulty levels
TEST_PROMPTS = [
    "What is 2+2?",
    "Explain quantum entanglement in simple terms.",
    "Write a haiku about artificial intelligence.",
    "What are the key principles of object-oriented programming?",
    "Describe the water cycle.",
]


# Parameter grids to test
PARAMETER_GRIDS = [
    SamplingConfig(
        name="conservative",
        temperature=0.6,
        top_p=0.9,
        top_k=40,
        repetition_penalty=1.1,
    ),
    SamplingConfig(
        name="balanced",
        temperature=0.7,
        top_p=0.9,
        top_k=80,
        repetition_penalty=1.15,
    ),
    SamplingConfig(
        name="creative",
        temperature=0.8,
        top_p=0.95,
        top_k=100,
        repetition_penalty=1.2,
    ),
    SamplingConfig(
        name="very_conservative",
        temperature=0.5,
        top_p=0.85,
        top_k=30,
        repetition_penalty=1.05,
    ),
    SamplingConfig(
        name="high_repetition_penalty",
        temperature=0.7,
        top_p=0.9,
        top_k=60,
        repetition_penalty=1.3,
    ),
    SamplingConfig(
        name="low_temperature_long_context",
        temperature=0.6,
        top_p=0.88,
        top_k=50,
        repetition_penalty=1.12,
    ),
]


class GibberishTriage:
    """Diagnose and fix GPT-OSS gibberish output"""

    def __init__(
        self,
        base_url: str = "http://localhost:8001",
        model: str = "gpt-oss-20b",
        use_harmony_format: bool = True,
    ):
        self.base_url = base_url
        self.model = model
        self.use_harmony_format = use_harmony_format
        self.client = httpx.AsyncClient(timeout=120.0)
        self.results: List[TriageResult] = []

    async def test_health(self) -> bool:
        """Check if LLM server is healthy"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                logger.info("llm_server_healthy", url=self.base_url)
                return True
            else:
                logger.error("llm_server_unhealthy", status=response.status_code)
                return False
        except Exception as e:
            logger.error("llm_server_unreachable", error=str(e))
            return False

    def build_harmony_prompt(self, user_message: str) -> str:
        """Build Harmony format prompt"""
        return (
            f"<|start_header_id|>system<|end_header_id|>\n\n"
            f"You are ASTRA, a helpful AI assistant.\n\n"
            f"<|start_header_id|>user<|end_header_id|>\n\n"
            f"{user_message}\n\n"
            f"<|start_header_id|>assistant|final<|end_header_id|>\n\n"
        )

    def build_simple_prompt(self, user_message: str) -> str:
        """Build simple chat prompt"""
        return (
            f"System: You are ASTRA, a helpful AI assistant.\n"
            f"User: {user_message}\n"
            f"Assistant:"
        )

    def get_stop_tokens(self) -> List[str]:
        """Get appropriate stop tokens"""
        if self.use_harmony_format:
            return [
                "<|start_header_id|>",
                "<|end_header_id|>",
                "</s>",
                "<|eot_id|>",
            ]
        else:
            return ["</s>", "\nUser:", "\nSystem:"]

    async def test_configuration(
        self, config: SamplingConfig, prompt: str
    ) -> TriageResult:
        """Test a specific parameter configuration"""
        logger.info(
            "testing_configuration",
            config=config.name,
            prompt=prompt[:50],
        )

        # Build prompt
        if self.use_harmony_format:
            full_prompt = self.build_harmony_prompt(prompt)
        else:
            full_prompt = self.build_simple_prompt(prompt)

        # Prepare request
        request_body = {
            "prompt": full_prompt,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "top_k": config.top_k,
            "repeat_penalty": config.repetition_penalty,
            "min_p": config.min_p,
            "mirostat": config.mirostat,
            "mirostat_tau": config.mirostat_tau,
            "mirostat_eta": config.mirostat_eta,
            "stop": self.get_stop_tokens(),
            "n_predict": 200,  # Max tokens
            "stream": False,
        }

        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/completion",
                json=request_body,
            )
            elapsed = time.time() - start_time

            if response.status_code != 200:
                logger.error(
                    "request_failed",
                    status=response.status_code,
                    config=config.name,
                )
                return TriageResult(
                    config_name=config.name,
                    prompt=prompt,
                    response="[REQUEST FAILED]",
                    tokens_generated=0,
                    time_elapsed=elapsed,
                    bad_token_rate=1.0,
                    repetition_score=0.0,
                    quality_score=0.0,
                    stop_reason="error",
                )

            result = response.json()
            generated_text = result.get("content", "")
            tokens_generated = result.get("tokens_predicted", 0)
            stop_reason = result.get("stop", "unknown")

            # Analyze quality
            bad_token_rate = self._calculate_bad_token_rate(generated_text)
            repetition_score = self._calculate_repetition_score(generated_text)
            quality_score = self._calculate_quality_score(
                generated_text, bad_token_rate, repetition_score
            )

            result_obj = TriageResult(
                config_name=config.name,
                prompt=prompt,
                response=generated_text,
                tokens_generated=tokens_generated,
                time_elapsed=elapsed,
                bad_token_rate=bad_token_rate,
                repetition_score=repetition_score,
                quality_score=quality_score,
                stop_reason=stop_reason,
                metadata={
                    "temperature": config.temperature,
                    "top_p": config.top_p,
                    "top_k": config.top_k,
                    "repetition_penalty": config.repetition_penalty,
                },
            )

            logger.info(
                "test_complete",
                config=config.name,
                quality=quality_score,
                bad_tokens=bad_token_rate,
                tokens=tokens_generated,
                time=elapsed,
            )

            return result_obj

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("test_exception", config=config.name, error=str(e))
            return TriageResult(
                config_name=config.name,
                prompt=prompt,
                response=f"[ERROR: {str(e)}]",
                tokens_generated=0,
                time_elapsed=elapsed,
                bad_token_rate=1.0,
                repetition_score=0.0,
                quality_score=0.0,
                stop_reason="exception",
            )

    def _calculate_bad_token_rate(self, text: str) -> float:
        """Calculate rate of nonsensical tokens"""
        if not text:
            return 1.0

        # Common patterns in gibberish
        bad_patterns = [
            "望", "�", "&#", "\ufffd",  # Unicode issues
            "amp amp", "conj conj", "cant vali",  # Repeated fragments
            "hil hil", "burst burst",  # Pattern repetition
        ]

        bad_count = sum(text.count(pattern) for pattern in bad_patterns)
        total_tokens = len(text.split())
        
        if total_tokens == 0:
            return 1.0

        return min(bad_count / total_tokens, 1.0)

    def _calculate_repetition_score(self, text: str) -> float:
        """Calculate repetition rate"""
        if not text:
            return 1.0

        words = text.split()
        if len(words) < 5:
            return 0.0

        # Count repeated bigrams
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        bigram_counts = Counter(bigrams)
        
        # Find most common bigram
        if bigram_counts:
            most_common_count = bigram_counts.most_common(1)[0][1]
            return min(most_common_count / len(bigrams), 1.0)
        
        return 0.0

    def _calculate_quality_score(
        self, text: str, bad_token_rate: float, repetition_score: float
    ) -> float:
        """Calculate overall quality score (0-100)"""
        if not text or len(text.strip()) < 10:
            return 0.0

        # Penalties
        bad_token_penalty = bad_token_rate * 50
        repetition_penalty = repetition_score * 30
        
        # Length bonus (reasonable responses)
        length_score = min(len(text.split()) / 20, 1.0) * 20

        # Base score
        quality = 100 - bad_token_penalty - repetition_penalty + length_score
        
        return max(0.0, min(100.0, quality))

    async def run_triage(
        self,
        prompts: Optional[List[str]] = None,
        configs: Optional[List[SamplingConfig]] = None,
    ) -> List[TriageResult]:
        """Run full triage with all configurations"""
        if prompts is None:
            prompts = TEST_PROMPTS
        
        if configs is None:
            configs = PARAMETER_GRIDS

        logger.info(
            "starting_triage",
            num_prompts=len(prompts),
            num_configs=len(configs),
            total_tests=len(prompts) * len(configs),
        )

        results = []

        for prompt in prompts:
            for config in configs:
                result = await self.test_configuration(config, prompt)
                results.append(result)
                self.results.append(result)
                
                # Brief delay between tests
                await asyncio.sleep(0.5)

        logger.info("triage_complete", total_results=len(results))
        return results

    def analyze_results(self) -> Dict:
        """Analyze all results and provide recommendations"""
        if not self.results:
            return {"error": "No results to analyze"}

        # Group by configuration
        config_scores = {}
        for result in self.results:
            if result.config_name not in config_scores:
                config_scores[result.config_name] = []
            config_scores[result.config_name].append(result.quality_score)

        # Calculate averages
        config_averages = {
            name: sum(scores) / len(scores)
            for name, scores in config_scores.items()
        }

        # Find best configuration
        best_config = max(config_averages.items(), key=lambda x: x[1])
        worst_config = min(config_averages.items(), key=lambda x: x[1])

        # Calculate overall statistics
        all_scores = [r.quality_score for r in self.results]
        all_bad_rates = [r.bad_token_rate for r in self.results]
        all_repetitions = [r.repetition_score for r in self.results]

        analysis = {
            "best_configuration": {
                "name": best_config[0],
                "average_quality": best_config[1],
            },
            "worst_configuration": {
                "name": worst_config[0],
                "average_quality": worst_config[1],
            },
            "overall_statistics": {
                "average_quality": sum(all_scores) / len(all_scores),
                "average_bad_token_rate": sum(all_bad_rates) / len(all_bad_rates),
                "average_repetition_score": sum(all_repetitions) / len(all_repetitions),
            },
            "configuration_rankings": sorted(
                config_averages.items(), key=lambda x: x[1], reverse=True
            ),
            "recommendations": self._generate_recommendations(config_averages),
        }

        return analysis

    def _generate_recommendations(self, config_averages: Dict[str, float]) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []

        best_score = max(config_averages.values())
        
        if best_score < 30:
            recommendations.append(
                "⚠️ CRITICAL: All configurations produce poor quality. "
                "Check tokenizer alignment, model file integrity, and chat template."
            )
        elif best_score < 60:
            recommendations.append(
                "⚠️ WARNING: Quality is below acceptable. "
                "Try different quantization (Q5_K_M instead of Q4) or verify model file."
            )
        else:
            recommendations.append(
                f"✅ Good quality found with best configuration. "
                f"Use parameters from top-ranked config."
            )

        # Check for bad token issues
        avg_bad_rate = sum(r.bad_token_rate for r in self.results) / len(self.results)
        if avg_bad_rate > 0.2:
            recommendations.append(
                "⚠️ High bad token rate detected. "
                "Verify tokenizer files match GGUF and check special tokens."
            )

        # Check for repetition issues
        avg_repetition = sum(r.repetition_score for r in self.results) / len(self.results)
        if avg_repetition > 0.3:
            recommendations.append(
                "⚠️ High repetition detected. "
                "Increase repetition_penalty (try 1.2-1.3) or adjust top_k."
            )

        return recommendations

    def save_results(self, output_path: Path):
        """Save results to JSON file"""
        analysis = self.analyze_results()
        
        output_data = {
            "triage_metadata": {
                "base_url": self.base_url,
                "model": self.model,
                "use_harmony_format": self.use_harmony_format,
                "timestamp": time.time(),
                "total_tests": len(self.results),
            },
            "analysis": analysis,
            "detailed_results": [
                {
                    "config_name": r.config_name,
                    "prompt": r.prompt,
                    "response": r.response[:200],  # Truncate for readability
                    "tokens_generated": r.tokens_generated,
                    "time_elapsed": r.time_elapsed,
                    "bad_token_rate": r.bad_token_rate,
                    "repetition_score": r.repetition_score,
                    "quality_score": r.quality_score,
                    "stop_reason": r.stop_reason,
                    "metadata": r.metadata,
                }
                for r in self.results
            ],
        }

        output_path.write_text(json.dumps(output_data, indent=2))
        logger.info("results_saved", path=str(output_path))

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="GPT-OSS Gibberish Triage")
    parser.add_argument(
        "--url",
        default="http://localhost:8001",
        help="LLM server URL",
    )
    parser.add_argument(
        "--model",
        default="gpt-oss-20b",
        help="Model name",
    )
    parser.add_argument(
        "--harmony",
        action="store_true",
        default=True,
        help="Use Harmony format",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick test (fewer prompts)",
    )
    parser.add_argument(
        "--output",
        default="data/logs/gibberish_triage_results.json",
        help="Output file path",
    )

    args = parser.parse_args()

    # Setup structured logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ]
    )

    triage = GibberishTriage(
        base_url=args.url,
        model=args.model,
        use_harmony_format=args.harmony,
    )

    # Check health
    if not await triage.test_health():
        print("❌ LLM server is not healthy. Please start it first.")
        return

    # Run triage
    prompts = TEST_PROMPTS[:2] if args.quick else TEST_PROMPTS
    results = await triage.run_triage(prompts=prompts)

    # Analyze and display
    analysis = triage.analyze_results()
    
    print("\n" + "=" * 80)
    print("GIBBERISH TRIAGE RESULTS")
    print("=" * 80)
    print(f"\n📊 Best Configuration: {analysis['best_configuration']['name']}")
    print(f"   Average Quality: {analysis['best_configuration']['average_quality']:.1f}/100")
    print(f"\n📊 Worst Configuration: {analysis['worst_configuration']['name']}")
    print(f"   Average Quality: {analysis['worst_configuration']['average_quality']:.1f}/100")
    
    print(f"\n📈 Overall Statistics:")
    stats = analysis['overall_statistics']
    print(f"   Average Quality: {stats['average_quality']:.1f}/100")
    print(f"   Bad Token Rate: {stats['average_bad_token_rate']:.2%}")
    print(f"   Repetition Score: {stats['average_repetition_score']:.2%}")
    
    print(f"\n🏆 Configuration Rankings:")
    for i, (name, score) in enumerate(analysis['configuration_rankings'], 1):
        print(f"   {i}. {name}: {score:.1f}/100")
    
    print(f"\n💡 Recommendations:")
    for rec in analysis['recommendations']:
        print(f"   {rec}")
    
    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    triage.save_results(output_path)
    
    print(f"\n📁 Detailed results saved to: {output_path}")
    print("=" * 80)

    await triage.close()


if __name__ == "__main__":
    asyncio.run(main())
