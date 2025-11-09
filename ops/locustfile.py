"""
ASTRA Load Testing with Locust
================================

Performance validation tool for ASTRA endpoints.
Target: 100 req/s sustained, <1.2s p95 latency.

Usage:
    # Run with UI
    locust -f ops/locustfile.py --host http://localhost:8000
    
    # Headless mode (5 min test, 100 users)
    locust -f ops/locustfile.py --headless -u 100 -r 10 --run-time 5m \\
        --host http://localhost:8000

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""
from locust import HttpUser, task, between, events
import json
import time


class AstraUser(HttpUser):
    """
    Simulated ASTRA user making requests to various endpoints.
    
    Weight distribution:
    - 3x chat requests (most common operation)
    - 1x memory search
    - 1x cognitive status check
    - 1x agent task creation
    """
    
    # Wait 200-800ms between requests (simulates realistic user behavior)
    wait_time = between(0.2, 0.8)
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Could initialize session, authenticate, etc.
        pass
    
    @task(3)
    def chat_request(self):
        """
        Test chat endpoint (highest weight).
        
        Simulates user sending chat messages.
        """
        payload = {
            "query": "What is ASTRA's purpose?",
            "stream": False,
            "conversation_id": None
        }
        
        with self.client.post(
            "/v1/chat",
            json=payload,
            catch_response=True,
            name="/v1/chat"
        ) as response:
            if response.status_code == 200:
                # Validate response structure
                data = response.json()
                if "response" in data:
                    response.success()
                else:
                    response.failure("Missing response field")
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(1)
    def memory_search(self):
        """
        Test memory search endpoint.
        
        Simulates semantic memory queries.
        """
        payload = {
            "query": "Sigil Gate authorization",
            "limit": 10
        }
        
        with self.client.post(
            "/v1/memory/search",
            json=payload,
            catch_response=True,
            name="/v1/memory/search"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if isinstance(data.get("results"), list):
                    response.success()
                else:
                    response.failure("Invalid results format")
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(1)
    def cognitive_status(self):
        """
        Test cognitive system status endpoint.
        
        Lightweight health check for cognitive phases.
        """
        with self.client.get(
            "/v1/cognitive/status",
            catch_response=True,
            name="/v1/cognitive/status"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(1)
    def create_agent_task(self):
        """
        Test agent task creation.
        
        Simulates autonomous agent task submission.
        """
        payload = {
            "goal": "Check system status",
            "timeout_s": 30
        }
        
        with self.client.post(
            "/v1/agent/task",
            json=payload,
            catch_response=True,
            name="/v1/agent/task"
        ) as response:
            if response.status_code in (200, 201):
                data = response.json()
                if "task_id" in data:
                    response.success()
                else:
                    response.failure("Missing task_id")
            else:
                response.failure(f"Status {response.status_code}")
    
    @task(2)
    def health_check(self):
        """
        Test system health endpoint.
        
        Lightweight ping to verify system responsiveness.
        """
        with self.client.get(
            "/v1/system/health",
            catch_response=True,
            name="/v1/system/health"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")


# Event hooks for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print("\n" + "="*60)
    print("🌌 ASTRA Load Test Starting")
    print("="*60)
    print(f"Target: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    print("="*60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    print("\n" + "="*60)
    print("🌌 ASTRA Load Test Complete")
    print("="*60)
    
    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio*100:.2f}%")
    print(f"RPS: {stats.total.total_rps:.2f}")
    print(f"Median Response Time: {stats.total.median_response_time}ms")
    print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99)}ms")
    
    # Check if performance targets met
    p95 = stats.total.get_response_time_percentile(0.95)
    fail_rate = stats.total.fail_ratio
    
    print("\n" + "-"*60)
    print("Performance Targets:")
    print(f"  p95 < 1200ms: {'✅ PASS' if p95 < 1200 else '❌ FAIL'} ({p95:.0f}ms)")
    print(f"  Failure Rate < 1%: {'✅ PASS' if fail_rate < 0.01 else '❌ FAIL'} ({fail_rate*100:.2f}%)")
    print("-"*60 + "\n")
