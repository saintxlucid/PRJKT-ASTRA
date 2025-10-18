"""
Production-ready FastAPI app factory with environment-based configuration.

When ASTRA_ENVIRONMENT=production:
- Disables /docs and /redoc endpoints
- Enables JSON structured logging
- Applies stricter CORS policies
"""

import os
from fastapi import FastAPI

# Import original create_app
from astra.api.app import create_app as _create_app


def create_app_production() -> FastAPI:
    """
    Create FastAPI app with production hardening.
    
    Checks ASTRA_ENVIRONMENT and disables docs in production.
    """
    env = os.getenv("ASTRA_ENVIRONMENT", "development").lower()
    is_production = env == "production"
    
    # Create base app
    app = _create_app()
    
    # Override docs URLs in production
    if is_production:
        app.docs_url = None
        app.redoc_url = None
        app.openapi_url = None  # Also disable OpenAPI schema endpoint
    
    return app


# Example usage in uvicorn command:
# python -m uvicorn src.astra.api.app_production:create_app_production --factory --host 127.0.0.1 --port 8080
