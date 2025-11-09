from fastapi.testclient import TestClient
from src.astra.core.app import app  # Adjust import path as needed

def test_liveness_and_readiness():
    """Test basic health check endpoints"""
    with TestClient(app) as client:
        # Test liveness
        live_response = client.get("/live")
        assert live_response.status_code == 200
        assert live_response.json().get("live") is True
        
        # Test readiness
        ready_response = client.get("/ready")
        assert ready_response.status_code == 200
        assert "ready" in ready_response.json()

def test_full_health_shape():
    """Test full health report structure"""
    with TestClient(app) as client:
        response = client.get("/health/full")
        assert response.status_code == 200
        health_data = response.json()
        
        # Verify required fields
        assert "status" in health_data
        assert health_data["status"] in ("ok", "degraded")
        
        # Verify all components present
        assert "components" in health_data
        required_components = {
            "memory", "inference", "rag", 
            "cache", "metrics"
        }
        for component in required_components:
            assert component in health_data["components"]
            
        # Verify component structure
        for component in health_data["components"].values():
            assert "status" in component
            assert component["status"] in ("ok", "degraded", "error")
            if component["status"] != "ok":
                assert "reason" in component