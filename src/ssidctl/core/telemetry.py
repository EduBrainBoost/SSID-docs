"""OpenTelemetry Instrumentation -- observability scaffold.

Provides tracing, metrics, and structured logging for EMS operations.
Requires: opentelemetry-api, opentelemetry-sdk (optional dependencies).
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger(__name__)

# --- Optional dependency gate ---------------------------------------------------

_HAS_OTEL = False
_tracer_provider: Any = None
_meter_provider: Any = None

try:
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace as otel_trace
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

    _HAS_OTEL = True
except ImportError:
    pass


# --- No-op fallbacks -----------------------------------------------------------


class _NoOpSpan:
    """No-op span for when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: BaseException) -> None:
        pass

    def end(self) -> None:
        pass

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class _NoOpTracer:
    """No-op tracer for when OpenTelemetry is not available."""

    def start_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()

    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()


class _NoOpCounter:
    """No-op counter metric."""

    def add(self, amount: int | float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpHistogram:
    """No-op histogram metric."""

    def record(self, amount: int | float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpMeter:
    """No-op meter for when OpenTelemetry is not available."""

    def create_counter(self, name: str, **kwargs: Any) -> _NoOpCounter:
        return _NoOpCounter()

    def create_histogram(self, name: str, **kwargs: Any) -> _NoOpHistogram:
        return _NoOpHistogram()

    def create_up_down_counter(self, name: str, **kwargs: Any) -> _NoOpCounter:
        return _NoOpCounter()


# --- Initialization -------------------------------------------------------------


def init_telemetry(service_name: str, endpoint: str | None = None) -> bool:
    """Initialize the OpenTelemetry SDK with tracing and metrics.

    Args:
        service_name: Service name for the OTel resource.
        endpoint: Optional OTLP endpoint URL. If None, uses console exporters.

    Returns:
        True if OTel was initialized successfully, False if not available.
    """
    global _tracer_provider, _meter_provider  # noqa: PLW0603

    if not _HAS_OTEL:
        logger.info(
            "OpenTelemetry not available; telemetry disabled. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk"
        )
        return False

    resource = Resource.create({"service.name": service_name})

    # Tracing
    tracer_provider = TracerProvider(resource=resource)

    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            span_exporter = OTLPSpanExporter(endpoint=endpoint)
        except ImportError:
            logger.warning(
                "OTLP exporter not available, falling back to console. "
                "Install with: pip install opentelemetry-exporter-otlp"
            )
            span_exporter = ConsoleSpanExporter()
    else:
        span_exporter = ConsoleSpanExporter()

    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    otel_trace.set_tracer_provider(tracer_provider)
    _tracer_provider = tracer_provider

    # Metrics
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                OTLPMetricExporter,
            )

            metric_exporter = OTLPMetricExporter(endpoint=endpoint)
        except ImportError:
            metric_exporter = ConsoleMetricExporter()
    else:
        metric_exporter = ConsoleMetricExporter()

    reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    otel_metrics.set_meter_provider(meter_provider)
    _meter_provider = meter_provider

    logger.info("OpenTelemetry initialized: service=%s endpoint=%s", service_name, endpoint)
    return True


# --- Accessor functions ---------------------------------------------------------


def get_tracer(name: str) -> Any:
    """Return an OTel tracer, or a no-op tracer if OTel is not available.

    Args:
        name: Tracer instrumentation name (e.g. "ssidctl.core").

    Returns:
        A tracer instance (real or no-op).
    """
    if _HAS_OTEL and _tracer_provider is not None:
        return otel_trace.get_tracer(name)
    return _NoOpTracer()


def get_meter(name: str) -> Any:
    """Return an OTel meter, or a no-op meter if OTel is not available.

    Args:
        name: Meter instrumentation name (e.g. "ssidctl.core").

    Returns:
        A meter instance (real or no-op).
    """
    if _HAS_OTEL and _meter_provider is not None:
        return otel_metrics.get_meter(name)
    return _NoOpMeter()


# --- Convenience context manager ------------------------------------------------


@contextmanager
def span(name: str, attributes: dict[str, Any] | None = None) -> Generator[Any, None, None]:
    """Create a tracing span as a context manager.

    Args:
        name: Span name.
        attributes: Optional span attributes.

    Yields:
        The span object (real or no-op).
    """
    tracer = get_tracer("ssidctl")
    if _HAS_OTEL and _tracer_provider is not None:
        with tracer.start_as_current_span(name, attributes=attributes or {}) as s:
            yield s
    else:
        noop = _NoOpSpan()
        if attributes:
            for k, v in attributes.items():
                noop.set_attribute(k, v)
        yield noop


# --- Pre-defined metrics --------------------------------------------------------

# These are initialized lazily on first access so they work whether or not
# init_telemetry() has been called.

_metrics_cache: dict[str, Any] = {}


def gate_duration_histogram() -> Any:
    """Histogram tracking gate execution duration in seconds.

    Returns:
        A histogram instrument (real or no-op).
    """
    if "gate_duration" not in _metrics_cache:
        meter = get_meter("ssidctl.gates")
        _metrics_cache["gate_duration"] = meter.create_histogram(
            name="ems.gate.duration",
            description="Gate execution duration in seconds",
            unit="s",
        )
    return _metrics_cache["gate_duration"]


def evidence_write_counter() -> Any:
    """Counter tracking evidence write operations.

    Returns:
        A counter instrument (real or no-op).
    """
    if "evidence_write" not in _metrics_cache:
        meter = get_meter("ssidctl.evidence")
        _metrics_cache["evidence_write"] = meter.create_counter(
            name="ems.evidence.writes",
            description="Number of evidence write operations",
        )
    return _metrics_cache["evidence_write"]


def api_call_counter() -> Any:
    """Counter tracking external API calls.

    Returns:
        A counter instrument (real or no-op).
    """
    if "api_call" not in _metrics_cache:
        meter = get_meter("ssidctl.api")
        _metrics_cache["api_call"] = meter.create_counter(
            name="ems.api.calls",
            description="Number of external API calls",
        )
    return _metrics_cache["api_call"]
