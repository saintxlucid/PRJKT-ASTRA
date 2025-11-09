"""Web Agent Workflows - High-level web automation patterns.

Provides multi-step workflows for common web tasks built on browser skill.
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import chat_os.skills.browser as browser_skill
from chat_os.executor import ExecutionContext, register_intent
from chat_os.plan import PlanStep
from chat_os.skills.compose import _call_llm

logger = logging.getLogger(__name__)

# Module-level proxies allow tests to patch browser handlers without touching the
# underlying browser module directly.
handle_navigate = browser_skill.handle_navigate
handle_extract_markdown = browser_skill.handle_extract_markdown
handle_query = browser_skill.handle_query
handle_type = browser_skill.handle_type
handle_click = browser_skill.handle_click

_ORIGINAL_HANDLERS = {
    "handle_navigate": handle_navigate,
    "handle_extract_markdown": handle_extract_markdown,
    "handle_query": handle_query,
    "handle_type": handle_type,
    "handle_click": handle_click,
}


def _call_browser(intent: str, ctx: ExecutionContext, **args: Any) -> dict[str, Any]:
    """Dispatch to browser skill handlers by intent name."""
    handler_name = f"handle_{intent.split('.')[-1]}"
    override = globals().get(handler_name)
    module_attr = getattr(browser_skill, handler_name, None)

    if override is not None and override is not _ORIGINAL_HANDLERS.get(handler_name):
        handler = override
    elif module_attr is not None:
        handler = module_attr
    else:
        handler = override

    if handler is None:
        raise ValueError(f"Unsupported browser intent: {intent}")
    step = PlanStep(intent=intent, args=args)
    return handler(step, ctx)



def _sleep(seconds: float, ctx: ExecutionContext) -> None:
    """Allow tests to override sleep with a faster implementation."""
    sleeper = ctx.variables.get("web_agent.sleep_fn")
    if callable(sleeper):
        sleeper(seconds)
    else:
        time.sleep(seconds)


@register_intent("web_agent.research")
def handle_web_research(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Multi-step web research workflow with optional AI summarization."""
    url = step.args.get("url")
    extract_selector = step.args.get("extract_selector")
    summarize = step.args.get("summarize", False)
    max_tokens = int(step.args.get("max_tokens", 1200))
    store_as = step.args.get("store_as")

    if not url:
        return {"ok": False, "error": "Missing required arg: url"}

    try:
        # Navigate to URL
        nav_result = _call_browser(
            "browser.navigate",
            ctx,
            url=url,
            extract_content=False,
        )

        if not nav_result.get("ok"):
            return nav_result

        # Extract content
        extract_result = _call_browser(
            "browser.extract_markdown",
            ctx,
            selector=extract_selector,
            max_tokens=max_tokens,
        )

        if not extract_result.get("ok"):
            return extract_result

        content = extract_result.get("markdown", "")
        result = {
            "ok": True,
            "url": nav_result["url"],
            "title": nav_result.get("title", ""),
            "content": content,
            "tokens_extracted": len(content.split()),
        }

        # Optional summarization
        if summarize and content:
            prompt = f"""Summarize the following web content in 2-3 concise paragraphs:

{content[:2000]}

Summary:"""

            summary = _call_llm(prompt, max_tokens=300, temperature=0.5)
            result["summary"] = summary

        # Store in context if requested
        if store_as:
            ctx.variables[store_as] = result
            logger.info(f"Stored research results as '{store_as}'")

        return result

    except Exception as e:
        logger.error(f"Web research failed: {e}")
        return {"ok": False, "error": str(e)}


@register_intent("web_agent.extract_structured")
def handle_extract_structured(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Extract structured data from webpage using LLM."""
    url = step.args.get("url")
    schema = step.args.get("schema")
    selector = step.args.get("selector")
    examples = step.args.get("examples", "")

    if not schema:
        return {"ok": False, "error": "Missing required arg: schema"}

    try:
        # Navigate if URL provided
        if url:
            nav_result = _call_browser(
                "browser.navigate",
                ctx,
                url=url,
                extract_content=False,
            )
            if not nav_result.get("ok"):
                return nav_result

        # Extract content
        extract_result = _call_browser(
            "browser.extract_markdown",
            ctx,
            selector=selector,
            max_tokens=1500,
        )

        if not extract_result.get("ok"):
            return extract_result

        content = extract_result.get("markdown", "")

        # Use LLM to extract structured data
        example_text = f"\n\nExamples:\n{examples}" if examples else ""

        prompt = f"""Extract structured data from the following webpage content.

Required Schema:
{schema}
{example_text}

Webpage Content:
{content[:2000]}

Return ONLY valid JSON matching the schema above:"""

        llm_response = _call_llm(prompt, max_tokens=800, temperature=0.3)

        # Parse JSON from response
        try:
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(llm_response)

            return {
                "ok": True,
                "data": data,
                "confidence": "high" if json_match else "medium",
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            fallback = _build_fallback_from_schema(schema, content)
            if fallback is not None:
                return {
                    "ok": True,
                    "data": fallback,
                    "confidence": "low",
                    "note": "Returned heuristic fallback due to parse failure",
                }
            return {
                "ok": False,
                "error": "Failed to parse structured data",
                "llm_response": llm_response[:200],
            }

    except Exception as e:
        logger.error(f"Structured extraction failed: {e}")
        return {"ok": False, "error": str(e)}


@register_intent("web_agent.fill_form")
def handle_fill_form(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Fill web form with validation."""
    url = step.args.get("url")
    fields = step.args.get("fields", {})
    submit_selector = step.args.get("submit_selector")
    validate = step.args.get("validate", True)
    wait_after_submit = int(step.args.get("wait_after_submit", 2000))

    if not fields:
        return {"ok": False, "error": "Missing required arg: fields"}

    try:
        # Navigate if URL provided
        if url:
            nav_result = _call_browser(
                "browser.navigate",
                ctx,
                url=url,
                extract_content=False,
            )
            if not nav_result.get("ok"):
                return nav_result

        # Fill each field
        filled_count = 0
        validation_results = {}

        for selector, value in fields.items():
            type_result = _call_browser(
                "browser.type",
                ctx,
                selector=selector,
                text=str(value),
                clear_first=True,
            )

            if type_result.get("ok"):
                filled_count += 1

                # Validate if requested
                if validate:
                    query_result = _call_browser(
                        "browser.query",
                        ctx,
                        selector=selector,
                    )
                    validation_results[selector] = {
                        "ok": query_result.get("ok", False),
                        "visible": query_result.get("visible", False),
                    }
            else:
                validation_results[selector] = {
                    "ok": False,
                    "error": type_result.get("error", "Unknown error"),
                }

        result = {
            "ok": True,
            "filled_count": filled_count,
            "total_fields": len(fields),
            "validation": validation_results if validate else {},
        }

        # Submit form if requested
        if submit_selector:
            click_result = _call_browser(
                "browser.click",
                ctx,
                selector=submit_selector,
            )
            result["submitted"] = click_result.get("ok", False)

            if click_result.get("ok") and wait_after_submit > 0:
                _sleep(wait_after_submit / 1000, ctx)

        return result

    except Exception as e:
        logger.error(f"Form filling failed: {e}")
        return {"ok": False, "error": str(e)}


@register_intent("web_agent.paginate")
def handle_paginate(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Navigate through paginated results."""
    next_selector = step.args.get("next_selector")
    content_selector = step.args.get("content_selector")
    max_pages = int(step.args.get("max_pages", 10))
    combine_strategy = step.args.get("combine_strategy", "concat")
    stop_text = step.args.get("stop_text")

    if not next_selector:
        return {"ok": False, "error": "Missing required arg: next_selector"}

    pages_visited = 0
    try:
        collected: list[str] = []

        while pages_visited < max_pages:
            # Extract content from current page
            extract_result = _call_browser(
                "browser.extract_markdown",
                ctx,
                selector=content_selector,
                max_tokens=1000,
            )

            if not extract_result.get("ok"):
                logger.warning(f"Failed to extract page {pages_visited + 1}")
                break

            content = extract_result.get("markdown", "")
            pages_visited += 1

            # Check for stop text
            if stop_text and stop_text in content:
                logger.info(f"Found stop text '{stop_text}' on page {pages_visited}")
                break

            # Add to combined content
            if combine_strategy == "list":
                collected.append(content)
            else:
                collected.append(f"--- Page {pages_visited} ---\n\n{content}")

            # Try to click "Next" button
            click_result = _call_browser(
                "browser.click",
                ctx,
                selector=next_selector,
            )

            if not click_result.get("ok"):
                logger.info(f"No more pages after page {pages_visited}")
                break

            # Wait for new page to load
            _sleep(1, ctx)
        combined_content = collected if combine_strategy == "list" else "\n\n".join(collected)

        return {
            "ok": True,
            "pages_visited": pages_visited,
            "combined_content": combined_content,
            "strategy": combine_strategy,
        }

    except Exception as e:
        logger.error(f"Pagination failed: {e}")
        return {
            "ok": False,
            "error": str(e),
            "pages_visited": pages_visited,
        }


@register_intent("web_agent.monitor")
def handle_monitor_page(step: PlanStep, ctx: ExecutionContext) -> dict[str, Any]:
    """Monitor webpage for changes."""
    url = step.args.get("url")
    selector = step.args.get("selector")
    interval_seconds = int(step.args.get("interval_seconds", 60))
    max_checks = int(step.args.get("max_checks", 10))
    notify_on_change = step.args.get("notify_on_change", True)

    try:
        # Navigate if URL provided
        if url:
            nav_result = _call_browser(
                "browser.navigate",
                ctx,
                url=url,
                extract_content=False,
            )
            if not nav_result.get("ok"):
                return nav_result

        # Get initial content
        initial_result = _call_browser(
            "browser.extract_markdown",
            ctx,
            selector=selector,
            max_tokens=1000,
        )

        if not initial_result.get("ok"):
            return initial_result

        previous_content = initial_result.get("markdown", "")
        checks_performed = 1
        changes_detected = 0

        # Monitor loop
        for check_num in range(2, max_checks + 1):
            _sleep(interval_seconds, ctx)

            # Refresh page
            _call_browser(
                "browser.navigate",
                ctx,
                url=url or ctx.variables.get("browser.current_url", ""),
                extract_content=False,
            )

            # Extract new content
            current_result = _call_browser(
                "browser.extract_markdown",
                ctx,
                selector=selector,
                max_tokens=1000,
            )

            if not current_result.get("ok"):
                logger.warning(f"Failed to extract content on check {check_num}")
                continue

            current_content = current_result.get("markdown", "")
            checks_performed += 1

            # Compare content
            if current_content != previous_content:
                changes_detected += 1
                if notify_on_change:
                    logger.info(f"Change detected on check {check_num}")
                previous_content = current_content

        return {
            "ok": True,
            "checks_performed": checks_performed,
            "changes_detected": changes_detected,
            "last_content": previous_content,
            "interval_seconds": interval_seconds,
        }

    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        return {"ok": False, "error": str(e)}


def _build_fallback_from_schema(schema: str, content: str) -> dict[str, Any] | None:
    """Attempt a simple fallback extraction when JSON parsing fails."""
    try:
        schema_obj = json.loads(schema)
    except json.JSONDecodeError:
        return None

    if not isinstance(schema_obj, dict):
        return None

    fallback: dict[str, Any] = {}
    for key, value in schema_obj.items():
        if isinstance(value, str):
            # crude heuristic: look for "key: value" patterns in content
            pattern = rf"{re.escape(key)}[:\-]\s*(.+)"
            match = re.search(pattern, content, re.IGNORECASE)
            fallback[key] = match.group(1).strip() if match else ""
        else:
            fallback[key] = None

    return fallback if any(fallback.values()) else None
