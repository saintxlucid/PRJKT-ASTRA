"""
Phase 5: Quantum Intent Resolution

Implements superposition-based intent detection where multiple interpretations
coexist until observation (execution) collapses to a single intent.

Key Concepts:
- IntentSuperposition: Multiple possible interpretations with probabilities
- ConfidenceScoring: Probabilistic operator selection
- IntentCollapse: Observation collapses superposition to single intent
- Ambiguity Detection: Identifies when clarification needed
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(Enum):
    """Types of user intents."""

    QUERY = "query"  # Information retrieval
    COMMAND = "command"  # Action execution
    CLARIFICATION = "clarification"  # Resolve ambiguity
    STATEMENT = "statement"  # Information provision
    QUESTION = "question"  # Seeking information
    INSTRUCTION = "instruction"  # Step-by-step guidance
    UNKNOWN = "unknown"  # Cannot determine


class IntentDomain(Enum):
    """Domain categories for intent classification."""

    CODE = "code"  # Programming/development
    FILE = "file"  # File operations
    SEARCH = "search"  # Information search
    ANALYSIS = "analysis"  # Data/code analysis
    GENERATION = "generation"  # Content creation
    MANIPULATION = "manipulation"  # Editing/refactoring
    TESTING = "testing"  # Test execution/validation
    DOCUMENTATION = "documentation"  # Docs reading/writing
    SYSTEM = "system"  # System operations
    CONVERSATION = "conversation"  # General chat
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """A single interpretation of user input."""

    intent_type: IntentType
    domain: IntentDomain
    action: str  # Verb describing the action (e.g., "search", "create", "analyze")
    entities: dict[str, Any]  # Extracted entities (files, patterns, parameters)
    raw_text: str  # Original user input
    confidence: float = 0.0  # Probability this interpretation is correct [0-1]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate confidence is in [0, 1]."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be in [0, 1], got {self.confidence}")


@dataclass
class IntentSuperposition:
    """
    Multiple coexisting intent interpretations (quantum superposition).

    All interpretations exist simultaneously with their probabilities
    until observation (execution) collapses to a single intent.
    """

    intents: list[Intent]  # All possible interpretations
    raw_text: str  # Original user input
    collapsed: bool = False  # Whether superposition has collapsed
    chosen_intent: Intent | None = None  # Result after collapse

    def __post_init__(self) -> None:
        """Normalize probabilities to sum to 1.0."""
        if not self.intents:
            raise ValueError("IntentSuperposition requires at least one intent")

        # Normalize confidence scores to sum to 1.0
        total_confidence = sum(i.confidence for i in self.intents)
        if total_confidence > 0:
            for intent in self.intents:
                intent.confidence /= total_confidence
        else:
            # Equal probabilities if all confidences are 0
            uniform_prob = 1.0 / len(self.intents)
            for intent in self.intents:
                intent.confidence = uniform_prob

    def collapse(self, observation: str | None = None) -> Intent:
        """
        Collapse superposition to single intent (quantum measurement).

        Args:
            observation: Optional context that influences collapse (e.g., execution result)

        Returns:
            The chosen intent after collapse
        """
        if self.collapsed:
            return self.chosen_intent  # type: ignore

        # Select intent with highest confidence
        # In quantum mechanics, observation determines outcome probabilistically
        # Here we use greedy selection (highest probability)
        self.chosen_intent = max(self.intents, key=lambda i: i.confidence)
        self.collapsed = True

        return self.chosen_intent

    def top_k(self, k: int = 3) -> list[Intent]:
        """Get top-k most probable intents."""
        return sorted(self.intents, key=lambda i: i.confidence, reverse=True)[:k]

    def is_ambiguous(self, threshold: float = 0.3) -> bool:
        """
        Check if intents are ambiguous.

        Ambiguous when multiple intents have similar high probabilities.

        Args:
            threshold: Maximum confidence difference for ambiguity

        Returns:
            True if top 2 intents are within threshold
        """
        if len(self.intents) < 2:
            return False

        sorted_intents = sorted(self.intents, key=lambda i: i.confidence, reverse=True)
        top_confidence = sorted_intents[0].confidence
        second_confidence = sorted_intents[1].confidence

        return (top_confidence - second_confidence) < threshold

    def entropy(self) -> float:
        """
        Calculate Shannon entropy of intent distribution.

        Higher entropy = more uncertainty/ambiguity.
        Lower entropy = more certainty.

        Returns:
            Entropy in nats (natural units)
        """
        entropy_val = 0.0
        for intent in self.intents:
            if intent.confidence > 0:
                entropy_val -= intent.confidence * math.log(intent.confidence)
        return entropy_val


class IntentResolver:
    """
    Resolves user input into probabilistic intent superposition.

    Implements quantum-inspired intent detection where multiple interpretations
    coexist until execution observation collapses to single intent.
    """

    def __init__(self) -> None:
        """Initialize intent resolver with pattern matchers."""
        self._action_patterns = self._build_action_patterns()
        self._domain_patterns = self._build_domain_patterns()

    def _build_action_patterns(self) -> dict[str, list[str]]:
        """Build regex patterns for action detection."""
        return {
            "search": [r"\b(find|search|look\s+for|grep|locate)\b"],
            "create": [r"\b(create|make|generate|build|add|new)\b"],
            "edit": [r"\b(edit|modify|change|update|fix|refactor)\b"],
            "delete": [r"\b(delete|remove|clean|clear)\b"],
            "read": [r"\b(read|show|display|view|open|check)\b"],
            "analyze": [r"\b(analyze|examine|inspect|review|understand)\b"],
            "run": [r"\b(run|execute|test|start|launch)\b"],
            "explain": [r"\b(explain|describe|what\s+is|how\s+does|tell\s+me)\b"],
            "list": [r"\b(list|show\s+all|enumerate)\b"],
            "compare": [r"\b(compare|diff|difference)\b"],
        }

    def _build_domain_patterns(self) -> dict[IntentDomain, list[str]]:
        """Build regex patterns for domain detection."""
        return {
            IntentDomain.CODE: [
                r"\b(function|class|method|variable|code|implement|algorithm)\b",
                r"\b(python|javascript|typescript|rust|go)\b",
            ],
            IntentDomain.FILE: [
                r"\b(file|folder|directory|path)\b",
                r"\.(py|js|ts|md|txt|json|yaml|toml)\b",
            ],
            IntentDomain.SEARCH: [
                r"\b(find|search|grep|locate|where)\b",
            ],
            IntentDomain.ANALYSIS: [
                r"\b(analyze|examine|understand|explain|how|why)\b",
            ],
            IntentDomain.GENERATION: [
                r"\b(create|generate|write|build|make)\b",
            ],
            IntentDomain.TESTING: [
                r"\b(test|pytest|unittest|coverage|validate)\b",
            ],
            IntentDomain.DOCUMENTATION: [
                r"\b(docs|documentation|readme|comment|docstring)\b",
            ],
        }

    def resolve(self, user_input: str) -> IntentSuperposition:
        """
        Resolve user input into intent superposition.

        Args:
            user_input: Natural language user request

        Returns:
            IntentSuperposition with multiple possible interpretations
        """
        user_input = user_input.strip()
        if not user_input:
            return IntentSuperposition(
                intents=[
                    Intent(
                        intent_type=IntentType.UNKNOWN,
                        domain=IntentDomain.UNKNOWN,
                        action="unknown",
                        entities={},
                        raw_text=user_input,
                        confidence=1.0,
                    )
                ],
                raw_text=user_input,
            )

        # Generate multiple interpretations
        intents = []

        # Parse as query
        query_intent = self._parse_as_query(user_input)
        if query_intent:
            intents.append(query_intent)

        # Parse as command
        command_intent = self._parse_as_command(user_input)
        if command_intent:
            intents.append(command_intent)

        # Parse as question
        question_intent = self._parse_as_question(user_input)
        if question_intent:
            intents.append(question_intent)

        # If no interpretations, create unknown intent
        if not intents:
            intents.append(
                Intent(
                    intent_type=IntentType.UNKNOWN,
                    domain=IntentDomain.CONVERSATION,
                    action="converse",
                    entities={},
                    raw_text=user_input,
                    confidence=1.0,
                )
            )

        return IntentSuperposition(intents=intents, raw_text=user_input)

    def _parse_as_query(self, text: str) -> Intent | None:
        """Parse text as information query."""
        # Detect query indicators
        query_indicators = [
            r"\bwhat\b",
            r"\bwhere\b",
            r"\bwhen\b",
            r"\bshow\b",
            r"\blist\b",
            r"\bfind\b",
            r"\bsearch\b",
            r"\blook\b",
        ]

        for pattern in query_indicators:
            if re.search(pattern, text.lower()):
                domain = self._detect_domain(text)
                action = self._detect_action(text)

                confidence = 0.6  # Base confidence for query
                if text.lower().startswith(
                    ("what", "where", "when", "show", "list", "find", "search")
                ):
                    confidence = 0.8  # Higher if starts with query word

                return Intent(
                    intent_type=IntentType.QUERY,
                    domain=domain,
                    action=action,
                    entities=self._extract_entities(text),
                    raw_text=text,
                    confidence=confidence,
                )
        return None

    def _parse_as_command(self, text: str) -> Intent | None:
        """Parse text as action command."""
        # Detect command verbs
        command_verbs = [
            r"\bcreate\b",
            r"\bdelete\b",
            r"\brun\b",
            r"\bexecute\b",
            r"\bstart\b",
            r"\bstop\b",
        ]

        for pattern in command_verbs:
            if re.search(pattern, text.lower()):
                domain = self._detect_domain(text)
                action = self._detect_action(text)

                confidence = 0.7  # Base confidence for command
                if text.lower().startswith(("create", "delete", "run", "execute")):
                    confidence = 0.9  # Higher if starts with command verb

                return Intent(
                    intent_type=IntentType.COMMAND,
                    domain=domain,
                    action=action,
                    entities=self._extract_entities(text),
                    raw_text=text,
                    confidence=confidence,
                )
        return None

    def _parse_as_question(self, text: str) -> Intent | None:
        """Parse text as question."""
        if text.strip().endswith("?"):
            domain = self._detect_domain(text)
            action = "answer"

            return Intent(
                intent_type=IntentType.QUESTION,
                domain=domain,
                action=action,
                entities=self._extract_entities(text),
                raw_text=text,
                confidence=0.85,  # High confidence for questions
            )
        return None

    def _detect_domain(self, text: str) -> IntentDomain:
        """Detect domain from text."""
        text_lower = text.lower()
        domain_scores = {}

        for domain, patterns in self._domain_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)  # type: ignore

        # Default to conversation if no specific domain detected
        return IntentDomain.CONVERSATION

    def _detect_action(self, text: str) -> str:
        """Detect primary action from text."""
        text_lower = text.lower()

        for action, patterns in self._action_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return action

        return "process"  # Default action

    def _extract_entities(self, text: str) -> dict[str, Any]:
        """Extract entities from text."""
        entities: dict[str, Any] = {}

        # Extract file paths (simple heuristic)
        file_pattern = r"[\w/\\]+\.\w+"
        files = re.findall(file_pattern, text)
        if files:
            entities["files"] = files

        # Extract numbers
        numbers = re.findall(r"\b\d+\b", text)
        if numbers:
            entities["numbers"] = [int(n) for n in numbers]

        # Extract quoted strings
        quoted = re.findall(r'"([^"]*)"', text)
        if quoted:
            entities["quoted"] = quoted

        return entities


def get_intent_resolver() -> IntentResolver:
    """Get global intent resolver singleton."""
    global _intent_resolver
    if "_intent_resolver" not in globals():
        _intent_resolver = IntentResolver()
    return _intent_resolver


# Example usage
if __name__ == "__main__":
    resolver = IntentResolver()

    # Test ambiguous input
    superposition = resolver.resolve("find the function")

    print(f"Raw input: {superposition.raw_text}")
    print(f"Number of interpretations: {len(superposition.intents)}")
    print(f"Ambiguous: {superposition.is_ambiguous()}")
    print(f"Entropy: {superposition.entropy():.3f}")
    print("\nTop 3 interpretations:")
    for i, intent in enumerate(superposition.top_k(3), 1):
        print(f"{i}. {intent.intent_type.value} ({intent.confidence:.2f})")
        print(f"   Domain: {intent.domain.value}, Action: {intent.action}")

    # Collapse superposition
    chosen = superposition.collapse()
    print(f"\nCollapsed to: {chosen.intent_type.value} with {chosen.confidence:.2f} confidence")
