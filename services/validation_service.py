"""Validation run persistence and analytics service."""

import json
import logging
from collections import Counter
from datetime import datetime

from database.models import MigrationObject, Stream, ValidationRun
from database.session import get_session

logger = logging.getLogger(__name__)


def record_run(
    object_id: int | None,
    user_id: int | None,
    total_records: int,
    passed_records: int,
    failed_records: int,
    validation_results: list[dict] | None = None,
) -> int:
    """Persist a validation run and return its id."""
    failures = [r for r in (validation_results or []) if r.get("Status") == "FAIL"]
    with get_session() as session:
        run = ValidationRun(
            object_id=object_id,
            user_id=user_id,
            run_date=datetime.utcnow(),
            total_records=total_records,
            passed_records=passed_records,
            failed_records=failed_records,
            failure_detail_json=json.dumps(failures[:500], ensure_ascii=False),
        )
        session.add(run)
        session.flush()
        return run.id


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------
def _success_rate(passed: int, total: int) -> float:
    return round((passed / total) * 100, 1) if total else 0.0


def global_metrics() -> dict:
    """Aggregate platform-wide metrics for the global dashboard."""
    with get_session() as session:
        streams = session.query(Stream).count()
        objects = session.query(MigrationObject).count()
        runs = session.query(ValidationRun).all()

        total_runs = len(runs)
        total_records = sum(r.total_records for r in runs)
        passed = sum(r.passed_records for r in runs)
        failed = sum(r.failed_records for r in runs)

        return {
            "total_streams": streams,
            "total_objects": objects,
            "total_runs": total_runs,
            "total_records": total_records,
            "passed_records": passed,
            "failed_records": failed,
            "success_rate": _success_rate(passed, total_records),
            "failure_rate": round(100 - _success_rate(passed, total_records), 1) if total_records else 0.0,
        }


def metrics_by_stream() -> list[dict]:
    """Return per-stream aggregated metrics."""
    with get_session() as session:
        streams = session.query(Stream).order_by(Stream.stream_name).all()
        out = []
        for s in streams:
            object_ids = [o.id for o in s.objects]
            runs = (
                session.query(ValidationRun)
                .filter(ValidationRun.object_id.in_(object_ids or [-1]))
                .all()
            )
            total = sum(r.total_records for r in runs)
            passed = sum(r.passed_records for r in runs)
            failed = sum(r.failed_records for r in runs)
            out.append(
                {
                    "stream": s.stream_name,
                    "objects": len(object_ids),
                    "runs": len(runs),
                    "total_records": total,
                    "passed_records": passed,
                    "failed_records": failed,
                    "success_rate": _success_rate(passed, total),
                }
            )
        return out


def metrics_for_stream(stream_id: int) -> dict:
    """Aggregate metrics and object-wise breakdown for a single stream."""
    with get_session() as session:
        stream = session.get(Stream, stream_id)
        if not stream:
            return {}

        object_rows = []
        total_runs = total_records = total_passed = 0
        for obj in stream.objects:
            runs = (
                session.query(ValidationRun)
                .filter(ValidationRun.object_id == obj.id)
                .all()
            )
            t = sum(r.total_records for r in runs)
            p = sum(r.passed_records for r in runs)
            f = sum(r.failed_records for r in runs)
            total_runs += len(runs)
            total_records += t
            total_passed += p
            object_rows.append(
                {
                    "object": obj.object_name,
                    "runs": len(runs),
                    "total_records": t,
                    "failed_records": f,
                    "success_rate": _success_rate(p, t),
                }
            )

        return {
            "stream": stream.stream_name,
            "total_objects": len(stream.objects),
            "total_runs": total_runs,
            "total_records": total_records,
            "success_rate": _success_rate(total_passed, total_records),
            "objects": object_rows,
        }


def metrics_for_object(object_id: int) -> dict:
    """Aggregate metrics, trend, and top failures for a single object."""
    with get_session() as session:
        obj = session.get(MigrationObject, object_id)
        if not obj:
            return {}

        runs = (
            session.query(ValidationRun)
            .filter(ValidationRun.object_id == object_id)
            .order_by(ValidationRun.run_date.asc())
            .all()
        )
        total = sum(r.total_records for r in runs)
        passed = sum(r.passed_records for r in runs)

        # Trend over time
        trend = [
            {
                "run_date": r.run_date.strftime("%Y-%m-%d %H:%M"),
                "total_records": r.total_records,
                "passed_records": r.passed_records,
                "failed_records": r.failed_records,
                "success_rate": _success_rate(r.passed_records, r.total_records),
            }
            for r in runs
        ]

        # Top failing fields / rule violations across runs
        field_counter: Counter = Counter()
        rule_counter: Counter = Counter()
        for r in runs:
            for f in json.loads(r.failure_detail_json or "[]"):
                field_counter[f.get("Field", "Unknown")] += 1
                rule_counter[f.get("Error Description", "Unknown")] += 1

        return {
            "object": obj.object_name,
            "stream": obj.stream.stream_name,
            "total_runs": len(runs),
            "total_records": total,
            "success_rate": _success_rate(passed, total),
            "trend": trend,
            "top_failures": [{"field": k, "count": v} for k, v in field_counter.most_common(10)],
            "top_violations": [{"violation": k, "count": v} for k, v in rule_counter.most_common(10)],
        }
