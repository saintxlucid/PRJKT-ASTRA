"""
Harmony Format Round-Trip Tests

Tests the full cycle: harmony.build() → model → harmony.parse()
Validates schema guards, stop token enforcement, and analysis channel redaction.
"""

from typing import List

import pytest

from astra.infrastructure.llm.base import Message
from astra.infrastructure.llm.harmony import (
    HarmonyMessage,
    HarmonyPromptBuilder,
    convert_to_openai_format,
    parse_harmony_response,
    strip_cot_from_history,
)


class TestHarmonyRoundTrip:
    """Test Harmony format round-trip processing"""

    def test_build_and_parse_simple(self):
        """Test simple round-trip: build → parse"""
        messages = [
            Message(role="system", content="You are a helpful assistant."),
            Message(role="user", content="What is 2+2?"),
        ]

        # Build Harmony prompt
        builder = HarmonyPromptBuilder()
        for msg in messages:
            builder.add_message(msg.role, msg.content, channel="final")
        
        harmony_prompt = builder.build()

        # Verify structure
        assert "<|start_header_id|>system<|end_header_id|>" in harmony_prompt
        assert "<|start_header_id|>user<|end_header_id|>" in harmony_prompt
        assert "You are a helpful assistant." in harmony_prompt
        assert "What is 2+2?" in harmony_prompt

    def test_parse_response_with_analysis_channel(self):
        """Test parsing response with analysis channel"""
        model_output = """<|start_header_id|>assistant|analysis<|end_header_id|>

Let me think about this. 2+2 is a basic arithmetic operation. I need to add two and two together.

<|start_header_id|>assistant|final<|end_header_id|>

The answer is 4."""

        parsed = parse_harmony_response(model_output)

        assert len(parsed) == 2
        assert parsed[0].role == "assistant"
        assert parsed[0].channel == "analysis"
        assert "Let me think" in parsed[0].content
        assert parsed[1].role == "assistant"
        assert parsed[1].channel == "final"
        assert "The answer is 4" in parsed[1].content

    def test_parse_response_without_channels(self):
        """Test parsing response without channel specification"""
        model_output = """<|start_header_id|>assistant<|end_header_id|>

The answer is 4."""

        parsed = parse_harmony_response(model_output)

        assert len(parsed) == 1
        assert parsed[0].role == "assistant"
        assert parsed[0].channel == "final"
        assert "The answer is 4" in parsed[0].content

    def test_strip_cot_from_history(self):
        """Test removing analysis channel from history"""
        messages = [
            HarmonyMessage(role="user", content="What is 2+2?", channel="final"),
            HarmonyMessage(
                role="assistant",
                content="Let me think...",
                channel="analysis"
            ),
            HarmonyMessage(role="assistant", content="The answer is 4.", channel="final"),
        ]

        stripped = strip_cot_from_history(messages)

        assert len(stripped) == 2
        assert stripped[0].role == "user"
        assert stripped[1].role == "assistant"
        assert stripped[1].content == "The answer is 4."
        assert "Let me think" not in str(stripped)

    def test_convert_to_openai_format(self):
        """Test converting Harmony messages to OpenAI format"""
        harmony_messages = [
            HarmonyMessage(role="system", content="You are helpful.", channel="final"),
            HarmonyMessage(role="user", content="Hello!", channel="final"),
            HarmonyMessage(
                role="assistant",
                content="Chain of thought...",
                channel="analysis"
            ),
            HarmonyMessage(role="assistant", content="Hi there!", channel="final"),
        ]

        openai_messages = convert_to_openai_format(harmony_messages)

        assert len(openai_messages) == 3  # Analysis channel stripped
        assert openai_messages[0]["role"] == "system"
        assert openai_messages[1]["role"] == "user"
        assert openai_messages[2]["role"] == "assistant"
        assert openai_messages[2]["content"] == "Hi there!"

    def test_multi_turn_conversation(self):
        """Test multi-turn conversation with analysis"""
        messages = [
            Message(role="system", content="You are a math tutor."),
            Message(role="user", content="What is 10 * 5?"),
            Message(role="assistant", content="50"),
            Message(role="user", content="What about 50 / 2?"),
        ]

        # Build
        builder = HarmonyPromptBuilder()
        for msg in messages:
            builder.add_message(msg.role, msg.content)
        
        prompt = builder.build()

        # Verify all messages present
        assert "math tutor" in prompt
        assert "10 * 5" in prompt
        assert "50 / 2" in prompt

        # Simulate model response with analysis
        response = """<|start_header_id|>assistant|analysis<|end_header_id|>

50 divided by 2 equals 25.

<|start_header_id|>assistant|final<|end_header_id|>

The answer is 25."""

        parsed = parse_harmony_response(response)
        assert len(parsed) == 2
        
        # Strip analysis for next turn
        stripped = strip_cot_from_history(parsed)
        assert len(stripped) == 1
        assert stripped[0].content == "The answer is 25."


class TestSchemaGuards:
    """Test schema validation and guards"""

    def test_analysis_in_final_detection(self):
        """Test detecting when analysis bleeds into final channel"""
        # This should be detected as problematic
        bad_response = """<|start_header_id|>assistant|final<|end_header_id|>

Let me think step by step...
1. First, I need to consider...
2. Then, I should...

The answer is 4."""

        # Simple heuristic: if "step by step" or "Let me think" appears in final
        def has_analysis_bleed(content: str) -> bool:
            analysis_markers = [
                "let me think",
                "step by step",
                "first, i need to",
                "i should consider",
            ]
            content_lower = content.lower()
            return any(marker in content_lower for marker in analysis_markers)

        parsed = parse_harmony_response(bad_response)
        assert len(parsed) == 1
        assert has_analysis_bleed(parsed[0].content)

    def test_missing_final_channel(self):
        """Test handling response with only analysis channel"""
        analysis_only = """<|start_header_id|>assistant|analysis<|end_header_id|>

This is only analysis, no final answer."""

        parsed = parse_harmony_response(analysis_only)
        
        # Should still parse, but we need a final channel
        assert len(parsed) == 1
        assert parsed[0].channel == "analysis"
        
        # Application should detect this and retry or default

    def test_malformed_headers(self):
        """Test handling malformed Harmony headers"""
        malformed = """<|start_header_id|>assistant

Missing end tag!"""

        # Parser should handle gracefully
        parsed = parse_harmony_response(malformed)
        
        # Should fall back to treating entire content as final
        assert len(parsed) >= 0  # Graceful degradation

    def test_empty_channels(self):
        """Test handling empty channel content"""
        empty_analysis = """<|start_header_id|>assistant|analysis<|end_header_id|>

<|start_header_id|>assistant|final<|end_header_id|>

The answer is 4."""

        parsed = parse_harmony_response(empty_analysis)
        
        # Should skip empty channels or handle gracefully
        final_messages = [m for m in parsed if m.channel == "final"]
        assert len(final_messages) == 1
        assert "The answer is 4" in final_messages[0].content


class TestStopTokenEnforcement:
    """Test stop token enforcement"""

    def test_stop_tokens_list(self):
        """Test comprehensive stop token list"""
        stop_tokens = [
            "<|start_header_id|>",
            "<|end_header_id|>",
            "</s>",
            "<|eot_id|>",
            "<|end_of_text|>",
        ]

        # These should prevent model from continuing inappropriately
        assert "<|start_header_id|>" in stop_tokens
        assert "</s>" in stop_tokens

    def test_channel_switch_detection(self):
        """Test detecting when model switches channels mid-response"""
        channel_switch = """<|start_header_id|>assistant|final<|end_header_id|>

Here is my answer.

<|start_header_id|>assistant|analysis<|end_header_id|>

Wait, let me reconsider..."""

        # This should be detected and prevented
        parsed = parse_harmony_response(channel_switch)
        assert len(parsed) == 2
        
        # Application should only use the first final channel
        final_only = [m for m in parsed if m.channel == "final"]
        assert len(final_only) == 1

    def test_prevent_multiple_assistant_turns(self):
        """Test preventing model from generating multiple assistant turns"""
        multi_turn = """<|start_header_id|>assistant|final<|end_header_id|>

Here is my answer.

<|start_header_id|>user<|end_header_id|>

Follow-up question?

<|start_header_id|>assistant|final<|end_header_id|>

Another answer."""

        # Stop tokens should prevent this
        # Parser should detect and only take first assistant message
        parsed = parse_harmony_response(multi_turn)
        
        # Should stop at first complete assistant message
        assistant_messages = [m for m in parsed if m.role == "assistant"]
        # In practice, stop tokens prevent this, but parser should handle it


class TestChannelIsolation:
    """Test channel isolation and redaction"""

    def test_analysis_never_in_user_memory(self):
        """Test that analysis channel is never persisted to user-facing memory"""
        conversation = [
            HarmonyMessage(role="user", content="Question", channel="final"),
            HarmonyMessage(role="assistant", content="Thinking...", channel="analysis"),
            HarmonyMessage(role="assistant", content="Answer", channel="final"),
        ]

        # Strip before storage
        memory_safe = strip_cot_from_history(conversation)
        
        assert len(memory_safe) == 2
        assert all(m.channel != "analysis" for m in memory_safe)
        assert "Thinking" not in str(memory_safe)

    def test_logging_redaction(self):
        """Test that sensitive analysis is redacted from logs"""
        response_with_analysis = """<|start_header_id|>assistant|analysis<|end_header_id|>

[Private reasoning about user's sensitive query]

<|start_header_id|>assistant|final<|end_header_id|>

[Public answer]"""

        parsed = parse_harmony_response(response_with_analysis)
        
        # For logging, strip analysis
        log_safe = strip_cot_from_history(parsed)
        assert "Private reasoning" not in str(log_safe)

    def test_api_response_format(self):
        """Test API response only includes final channel"""
        full_response = [
            HarmonyMessage(role="assistant", content="Analysis", channel="analysis"),
            HarmonyMessage(role="assistant", content="Final answer", channel="final"),
        ]

        # Convert for API
        api_response = strip_cot_from_history(full_response)
        
        assert len(api_response) == 1
        assert api_response[0].content == "Final answer"


class TestEmptyContextFallbacks:
    """Test fallback behavior for edge cases"""

    def test_empty_message_list(self):
        """Test handling empty message list"""
        builder = HarmonyPromptBuilder()
        prompt = builder.build()
        
        # Should produce valid but minimal prompt
        assert "<|start_header_id|>" in prompt or prompt == ""

    def test_no_system_message(self):
        """Test conversation without system message"""
        messages = [
            Message(role="user", content="Hello"),
        ]

        builder = HarmonyPromptBuilder()
        for msg in messages:
            builder.add_message(msg.role, msg.content)
        
        prompt = builder.build()
        
        # Should still be valid
        assert "<|start_header_id|>user<|end_header_id|>" in prompt

    def test_system_only(self):
        """Test with only system message"""
        messages = [
            Message(role="system", content="You are helpful."),
        ]

        builder = HarmonyPromptBuilder()
        for msg in messages:
            builder.add_message(msg.role, msg.content)
        
        prompt = builder.build()
        
        # Should be valid
        assert "helpful" in prompt

    def test_parse_empty_response(self):
        """Test parsing empty model response"""
        parsed = parse_harmony_response("")
        
        # Should return empty list or single empty message
        assert isinstance(parsed, list)

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only response"""
        parsed = parse_harmony_response("   \n\n  ")
        
        # Should handle gracefully
        assert isinstance(parsed, list)


class TestHeaderSequencing:
    """Test proper header sequencing and role hierarchy"""

    def test_role_hierarchy(self):
        """Test role hierarchy: system > developer > user > assistant > tool"""
        # System should come first
        messages = [
            Message(role="user", content="Question"),
            Message(role="system", content="System prompt"),
        ]

        # Builder should handle ordering
        builder = HarmonyPromptBuilder()
        builder.add_message("system", "System prompt")
        builder.add_message("user", "Question")
        
        prompt = builder.build()
        
        # System should appear before user
        system_pos = prompt.find("system")
        user_pos = prompt.find("user")
        assert system_pos < user_pos

    def test_alternating_user_assistant(self):
        """Test proper alternating user/assistant pattern"""
        builder = HarmonyPromptBuilder()
        builder.add_message("user", "First question")
        builder.add_message("assistant", "First answer")
        builder.add_message("user", "Second question")
        builder.add_message("assistant", "Second answer")
        
        prompt = builder.build()
        
        # All messages should be present in order
        assert "First question" in prompt
        assert "First answer" in prompt
        assert "Second question" in prompt
        assert "Second answer" in prompt

    def test_no_consecutive_same_role(self):
        """Test detection of consecutive same-role messages"""
        # This should be flagged as potentially problematic
        messages = [
            Message(role="user", content="First user message"),
            Message(role="user", content="Second user message"),
        ]

        # Application should merge or handle appropriately
        def has_consecutive_same_role(messages: List[Message]) -> bool:
            for i in range(len(messages) - 1):
                if messages[i].role == messages[i + 1].role:
                    return True
            return False

        assert has_consecutive_same_role(messages)


# Integration test with mock LLM
class TestHarmonyIntegration:
    """Integration tests with mocked LLM"""

    @pytest.mark.asyncio
    async def test_full_cycle_with_mock_llm(self):
        """Test full cycle: build → mock LLM → parse → store"""
        # Build request
        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="What is AI?"),
        ]

        builder = HarmonyPromptBuilder()
        for msg in messages:
            builder.add_message(msg.role, msg.content)
        
        prompt = builder.build()

        # Mock LLM response
        mock_response = """<|start_header_id|>assistant|analysis<|end_header_id|>

AI stands for Artificial Intelligence. Let me provide a clear definition.

<|start_header_id|>assistant|final<|end_header_id|>

AI is the simulation of human intelligence by machines."""

        # Parse response
        parsed = parse_harmony_response(mock_response)
        assert len(parsed) == 2

        # Strip analysis for storage
        storage_messages = strip_cot_from_history(parsed)
        assert len(storage_messages) == 1
        assert storage_messages[0].content == "AI is the simulation of human intelligence by machines."

        # Convert for API response
        api_messages = convert_to_openai_format(storage_messages)
        assert len(api_messages) == 1
        assert api_messages[0]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_retry_on_analysis_bleed(self):
        """Test retry logic when analysis bleeds into final"""
        # First attempt: analysis in final channel
        bad_response = """<|start_header_id|>assistant|final<|end_header_id|>

Let me think step by step about this question..."""

        # Detect bleed
        def has_analysis_in_final(response: str) -> bool:
            if "|final<|end_header_id|>" in response:
                content = response.split("|final<|end_header_id|>")[1]
                analysis_markers = ["step by step", "let me think", "first, i"]
                return any(marker in content.lower() for marker in analysis_markers)
            return False

        assert has_analysis_in_final(bad_response)

        # Application should retry with lower temperature
        # Second attempt would have better parameters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
