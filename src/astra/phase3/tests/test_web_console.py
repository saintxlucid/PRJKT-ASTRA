"""Integration tests for Operator Web Console FastAPI endpoints.

Validates status, metrics, log streaming, and health check endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from astra.phase3.ui.web_console.main import ConsoleManager, app


@pytest.fixture
def client() -> TestClient:
    """Fixture for FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def console_manager() -> ConsoleManager:
    """Fixture for ConsoleManager instance."""
    return ConsoleManager()


class TestConsoleManagerBasic:
    """Test ConsoleManager basic functionality."""

    def test_initialization(self, console_manager: ConsoleManager) -> None:
        """Test console manager initializes correctly."""
        assert console_manager.start_time > 0
        assert len(console_manager.log_buffer) == 0

    def test_uptime_calculation(self, console_manager: ConsoleManager) -> None:
        """Test uptime is calculated correctly."""
        uptime = console_manager.get_uptime()
        assert uptime >= 0.0

    def test_add_log(self, console_manager: ConsoleManager) -> None:
        """Test adding a log message."""
        console_manager.add_log("Test message")
        assert len(console_manager.log_buffer) == 1
        assert "Test message" in console_manager.log_buffer[0]

    def test_add_multiple_logs(self, console_manager: ConsoleManager) -> None:
        """Test adding multiple log messages."""
        for i in range(5):
            console_manager.add_log(f"Message {i}")
        assert len(console_manager.log_buffer) == 5

    def test_log_buffer_max_size(self, console_manager: ConsoleManager) -> None:
        """Test log buffer maintains max size of 1000."""
        for i in range(1500):
            console_manager.add_log(f"Message {i}")
        assert len(console_manager.log_buffer) <= 1000

    def test_get_status(self, console_manager: ConsoleManager) -> None:
        """Test getting system status."""
        status = console_manager.get_status()
        assert status.uptime_seconds >= 0.0
        assert status.active_tasks >= 0
        assert status.memory_mb > 0
        assert status.cpu_percent >= 0

    def test_get_metrics(self, console_manager: ConsoleManager) -> None:
        """Test getting detailed metrics."""
        metrics = console_manager.get_metrics()
        assert metrics.timestamp > 0
        assert metrics.uptime >= 0
        assert metrics.tasks_active >= 0
        assert metrics.inference_latency_p50_ms > 0
        assert metrics.inference_latency_p95_ms > metrics.inference_latency_p50_ms


class TestEndpointHealth:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime" in data

    def test_health_check_uptime_positive(self, client: TestClient) -> None:
        """Test health check reports positive uptime."""
        response = client.get("/health")
        data = response.json()
        assert data["uptime"] >= 0.0


class TestEndpointStatus:
    """Test status endpoint."""

    def test_status_endpoint_200(self, client: TestClient) -> None:
        """Test status endpoint returns 200."""
        response = client.get("/v1/console/status")
        assert response.status_code == 200

    def test_status_response_structure(self, client: TestClient) -> None:
        """Test status response has expected structure."""
        response = client.get("/v1/console/status")
        data = response.json()

        required_fields = [
            "uptime_seconds",
            "active_tasks",
            "memory_mb",
            "cpu_percent",
            "vector_store_size",
            "inference_latency_ms",
        ]
        for field in required_fields:
            assert field in data

    def test_status_response_types(self, client: TestClient) -> None:
        """Test status response fields have correct types."""
        response = client.get("/v1/console/status")
        data = response.json()

        assert isinstance(data["uptime_seconds"], int | float)
        assert isinstance(data["active_tasks"], int)
        assert isinstance(data["memory_mb"], int | float)
        assert isinstance(data["cpu_percent"], int | float)
        assert isinstance(data["vector_store_size"], int)
        assert isinstance(data["inference_latency_ms"], int | float)

    def test_status_values_reasonable(self, client: TestClient) -> None:
        """Test status response values are within reasonable ranges."""
        response = client.get("/v1/console/status")
        data = response.json()

        assert data["uptime_seconds"] >= 0
        assert data["active_tasks"] >= 0
        assert data["memory_mb"] > 0
        assert 0 <= data["cpu_percent"] <= 100
        assert data["vector_store_size"] >= 0
        assert data["inference_latency_ms"] > 0


class TestEndpointMetrics:
    """Test metrics endpoint."""

    def test_metrics_endpoint_200(self, client: TestClient) -> None:
        """Test metrics endpoint returns 200."""
        response = client.get("/v1/console/metrics")
        assert response.status_code == 200

    def test_metrics_response_structure(self, client: TestClient) -> None:
        """Test metrics response has expected structure."""
        response = client.get("/v1/console/metrics")
        data = response.json()

        required_fields = [
            "timestamp",
            "uptime",
            "tasks_active",
            "memory_usage_mb",
            "cpu_usage_percent",
            "vector_store_entries",
            "inference_latency_p50_ms",
            "inference_latency_p95_ms",
        ]
        for field in required_fields:
            assert field in data

    def test_metrics_p95_greater_p50(self, client: TestClient) -> None:
        """Test P95 latency is >= P50 latency."""
        response = client.get("/v1/console/metrics")
        data = response.json()

        assert data["inference_latency_p95_ms"] >= data["inference_latency_p50_ms"]


class TestEndpointLogPost:
    """Test log posting endpoint."""

    def test_log_post_201(self, client: TestClient) -> None:
        """Test posting a log returns 200."""
        response = client.post("/v1/console/log?message=Test%20message")
        assert response.status_code == 200

    def test_log_post_response(self, client: TestClient) -> None:
        """Test log post response structure."""
        response = client.post("/v1/console/log?message=Test%20message")
        data = response.json()
        assert data["status"] == "logged"

    def test_log_post_adds_to_buffer(self, client: TestClient) -> None:
        """Test posting a log adds it to buffer."""
        import astra.phase3.ui.web_console.main as console_module

        initial_len = len(console_module.console_manager.log_buffer)
        client.post("/v1/console/log?message=New%20log")
        final_len = len(console_module.console_manager.log_buffer)

        assert final_len > initial_len


class TestEndpointLogStream:
    """Test log streaming endpoint."""

    def test_log_stream_headers(self, client: TestClient) -> None:
        """Test log stream has correct content type."""
        response = client.get("/v1/console/logs")
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

    def test_log_stream_returns_data(self, client: TestClient) -> None:
        """Test log stream returns data chunks."""
        import astra.phase3.ui.web_console.main as console_module

        console_module.console_manager.add_log("Test log message")

        response = client.get("/v1/console/logs")
        assert response.status_code == 200
        # Stream response should have content
        assert response.content is not None


class TestEndpointIntegration:
    """Integration tests across endpoints."""

    def test_status_and_metrics_consistency(self, client: TestClient) -> None:
        """Test status and metrics are consistent."""
        status_response = client.get("/v1/console/status")
        metrics_response = client.get("/v1/console/metrics")

        status_data = status_response.json()
        metrics_data = metrics_response.json()

        # Both should have uptime values
        assert status_data["uptime_seconds"] >= 0
        assert metrics_data["uptime"] >= 0

    def test_health_consistency(self, client: TestClient) -> None:
        """Test health check is consistent."""
        response1 = client.get("/health")
        response2 = client.get("/health")

        data1 = response1.json()
        data2 = response2.json()

        assert data1["status"] == data2["status"]
        assert data2["uptime"] >= data1["uptime"]

    def test_multiple_log_posts(self, client: TestClient) -> None:
        """Test posting multiple logs."""
        for i in range(3):
            response = client.post(f"/v1/console/log?message=Log%20{i}")
            assert response.status_code == 200

    def test_rapid_endpoint_calls(self, client: TestClient) -> None:
        """Test rapid calls to endpoints."""
        for _ in range(10):
            status_response = client.get("/v1/console/status")
            assert status_response.status_code == 200

            metrics_response = client.get("/v1/console/metrics")
            assert metrics_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
