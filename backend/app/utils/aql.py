"""AQL utilities.

This module provides two simple helpers used by the rest of the app:

- AQLCalculator: given lot size and an AQL level, produce a basic sampling
  plan summary (sample size and allowed defects). The implementation here is a
  pragmatic approximation sufficient for UI flow and testing. If you later wire
  in the official tables (e.g. from Excel) you can replace the logic here.

- AQLResultProcessor: evaluate inspection responses against an AQL
  configuration. The current implementation returns a conservative summary and
  pass/fail decision using counts supplied; it is deliberately minimal to avoid
  breaking existing routes when detailed logic is not yet required.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        iv = int(value)
        return iv if iv >= 0 else default
    except Exception:
        return default


class AQLCalculator:
    """Lightweight calculator for sampling criteria.

    The logic below is intentionally simple and documented. It maps lot-size to a
    sample-size via coarse buckets roughly inspired by common Level II plans and
    then derives allowed defects from the target AQL. Critical defaults to 0.
    """

    # Coarse lot-size to sample-size mapping (cap at 2000)
    LOT_TO_SAMPLE_BUCKETS = [
        (8, 2), (15, 3), (25, 5), (50, 8), (90, 13), (150, 20), (280, 32),
        (500, 50), (1200, 80), (3200, 125), (10000, 200), (35000, 315),
        (150000, 500), (500000, 800), (10**9, 1250),
    ]

    @classmethod
    def _estimate_sample_size(cls, lot_size: int) -> int:
        lot = max(1, _safe_int(lot_size, 1))
        for upper, sample in cls.LOT_TO_SAMPLE_BUCKETS:
            if lot <= upper:
                return sample
        return 1250

    @classmethod
    def calculate_aql_criteria(cls, lot_size: int, aql_level: float = 2.5) -> Dict[str, int]:
        sample_size = cls._estimate_sample_size(lot_size)

        # Derive allowed defects from AQL percentage. The constants provide a
        # reasonable spread for major/minor bands while keeping critical at 0.
        aql = float(aql_level or 2.5)
        major_allowed = max(0, int(round(sample_size * (aql / 100.0))))
        minor_allowed = max(0, int(round(sample_size * ((aql * 1.6) / 100.0))))
        critical_allowed = 0

        return {
            "sample_size": sample_size,
            "major_defects_allowed": major_allowed,
            "minor_defects_allowed": minor_allowed,
            "critical_defects_allowed": critical_allowed,
        }


class AQLResultProcessor:
    """Minimal processor for inspection results against AQL config.

    This routine computes a simple summary structure and a pass/fail using the
    counts available in responses (if present). If specific mapping logic is not
    available, it returns a default pass with zero counts.
    """

    @staticmethod
    def process_inspection_results(
        responses: Dict[str, Any],
        aql_config: Dict[str, Any],
        defect_categories: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        # Default zero counts
        defect_counts = {"critical": 0, "major": 0, "minor": 0}

        # If responses carry explicit counts, honour them
        if isinstance(responses, dict):
            defect_counts["critical"] = _safe_int(responses.get("critical_defects"), 0)
            defect_counts["major"] = _safe_int(responses.get("major_defects"), 0)
            defect_counts["minor"] = _safe_int(responses.get("minor_defects"), 0)

        # Allowed from config (fallback to 0)
        allowed_critical = _safe_int(aql_config.get("critical_defects_allowed"), 0)
        allowed_major = _safe_int(aql_config.get("major_defects_allowed"), 0)
        allowed_minor = _safe_int(aql_config.get("minor_defects_allowed"), 0)

        # Determine pass/fail
        passed = (
            defect_counts["critical"] <= allowed_critical
            and defect_counts["major"] <= allowed_major
            and defect_counts["minor"] <= allowed_minor
        )
        rejection_reasons = []
        if not passed:
            if defect_counts["critical"] > allowed_critical:
                rejection_reasons.append("CRITICAL_EXCEEDED")
            if defect_counts["major"] > allowed_major:
                rejection_reasons.append("MAJOR_EXCEEDED")
            if defect_counts["minor"] > allowed_minor:
                rejection_reasons.append("MINOR_EXCEEDED")

        return {
            "defect_counts": defect_counts,
            "passed": bool(passed),
            "rejection_reasons": rejection_reasons,
        }


