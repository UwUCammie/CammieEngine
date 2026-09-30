#!/usr/bin/env python3
"""Audit natural-ending receipts against a chart matrix by runtime chart key.

This ledger records historical completion evidence for each exact
``(runtimeChart, difficulty)`` pair. It does not establish that a receipt came
from the current binary unless the caller supplies its SHA-256, and a natural
ending never establishes full source, visual, audio, UI, editor, or cutscene
parity.

Receipts may be JSON row objects, JSON arrays, JSON Lines, or sweep wrapper
objects with a ``rows`` array. Repeated copies of the same run record are
deduplicated without using ``matrixIndex`` as an identity.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_ending_summary(summary: Any) -> dict[str, Any] | None:
    """Return a compact ending marker only when its event accounting is valid."""
    if not isinstance(summary, dict):
        return None
    count = summary.get("count", 1)
    fields = {key: summary.get(key) for key in (
        "totalEvents", "dueEvents", "dispatchedEvents", "positionMs", "songLengthMs")}
    valid = (
        _is_count(count) and count == 1
        and all(_is_count(fields[key]) for key in
                ("totalEvents", "dueEvents", "dispatchedEvents"))
        and 0 <= fields["dueEvents"] <= fields["totalEvents"]
        and fields["dispatchedEvents"] >= 0
        and fields["totalEvents"] >= fields["dueEvents"]
        and fields["dueEvents"] == fields["dispatchedEvents"]
        and _is_number(fields["positionMs"])
        and _is_number(fields["songLengthMs"])
        and math.isfinite(fields["positionMs"])
        and math.isfinite(fields["songLengthMs"])
        and fields["songLengthMs"] > 0
        and fields["positionMs"] >= fields["songLengthMs"]
    )
    if not valid:
        return None
    return {
        "count": count,
        **fields,
        "time": summary.get("time"),
        "runToken": summary.get("runToken"),
    }


def natural_ending(record: dict[str, Any]) -> dict[str, Any] | None:
    """Recognize only a recorded, complete song-end marker.

    The marker is independent of the receipt's overall strict status: a run can
    reach the ending and still fail due to runtime diagnostics.
    """
    ending = _valid_ending_summary(record.get("naturalSongEnd"))
    if ending is not None:
        return ending

    marker = record.get("songEnd")
    if not isinstance(marker, dict) or marker.get("event") != "song_end":
        return None
    ending = _valid_ending_summary(marker)
    if ending is None:
        return None
    ending["event"] = "song_end"
    return ending


def _diagnostic_status(record: dict[str, Any]) -> str:
    status = record.get("status")
    diagnostic_fields = (
        "strictDiagnostics", "interpreterErrors", "unknownErrors", "diagnostics")
    has_diagnostics = any(
        isinstance(record.get(field), list) and bool(record[field])
        for field in diagnostic_fields)
    failed = (status == "failed"
              or record.get("strictDiagnosticsPassed") is False
              or record.get("strictRuntimeGatePassed") is False
              or has_diagnostics)
    if failed:
        return "failed"
    if status in {"blocked", "skipped", "source_media_blocker",
                  "empty_undeclared_raw_key", "unclassified_blocker"}:
        return "skipped"
    if status == "passed":
        return "passed"
    return "unknown"


def _effective_provenance(record: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    provenance: dict[str, Any] = {}
    # Wrapper values are defaults. A row's nested provenance is most specific
    # and must win over wrapper hashes when the two disagree.
    for source in (parent, parent.get("provenance"), record):
        if not isinstance(source, dict):
            continue
        for source_key, target_key in (("binarySha256", "binarySha256"),
                                       ("runtimeChartSha256", "runtimeChartSha256")):
            if source.get(source_key) is not None:
                provenance[target_key] = source[source_key]
    for source in (record.get("provenance"),):
        if isinstance(source, dict):
            provenance.update(source)
    return provenance


def _provenance_status(actual: Any, expected: Any) -> str:
    if not isinstance(actual, str) or not actual:
        return "unknown"
    if not isinstance(expected, str) or not expected:
        return "unknown"
    return "matched" if actual.casefold() == expected.casefold() else "mismatch"


def _current_build_status(provenance: dict[str, Any], expected_binary: str | None,
                          expected_chart: str | None) -> str:
    binary_status = _provenance_status(provenance.get("binarySha256"), expected_binary)
    chart_status = _provenance_status(provenance.get("runtimeChartSha256"), expected_chart)
    if "mismatch" in (binary_status, chart_status):
        return "mismatch"
    if binary_status == "matched" and chart_status == "matched":
        return "matched"
    return "unknown"


def _aggregate_status(statuses: Iterable[str]) -> str:
    observed = set(statuses)
    if not observed:
        return "missing"
    observed.discard("unknown")
    if not observed:
        return "unknown"
    if len(observed) > 1:
        return "mixed"
    return next(iter(observed))


def _record_key(record: dict[str, Any]) -> tuple[str, str] | None:
    runtime_chart = record.get("runtimeChart")
    difficulty = record.get("difficulty")
    if (not isinstance(runtime_chart, str) or not runtime_chart
            or not isinstance(difficulty, str) or not difficulty):
        return None
    return runtime_chart, difficulty


def _fingerprint(record: dict[str, Any], provenance: dict[str, Any],
                 ending: dict[str, Any] | None) -> str:
    diagnostic_values = {}
    for field in ("status", "reason", "strictDiagnosticsPassed",
                  "strictRuntimeGatePassed", "strictDiagnostics",
                  "interpreterErrors", "unknownErrors", "diagnostics", "runId"):
        if field in record:
            diagnostic_values[field] = record[field]
    payload = {
        "runtimeChart": record.get("runtimeChart"),
        "difficulty": record.get("difficulty"),
        "ending": ending,
        "diagnostics": diagnostic_values,
        "provenance": {key: provenance.get(key) for key in (
            "binarySha256", "runtimeChartSha256", "testMode", "playbackRate")},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _iter_receipt_records(path: Path) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], int]:
    """Load row records and their wrapper metadata; second return is bad lines."""
    content = path.read_text(encoding="utf-8")
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        document = None

    if document is not None:
        if isinstance(document, list):
            return [(item, {}) for item in document if isinstance(item, dict)], 0
        if not isinstance(document, dict):
            return [], 0
        for collection_name in ("rows", "completedRows", "records", "results"):
            rows = document.get(collection_name)
            if isinstance(rows, list):
                return ([(item, document) for item in rows if isinstance(item, dict)], 0)
        if _record_key(document) is not None:
            return [(document, {})], 0
        return [], 0

    records: list[tuple[dict[str, Any], dict[str, Any]]] = []
    malformed = 0
    for line in content.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(item, dict):
            records.append((item, {}))
    return records, malformed


def expand_receipts(receipt_files: Iterable[str | Path],
                    receipt_globs: Iterable[str]) -> list[Path]:
    paths: dict[str, Path] = {}
    for raw in receipt_files:
        path = Path(raw).expanduser()
        if not path.is_file():
            raise ValueError(f"receipt file not found: {path}")
        resolved = path.resolve()
        paths[str(resolved)] = resolved
    for pattern in receipt_globs:
        matches = [Path(item).resolve() for item in glob.glob(pattern, recursive=True)
                   if Path(item).is_file()]
        if not matches:
            raise ValueError(f"receipt glob matched no files: {pattern}")
        for path in matches:
            paths[str(path)] = path
    if not paths:
        raise ValueError("supply at least one --receipt or --receipt-glob")
    return sorted(paths.values(), key=lambda path: str(path))


def audit_matrix(matrix: dict[str, Any], receipt_paths: Iterable[Path],
                 current_build_sha256: str | None = None,
                 receipt_inputs: list[str] | None = None) -> dict[str, Any]:
    receipt_paths = list(receipt_paths)
    matrix_rows = matrix.get("rows")
    if not isinstance(matrix_rows, list) or not all(isinstance(row, dict) for row in matrix_rows):
        raise ValueError("matrix must contain a rows array of objects")

    targets: dict[tuple[str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str] | None] = []
    for row in matrix_rows:
        key = _record_key(row)
        ordered_keys.append(key)
        if key is None:
            continue
        if key in targets:
            raise ValueError(f"duplicate matrix runtimeChart+difficulty key: {key}")
        targets[key] = row

    attempts: dict[tuple[str, str], dict[str, dict[str, Any]]] = {
        key: {} for key in targets}
    receipt_record_count = 0
    malformed_line_count = 0
    unmatched_receipt_record_count = 0
    for path in receipt_paths:
        records, malformed = _iter_receipt_records(path)
        receipt_record_count += len(records)
        malformed_line_count += malformed
        for record, parent in records:
            key = _record_key(record)
            if key is None or key not in targets:
                unmatched_receipt_record_count += 1
                continue
            ending = natural_ending(record)
            provenance = _effective_provenance(record, parent)
            fingerprint = _fingerprint(record, provenance, ending)
            attempt = attempts[key].setdefault(fingerprint, {
                "receiptFiles": [],
                "record": record,
                "ending": ending,
                "provenance": provenance,
                "diagnosticStatus": _diagnostic_status(record),
            })
            display_path = str(path)
            if display_path not in attempt["receiptFiles"]:
                attempt["receiptFiles"].append(display_path)

    audited_rows: list[dict[str, Any]] = []
    for matrix_row, key in zip(matrix_rows, ordered_keys):
        if key is None:
            attempt_values: list[dict[str, Any]] = []
            key_status = "unkeyed"
        else:
            attempt_values = list(attempts[key].values())
            key_status = "keyed"

        ending_attempts = [attempt for attempt in attempt_values
                           if attempt["ending"] is not None]
        diagnostic_statuses = [attempt["diagnosticStatus"] for attempt in attempt_values]
        expected_chart = matrix_row.get("runtimeChartSha256")
        summarized_attempts = []
        build_states = []
        runtime_chart_states = []
        current_states = []
        for attempt in attempt_values:
            provenance = attempt["provenance"]
            build_state = _provenance_status(
                provenance.get("binarySha256"), current_build_sha256)
            chart_state = _provenance_status(
                provenance.get("runtimeChartSha256"), expected_chart)
            current_state = _current_build_status(
                provenance, current_build_sha256, expected_chart)
            build_states.append(build_state)
            runtime_chart_states.append(chart_state)
            if attempt["ending"] is not None:
                current_states.append(current_state)
            summarized_attempts.append({
                "receiptFiles": attempt["receiptFiles"],
                "naturalEnding": attempt["ending"] is not None,
                "ending": attempt["ending"],
                "diagnosticStatus": attempt["diagnosticStatus"],
                "status": attempt["record"].get("status"),
                "buildProvenanceStatus": build_state,
                "binarySha256": provenance.get("binarySha256"),
                "runtimeChartProvenanceStatus": chart_state,
                "runtimeChartSha256": provenance.get("runtimeChartSha256"),
                "currentBuildNaturalEndingValidation": current_state,
            })

        # An older build's ending remains historical but cannot invalidate an
        # observed ending for the requested binary/chart pair. Diagnostics are
        # still aggregated independently, including unresolved failed attempts.
        current_validation = ("matched" if "matched" in current_states
                              else _aggregate_status(current_states))
        if not ending_attempts:
            current_validation = "unknown" if attempt_values else "missing"
        audited_rows.append({
            "matrixIndex": matrix_row.get("matrixIndex"),
            "group": matrix_row.get("group"),
            "package": matrix_row.get("package"),
            "song": matrix_row.get("song"),
            "variant": matrix_row.get("variant"),
            "difficulty": matrix_row.get("difficulty"),
            "runtimeChart": matrix_row.get("runtimeChart"),
            "keyStatus": key_status,
            "historicalNaturalEnding": "covered" if ending_attempts else "missing",
            "endingEvidenceCount": len(ending_attempts),
            "uniqueAttemptCount": len(attempt_values),
            "diagnosticStatus": _aggregate_status(diagnostic_statuses),
            "diagnosticStatusCounts": {
                name: diagnostic_statuses.count(name)
                for name in ("passed", "failed", "skipped", "unknown")
            },
            "buildProvenanceStatus": _aggregate_status(build_states),
            "runtimeChartProvenanceStatus": _aggregate_status(runtime_chart_states),
            "currentBuildNaturalEndingValidation": current_validation,
            "attempts": summarized_attempts,
        })

    missing = [row for row in audited_rows
               if row["historicalNaturalEnding"] == "missing"]
    coverage_count = len(audited_rows) - len(missing)
    summary = {
        "matrixRows": len(audited_rows),
        "keyedMatrixRows": len(targets),
        "historicalNaturalEndingRows": coverage_count,
        "missingNaturalEndingRows": len(missing),
        "currentBuildNaturalEndingValidatedRows": sum(
            row["currentBuildNaturalEndingValidation"] == "matched"
            for row in audited_rows),
        "currentBuildNaturalEndingMismatchedRows": sum(
            row["currentBuildNaturalEndingValidation"] == "mismatch"
            for row in audited_rows),
        "currentBuildNaturalEndingUnknownRows": sum(
            row["currentBuildNaturalEndingValidation"] in {"unknown", "missing"}
            for row in audited_rows),
        "diagnosticStatusCounts": {
            name: sum(row["diagnosticStatus"] == name for row in audited_rows)
            for name in ("passed", "failed", "skipped", "unknown", "mixed", "missing")
        },
        "receiptFilesExamined": len(receipt_paths),
        "receiptRecordsExamined": receipt_record_count,
        "uniqueMatchedAttempts": sum(row["uniqueAttemptCount"] for row in audited_rows),
        "duplicateMatchedRecordsIgnored": max(
            0, receipt_record_count - unmatched_receipt_record_count
            - sum(row["uniqueAttemptCount"] for row in audited_rows)),
        "unmatchedReceiptRecords": unmatched_receipt_record_count,
        "malformedJsonLines": malformed_line_count,
    }
    return {
        "schema": 1,
        "scope": {
            "historicalNaturalEnding": (
                "A valid natural song-end marker from any supplied historical receipt. "
                "Diagnostic failure does not erase evidence that the row ended."),
            "currentBuildNaturalEndingValidation": (
                "Separate from historical coverage. A natural ending is matched to the "
                "current build only when its receipt records provenance.binarySha256 "
                "matching the supplied --current-build-sha256 and "
                "provenance.runtimeChartSha256 matching the matrix row hash. This verifies "
                "the binary/chart ending pair only, not all runtime dependencies. Missing "
                "provenance is unknown; mismatches are not promoted."),
            "fullParity": (
                "Not assessed. Natural endings do not establish source, visual, audio, UI, "
                "editor, menu, or cutscene parity."),
        },
        "matrix": {"rows": len(matrix_rows)},
        "currentBuildSha256": current_build_sha256,
        "receiptInputs": receipt_inputs or [],
        "summary": summary,
        "rows": audited_rows,
        "missingNaturalEndings": missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, type=Path,
                        help="JSON chart matrix with rows keyed by runtimeChart and difficulty")
    parser.add_argument("--receipt", action="append", default=[], metavar="FILE",
                        help="receipt JSON/JSONL file; may be repeated")
    parser.add_argument("--receipt-glob", "--receipts-glob", action="append", default=[],
                        metavar="PATTERN", help="receipt file glob; may be repeated")
    parser.add_argument("--output", required=True, type=Path,
                        help="write the audit JSON to this path")
    parser.add_argument("--current-build-sha256",
                        help="expected current binary SHA-256 for separate build validation")
    args = parser.parse_args(argv)

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    receipts = expand_receipts(args.receipt, args.receipt_glob)
    payload = audit_matrix(
        matrix, receipts, args.current_build_sha256,
        receipt_inputs=[*args.receipt, *args.receipt_glob])
    payload["matrix"]["path"] = str(args.matrix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
