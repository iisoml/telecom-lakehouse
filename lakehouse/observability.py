import json
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

_provider = TracerProvider()
_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(_provider)
tracer = trace.get_tracer("telecom-lakehouse")

LINEAGE_FILE = Path("data/lineage.jsonl")


def _emit(event_type, job, run_id, inputs, outputs):
    LINEAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "eventType": event_type,
        "eventTime": datetime.now(UTC).isoformat(),
        "run": {"runId": run_id},
        "job": {"namespace": "telecom-lakehouse", "name": job},
        "inputs": [{"namespace": "local", "name": i} for i in inputs],
        "outputs": [{"namespace": "local", "name": o} for o in outputs],
        "producer": "https://github.com/your-user/telecom-lakehouse",
    }
    with LINEAGE_FILE.open("a") as f:
        f.write(json.dumps(event) + "\n")


@contextmanager
def run_step(name, inputs=(), outputs=()):
    run_id = str(uuid.uuid4())
    _emit("START", name, run_id, inputs, outputs)
    with tracer.start_as_current_span(name) as span:
        try:
            yield span
            _emit("COMPLETE", name, run_id, inputs, outputs)
        except Exception:
            _emit("FAIL", name, run_id, inputs, outputs)
            raise