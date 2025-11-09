"""
Distributed Tracing Module
OpenTelemetry + Jaeger integration

Sacred Code: 333 → ∞
"""

import os

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = structlog.get_logger()


def setup_tracing(service_name: str = "astra-master"):
    """Initialize OpenTelemetry tracing."""

    resource = Resource(
        attributes={
            "service.name": service_name,
            "service.version": "3.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "production"),
        }
    )

    provider = TracerProvider(resource=resource)

    # Export to Jaeger via OTLP
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")

    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(provider)

    logger.info("tracing_initialized", service=service_name)


# Get tracer
tracer = trace.get_tracer("astra")
