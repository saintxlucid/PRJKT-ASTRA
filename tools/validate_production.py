#!/usr/bin/env python
"""Production validation suite for ASTRA Core."""
import argparse
import asyncio
import json
import sys
import time
from typing import Dict, List, Optional
import aiohttp
import requests
import structlog

log = structlog.get_logger()

class ValidationError(Exception):
    """Validation check failed."""
    pass

async def check_health_endpoints(base_url: str) -> None:
    """Validate health check endpoints."""
    async with aiohttp.ClientSession() as session:
        # Check /live
        async with session.get(f"{base_url}/live") as resp:
            if resp.status != 200:
                raise ValidationError(f"/live returned {resp.status}")
            
        # Check /ready
        async with session.get(f"{base_url}/ready") as resp:
            if resp.status != 200:
                raise ValidationError(f"/ready returned {resp.status}")
            data = await resp.json()
            if data.get("status") != "ready":
                raise ValidationError(f"/ready shows {data.get('status')}")
            
        # Check /health/full
        async with session.get(f"{base_url}/health/full") as resp:
            if resp.status != 200:
                raise ValidationError(f"/health/full returned {resp.status}")
            data = await resp.json()
            status = data.get("status")
            if status not in ("healthy", "degraded"):
                raise ValidationError(f"/health/full status {status}")
            log.info("health.check.complete", 
                    status=status, 
                    components=data.get("components", {}))

async def validate_answer_schema(base_url: str) -> None:
    """Validate /answer endpoint schema."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "query": "ping validation",
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": False
        }
        async with session.post(
            f"{base_url}/answer", 
            json=payload
        ) as resp:
            if resp.status != 200:
                raise ValidationError(f"/answer returned {resp.status}")
            data = await resp.json()
            
            required = ["answer", "latency_ms", "tokens_used", "queue_time_ms", "citations"]
            missing = [f for f in required if f not in data]
            if missing:
                raise ValidationError(f"Missing fields: {missing}")
            
            if not isinstance(data["citations"], list):
                raise ValidationError("citations must be an array")
                
            # Validate data types
            if not isinstance(data["latency_ms"], int):
                raise ValidationError("latency_ms must be an integer")
            if not isinstance(data["tokens_used"], int):
                raise ValidationError("tokens_used must be an integer")

async def check_sse_stream(base_url: str) -> None:
    """Validate SSE stream sequence."""
    async with aiohttp.ClientSession() as session:
        payload = {
            "query": "test stream validation",
            "max_tokens": 100,
            "temperature": 0.7,
            "stream": True
        }
        async with session.post(
            f"{base_url}/answer/stream",
            json=payload
        ) as resp:
            if resp.status != 200:
                raise ValidationError(f"/answer/stream returned {resp.status}")
            
            required_events = {"start", "content", "end"}
            seen_events = set()
            
            # Read events until we see all required (up to 50 lines to account for blank lines)
            count = 0
            max_lines = 50
            async for line in resp.content:
                count += 1
                if count > max_lines:
                    break
                    
                line = line.decode().strip()
                if not line or not line.startswith("data:"):
                    continue
                    
                try:
                    json_str = line.replace("data:", "", 1).strip()
                    data = json.loads(json_str)
                    event_type = data.get("type")
                    if event_type:
                        seen_events.add(event_type)
                        log.debug("sse.event.received", event_type=event_type, seen=list(seen_events))
                except json.JSONDecodeError as e:
                    log.debug("sse.parse.error", line=line[:100], error=str(e))
                    continue
                
                # Check if all required events have been seen
                if required_events.issubset(seen_events):
                    break
            
            log.info("sse.validation.complete", seen_events=list(seen_events), required=list(required_events))
            missing = required_events - seen_events
            if missing:
                raise ValidationError(f"Missing events: {missing}")

async def check_canary_routing(base_url: str) -> None:
    """Validate canary routing via header."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{base_url}/answer",
            params={"q": "whoami"},
            headers={"X-Canary": "1"}
        ) as resp:
            if resp.status != 200:
                raise ValidationError("Canary route failed")
            data = await resp.json()
            route = data.get("meta", {}).get("route")
            if route != "canary":
                raise ValidationError(f"Expected canary route, got {route}")

async def check_graceful_drain(base_url: str) -> None:
    """Validate graceful drain behavior."""
    async with aiohttp.ClientSession() as session:
        t0 = time.time()
        async with session.post(f"{base_url}/admin/drain") as resp:
            if resp.status != 200:
                raise ValidationError("Drain request failed")
        drain_time = time.time() - t0
        
        # Check readiness flipped to false
        async with session.get(f"{base_url}/ready") as resp:
            data = await resp.json()
            if data.get("ready"):
                raise ValidationError("Still ready after drain")
                
        log.info("drain.complete", 
                seconds=round(drain_time, 1))

async def run_validation(base_url: str) -> None:
    """Run all validation checks."""
    log.info("validation.starting", url=base_url)
    
    try:
        await check_health_endpoints(base_url)
        log.info("health.endpoints.valid")
        
        await validate_answer_schema(base_url)
        log.info("answer.schema.valid")
        
        await check_sse_stream(base_url)
        log.info("sse.stream.valid")
        
        await check_canary_routing(base_url)
        log.info("canary.routing.valid")
        
        # Skip drain check unless explicitly requested
        #await check_graceful_drain(base_url)
        
        log.info("validation.complete", status="success")
        
    except ValidationError as e:
        log.error("validation.failed", error=str(e))
        sys.exit(1)
        
    except Exception as e:
        log.exception("validation.error")
        sys.exit(2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://localhost:8080")
    args = parser.parse_args()
    
    asyncio.run(run_validation(args.host))

if __name__ == "__main__":
    main()