import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import json

@dataclass
class Span:
    id: str = field(default_factory=lambda: f"span-{uuid.uuid4().hex[:8]}")
    trace_id: str = ""
    name: str = ""
    parent_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

class ControlPlaneTracer:
    """
    Structured logging and distributed tracing for Control Plane jobs.
    """
    def __init__(self):
        self.active_spans: Dict[str, Span] = {}
        self.completed_spans: List[Span] = []

    def start_trace(self, name: str, trace_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Span:
        t_id = trace_id or f"trace-{uuid.uuid4().hex[:12]}"
        span = Span(trace_id=t_id, name=name, metadata=metadata or {})
        self.active_spans[span.id] = span
        return span

    def start_child_span(self, parent_span: Span, name: str, metadata: Optional[Dict[str, Any]] = None) -> Span:
        span = Span(trace_id=parent_span.trace_id, parent_id=parent_span.id, name=name, metadata=metadata or {})
        self.active_spans[span.id] = span
        return span

    def end_span(self, span_id: str):
        if span_id in self.active_spans:
            span = self.active_spans.pop(span_id)
            span.end_time = time.time()
            self.completed_spans.append(span)
            # Log structured data
            self._log_span(span)

    def log_event(self, span_id: str, name: str, payload: Optional[Dict[str, Any]] = None):
        if span_id in self.active_spans:
            self.active_spans[span_id].events.append({
                "name": name,
                "payload": payload or {},
                "timestamp": time.time()
            })

    def _log_span(self, span: Span):
        duration = (span.end_time - span.start_time) * 1000 if span.end_time else 0
        log_entry = {
            "level": "INFO",
            "type": "SPAN_END",
            "trace_id": span.trace_id,
            "span_id": span.id,
            "name": span.name,
            "duration_ms": duration,
            "metadata": span.metadata,
            "events_count": len(span.events)
        }
        print(f"[OBSERVABILITY] {json.dumps(log_entry)}")
