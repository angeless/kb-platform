"""OpenTelemetry tracing middleware for full-chain observability.

Adds trace context to every HTTP request, propagates through Celery tasks.
Configured via OTEL_EXPORTER_OTLP_ENDPOINT environment variable.
"""

import logging

logger = logging.getLogger(__name__)

# Lazy initialization — only set up OTel if the SDK is installed
_tracer = None


def _get_tracer():
    global _tracer
    if _tracer is not None:
        return _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": "kb-platform-api"})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter()  # reads OTEL_EXPORTER_OTLP_ENDPOINT from env
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("kb-platform")
        logger.info("OpenTelemetry tracing initialized")
        return _tracer
    except ImportError:
        logger.debug("OpenTelemetry SDK not installed — tracing disabled")
        return None


def init_tracing():
    """Initialize OTel tracing. Call once at app startup."""
    _get_tracer()


def get_tracer():
    """Get the global tracer instance (or None if OTel not available)."""
    return _tracer
