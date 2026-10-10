#!/usr/bin/env python3
"""Audit chart-facing scripting APIs against the local engine bindings.

Psych Lua, Psych HScript, and Nightmare Vision HScript are deliberately
inventoried as separate dialects. This is a static source audit: an explicit
binding or callback dispatch is reported as implemented, while text mentions
and broad reflection remain weaker evidence. Donor checkouts are optional so
fixture tests and the checked-in report continue to work in CI.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PSYCH_ROOT = REPO_ROOT.parent / "fnf_sources" / "FNF-PsychEngine"
DEFAULT_NV_ROOT = REPO_ROOT.parent / "fnf_sources" / "NightmareVision"
DEFAULT_EXAMPLES_ROOT = REPO_ROOT.parent / "fnf_example_mods"


@dataclass(frozen=True)
class SourceRef:
    path: str
    line: int


@dataclass
class ApiEntry:
    dialect: str
    group: str
    name: str
    kind: str
    source: list[SourceRef] = field(default_factory=list)
    status: str = "unverified"
    engine_evidence: list[str] = field(default_factory=list)
    contract: dict[str, object] = field(default_factory=dict)


@dataclass
class SourceMetadata:
    label: str
    available: bool
    path: str
    revision: str = "unavailable"
    version: str = "unavailable"
    tracked_tree: str = "unavailable"
    source_files: int = 0


def strip_haxe_comments(text: str) -> str:
    """Blank Haxe comments while preserving strings, offsets, and line breaks."""
    out = list(text)
    i = 0
    state = "code"
    quote = ""
    while i < len(text):
        char = text[i]
        following = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if char in ("'", '"'):
                quote = char
                state = "string"
            elif char == "/" and following == "/":
                out[i] = out[i + 1] = " "
                i += 1
                state = "line"
            elif char == "/" and following == "*":
                out[i] = out[i + 1] = " "
                i += 1
                state = "block"
        elif state == "string":
            if char == "\\":
                i += 1
            elif char == quote:
                state = "code"
        elif state == "line":
            if char == "\n":
                state = "code"
            else:
                out[i] = " "
        elif state == "block":
            if char == "*" and following == "/":
                out[i] = out[i + 1] = " "
                i += 1
                state = "code"
            elif char != "\n":
                out[i] = " "
        i += 1
    return "".join(out)


def iter_haxe_files(root: Path) -> Iterable[Path]:
    source = root / "source"
    if not source.is_dir():
        return ()
    return sorted(source.rglob("*.hx"))


def _read_code(path: Path) -> str:
    try:
        return strip_haxe_comments(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return ""


def _ref(root: Path, path: Path, line: int) -> SourceRef:
    try:
        name = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        name = str(path.resolve())
    return SourceRef(name, line)


def _line_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _split_top_level(text: str, separator: str = ",") -> list[tuple[str, int]]:
    """Split an expression at top-level separators, preserving each offset."""
    result: list[tuple[str, int]] = []
    start = 0
    stack: list[str] = []
    quote = ""
    pairs = {"(": ")", "[": "]", "{": "}"}
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 1
            elif char == quote:
                quote = ""
        elif char in ("'", '"'):
            quote = char
        elif char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
        elif not stack and char == separator:
            result.append((text[start:i].strip(), start))
            start = i + 1
        i += 1
    if text[start:].strip():
        result.append((text[start:].strip(), start))
    return result


def _parameter_contract(parameter_text: str) -> list[dict[str, object]]:
    parameters: list[dict[str, object]] = []
    for raw, _ in _split_top_level(parameter_text):
        optional = raw.startswith("?")
        parameter = raw[1:].strip() if optional else raw
        parts = _split_top_level(parameter, "=")
        declaration = parts[0][0].strip()
        default = parts[1][0].strip() if len(parts) > 1 else None
        if ":" in declaration:
            name, declared_type = declaration.split(":", 1)
            name = name.strip()
            declared_type = declared_type.strip() or None
        else:
            name, declared_type = declaration.strip(), None
        if not re.fullmatch(r"[A-Za-z_$][\w$]*", name):
            parameters.append({"source": raw, "parsed": False})
            continue
        parameters.append({
            "name": name,
            "type": declared_type,
            "optional": optional,
            "omittable": optional or default is not None,
            "default": default,
            "default_evidence": "source-expression" if default is not None else None,
        })
    return parameters


def _function_contract(code: str, start: int, limit: int | None = None) -> dict[str, object] | None:
    """Parse an inline Haxe function/arrow signature and bounded body evidence."""
    if limit is None:
        limit = len(code)
    expression = code[start:limit]
    prefix = re.match(r"\s*function(?:\s+[A-Za-z_$][\w$]*)?\s*\(", expression)
    params_open = -1
    shape = "function"
    if prefix:
        params_open = start + prefix.end() - 1
    else:
        arrow = re.match(r"\s*\(", expression)
        if arrow:
            maybe_close = _balanced_region(expression, arrow.end() - 1, "(", ")")
            after = arrow.end() - 1 + len(maybe_close)
            if re.match(r"\s*->", expression[after:]):
                params_open = start + arrow.end() - 1
                shape = "arrow"
        else:
            single = re.match(r"\s*([A-Za-z_$][\w$]*)\s*->", expression)
            if single:
                body = expression[single.end():].strip()
                return_evidence = []
                if body and not body.startswith("{"):
                    return_evidence.append({"expression": body.rstrip(";"), "kind": "implicit-arrow-result"})
                return {
                    "shape": "arrow",
                    "signature": single.group(1) + " ->",
                    "parameters": [{"name": single.group(1), "type": None, "optional": False,
                                    "omittable": False, "default": None}],
                    "declared_return_type": None,
                    "return_evidence": return_evidence,
                    "body_calls": [],
                    "body_writes": [],
                }
    if params_open < 0:
        return None
    params_region = _balanced_region(code, params_open, "(", ")")
    if not params_region.endswith(")"):
        return None
    params_text = params_region[1:-1]
    close = params_open + len(params_region)
    tail = code[close:limit]
    cursor = len(tail) - len(tail.lstrip())
    tail = tail[cursor:]
    return_type = None
    if tail.startswith(":"):
        type_match = re.match(r":\s*([^\{=\n]+?)(?=\s*(?:\{|=>)|$)", tail)
        if type_match:
            return_type = type_match.group(1).strip()
            tail = tail[type_match.end():].lstrip()
    body_start = close + cursor + (len(code[close + cursor:limit]) - len(tail))
    body = ""
    if shape == "arrow":
        arrow = re.match(r"->", tail)
        if arrow:
            body_start += arrow.end()
            body = code[body_start:limit].strip()
    elif tail.startswith("{"):
        body_region = _balanced_region(code, body_start, "{", "}")
        body = body_region[1:-1] if body_region.endswith("}") else body_region[1:]
    elif tail.startswith("=>"):
        body_start += 2
        body = code[body_start:limit].strip()
    elif tail:
        body = code[body_start:limit].strip()

    returns = []
    return_regex = re.compile(r"\breturn\s+([^;\n}]+)")
    for match in return_regex.finditer(body):
        returns.append({"expression": match.group(1).strip(), "kind": "explicit-return",
                        "line": _line_at(code, body_start + match.start())})
        if len(returns) >= 8:
            break
    if shape == "arrow" and body.strip() and not returns and not body.lstrip().startswith("{"):
        returns.append({"expression": body.strip().rstrip(";"), "kind": "implicit-arrow-result",
                        "line": _line_at(code, body_start)})
    calls = []
    for match in re.finditer(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*\(", body):
        name = match.group(1)
        if name in {"if", "for", "while", "switch", "catch", "function"}:
            continue
        calls.append({"target": name, "line": _line_at(code, body_start + match.start())})
        if len(calls) >= 16:
            break
    writes = []
    for match in re.finditer(r"\b([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\s*(?:=|\+=|-=|\*=|/=)", body):
        writes.append({"target": match.group(1), "line": _line_at(code, body_start + match.start())})
        if len(writes) >= 16:
            break
    throws = []
    for match in re.finditer(r"\bthrow\s+([^;\n}]+)", body):
        throws.append({"expression": match.group(1).strip(), "line": _line_at(code, body_start + match.start())})
        if len(throws) >= 8:
            break
    parameter_contract = _parameter_contract(params_text)
    signature = "function(" + params_text.strip() + ")"
    if return_type:
        signature += ":" + return_type
    return {
        "shape": shape,
        "signature": signature,
        "parameters": parameter_contract,
        "declared_return_type": return_type,
        "return_evidence": returns,
        "body_calls": calls,
        "body_writes": writes,
        "failure_evidence": throws,
    }


def _extract_call_arguments(code: str, opening: int) -> tuple[list[str], int]:
    region = _balanced_region(code, opening, "(", ")")
    if not region.endswith(")"):
        return [], opening + len(region)
    return [part for part, _ in _split_top_level(region[1:-1])], opening + len(region)


def _is_function_declaration(code: str, start: int) -> bool:
    line_start = code.rfind("\n", 0, start) + 1
    return re.search(r"\bfunction\s+$", code[max(line_start, start - 120):start]) is not None


def _doc_comment(raw: str, offset: int) -> str | None:
    """Return a directly-leading documentation block without guessing semantics."""
    end = offset
    prefix = raw[:offset]
    whitespace = re.search(r"\s*$", prefix)
    end = whitespace.start() if whitespace else offset
    close = prefix.rfind("*/", 0, end)
    if close < 0:
        return None
    opening = prefix.rfind("/**", 0, close)
    if opening < 0:
        return None
    between = prefix[close + 2:end]
    if between.strip():
        return None
    return prefix[opening:close + 2].strip()


UNIT_TERMS = re.compile(
    r"\b(?:milliseconds?|msecs?|ms|seconds?|secs?|frames?|pixels?|px|degrees?|radians?|beats?|steps?|percent(?:age)?|normalized|0\s*[-–]\s*1)\b",
    re.IGNORECASE,
)


def _unit_evidence(documentation: str | None) -> list[str]:
    if not documentation:
        return []
    return list(dict.fromkeys(match.group(0) for match in UNIT_TERMS.finditer(documentation)))


def _callable_expression_contract(code: str, expression: str, offset: int) -> dict[str, object]:
    leading = len(expression) - len(expression.lstrip())
    start = offset + leading
    local = code[start : start + len(expression.strip())]
    parsed = _function_contract(code, start, min(len(code), start + len(local)))
    if parsed is not None:
        parsed["binding"] = "inline-callable"
        parsed["binding_expression"] = local.split("{", 1)[0].strip()[:240]
        parsed["signature_status"] = "source-signature"
        return parsed
    identifier = local.strip()
    if re.fullmatch(r"[A-Za-z_$][\w$]*", identifier):
        declaration = re.search(rf"\bfunction\s+{re.escape(identifier)}\s*\(", code)
        if declaration:
            shape = _function_contract(code, declaration.start(), len(code))
            if shape is not None:
                shape["binding"] = "named-function-reference"
                shape["binding_expression"] = identifier
                shape["signature_status"] = "resolved-source-signature"
                shape["declaration_line"] = _line_at(code, declaration.start())
                return shape
        return {
            "binding": "function-reference",
            "binding_expression": identifier,
            "signature_status": "unresolved-reference",
            "signature": None,
            "parameters": [],
            "declared_return_type": None,
            "return_evidence": [],
            "body_calls": [],
            "body_writes": [],
        }
    return {
        "binding": "value-expression",
        "binding_expression": local[:600],
        "signature_status": "not-callable-or-not-statically-resolved",
        "signature": None,
        "parameters": [],
        "declared_return_type": None,
        "return_evidence": [],
        "body_calls": [],
        "body_writes": [],
    }


def _registration_expression(code: str, match: re.Match[str]) -> tuple[str, int] | None:
    opening = code.find("(", match.start())
    if opening < 0:
        return None
    region = _balanced_region(code, opening, "(", ")")
    if not region.endswith(")"):
        return None
    arguments = _split_top_level(region[1:-1])
    if len(arguments) < 2:
        return None
    expression, relative = arguments[-1]
    raw_inner = region[1:-1]
    leading = len(raw_inner[relative:]) - len(raw_inner[relative:].lstrip())
    return expression, opening + 1 + relative + leading


def _set_value_expression(code: str, match: re.Match[str]) -> tuple[str, int] | None:
    opening = code.find("(", match.start())
    if opening < 0:
        return None
    region = _balanced_region(code, opening, "(", ")")
    if not region.endswith(")"):
        return None
    arguments = _split_top_level(region[1:-1])
    if len(arguments) < 2:
        return None
    expression, relative = arguments[-1]
    raw_inner = region[1:-1]
    leading = len(raw_inner[relative:]) - len(raw_inner[relative:].lstrip())
    return expression, opening + 1 + relative + leading


def _registration_contract(root: Path, path: Path, code: str, raw: str, regex: re.Pattern[str], name: str) -> dict[str, object]:
    match = next((item for item in _code_matches(code, regex) if item.group(2) == name), None)
    if match is None:
        return {"signature_status": "not-found", "signature": None, "parameters": []}
    expression = _registration_expression(code, match)
    if expression is None:
        return {"signature_status": "registration-shape-unparsed", "signature": None, "parameters": []}
    callback_expr, offset = expression
    contract = _callable_expression_contract(code, callback_expr, offset)
    documentation = _doc_comment(raw, match.start())
    contract.update({
        "registration_expression": callback_expr[:240],
        "registration_line": _line_at(code, match.start()),
        "documentation": documentation,
        "units": _unit_evidence(documentation),
        "units_status": "documented" if _unit_evidence(documentation) else "not-stated-in-nearby-documentation",
    })
    contract["side_effect_evidence"] = {
        "calls": contract.get("body_calls", []),
        "writes": contract.get("body_writes", []),
        "classification": "syntactic source observations, not a complete semantic effect analysis",
    }
    contract["failure_evidence"] = contract.get("failure_evidence", [])
    contract["failure_behavior"] = "source-throw-observed" if contract["failure_evidence"] else "not-stated-in-nearby-source"
    return contract


def _seed_contract(root: Path, path: Path, code: str, raw: str, regex: re.Pattern[str], name: str) -> dict[str, object]:
    match = next((item for item in _code_matches(code, regex) if item.group(2) == name), None)
    if match is None:
        return {"binding_status": "not-found", "binding_expression": None}
    expression = _set_value_expression(code, match)
    if expression is None:
        return {"binding_status": "source-binding", "binding_expression": None}
    binding, offset = expression
    callable_contract = _callable_expression_contract(code, binding, offset)
    is_callable = callable_contract.get("signature_status") in {"source-signature", "resolved-source-signature"}
    documentation = _doc_comment(raw, match.start())
    return {
        **callable_contract,
        "binding_status": "callable" if is_callable else "seeded-value",
        "binding_expression": binding[:240],
        "seed_line": _line_at(code, match.start()),
        "documentation": documentation,
        "units": _unit_evidence(documentation),
        "units_status": "documented" if _unit_evidence(documentation) else "not-stated-in-nearby-documentation",
        "side_effect_evidence": {
            "calls": callable_contract.get("body_calls", []),
            "writes": callable_contract.get("body_writes", []),
            "classification": "syntactic source observations, not a complete semantic effect analysis",
        },
        "failure_behavior": "not-stated-in-nearby-source",
        "failure_evidence": callable_contract.get("failure_evidence", []),
    }


def _method_contract(code: str, name: str, line: int) -> dict[str, object]:
    line_offset = sum(len(part) for part in code.splitlines(keepends=True)[: max(0, line - 1)])
    declaration = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", code[line_offset:])
    if declaration is None:
        return {"signature_status": "not-found", "signature": None, "parameters": []}
    start = line_offset + declaration.start()
    parsed = _function_contract(code, start, len(code))
    if parsed is None:
        return {"signature_status": "unparsed-method-signature", "signature": None, "parameters": []}
    parsed["signature"] = f"function {name}" + parsed["signature"][len("function"):]
    parsed["signature_status"] = "source-signature"
    return parsed


def _field_contract(code: str, name: str, line: int) -> dict[str, object]:
    lines = code.splitlines(keepends=True)
    if not 1 <= line <= len(lines):
        return {"signature_status": "not-found", "signature": None, "parameters": []}
    text = lines[line - 1].strip()
    match = re.search(rf"\b(?:var|final)\s+{re.escape(name)}\b([^;]*)", text)
    if match is None:
        return {"signature_status": "field-declaration-unparsed", "signature": None, "parameters": []}
    tail = match.group(1).strip()
    return {"signature_status": "source-field-declaration", "signature": name + tail, "field_type_and_default": tail}


def _call_result_use(code: str, start: int, end: int) -> str:
    left = max(code.rfind(";", 0, start), code.rfind("{", 0, start), code.rfind("}", 0, start)) + 1
    right_candidates = [position for position in (code.find(";", end), code.find("\n", end), code.find("}", end)) if position >= 0]
    right = min(right_candidates) if right_candidates else min(len(code), end + 160)
    statement = re.sub(r"\s+", " ", code[left:right]).strip()
    if re.search(r"(?:==|!=)\s*(?:(?:[A-Za-z_$][\w$]*\.)?)(?:STOP_FUNC|Function_Stop|STOP_HSCRIPT|STOP_ALL|CONTINUE_FUNC|Function_Continue|HALT_FUNC|Function_Halt)\b", statement):
        return "compared-to-script-sentinel"
    if re.match(r"(?:final|var)\s+\w+\s*[:=]", statement):
        return "assigned-to-local"
    if statement.startswith("return "):
        return "returned-to-caller"
    if statement.startswith("if "):
        return "used-in-conditional"
    return "return-value-not-observed-in-containing-statement"


SCRIPT_CALL = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\.\s*call\s*\(")
PSYCH_DISPATCH_CALL = re.compile(r"\b(?:callOnScripts|callOnLuas|callOnHScript|callOnHaxe|callOnLua)\s*\(")


def _literal_callback_choices(expression: str) -> list[str]:
    """Resolve only a literal callback or a simple literal-valued ternary."""
    value = expression.strip()
    literal = re.fullmatch(r"(['\"])([A-Za-z_$][\w$]*)\1", value)
    if literal:
        return [literal.group(2)]
    ternary = re.fullmatch(
        r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\?\s*"
        r"(['\"])([A-Za-z_$][\w$]*)\1\s*:\s*(['\"])([A-Za-z_$][\w$]*)\3",
        value,
    )
    if ternary:
        return list(dict.fromkeys((ternary.group(2), ternary.group(4))))
    return []


def _psych_runtime_dispatch_inventory(
    engine_root: Path,
) -> tuple[dict[str, list[SourceRef]], list[dict[str, object]]]:
    """Recognize PsychRuntimeBindings.dispatch routes from real PlayState call sites.

    The dispatcher is only evidence when the public static adapter exists and
    forwards to its scope dispatcher. Literal names at PlayState call sites are
    direct routes. Variable callback names count only for the narrowly
    recognized source pre-hit and post-hit adapters when their real hit paths
    call the adapters.
    """
    routes: dict[str, list[SourceRef]] = defaultdict(list)
    dynamic_sites: list[dict[str, object]] = []
    runtime_path = engine_root / "source" / "PsychRuntimeBindings.hx"
    play_path = engine_root / "source" / "PlayState.hx"
    runtime_code = _read_code(runtime_path) if runtime_path.is_file() else ""
    play_code = _read_code(play_path) if play_path.is_file() else ""
    dispatch_method = _named_function_region(runtime_code, "dispatch")
    if not re.search(
        r"\bpublic\s+static\s+function\s+dispatch\s*\(\s*host\s*:\s*PlayState\s*,\s*"
        r"name\s*:\s*String\s*,\s*args\s*:\s*Array\s*<\s*Dynamic\s*>",
        runtime_code,
    ) or dispatch_method is None or not re.search(
        r"\breturn\s+dispatchScopes\s*\(\s*host\s*,\s*name\s*,\s*args\s*,\s*family\b",
        dispatch_method[0],
    ):
        return routes, dynamic_sites

    pre_region = _named_function_region(play_code, "dispatchPsychNoteHitPre")
    pre_choices: list[str] = []
    pre_branch_ref: SourceRef | None = None
    pre_native_refs: list[SourceRef] = []
    if pre_region is not None:
        pre_body, pre_offset = pre_region
        branch = re.search(
            r"\bvar\s+callback\s*(?::\s*[^=;]+)?=\s*([^;]+)", pre_body,
        )
        if branch is not None:
            choices = _literal_callback_choices(branch.group(1))
            if set(choices) == {"goodNoteHitPre", "opponentNoteHitPre"}:
                pre_choices = choices
                pre_branch_ref = _ref(
                    engine_root, play_path,
                    _line_at(play_code, pre_offset + branch.start()),
                )
                for caller_name in ("goodNoteHit", "dispatchHxcAutoNoteHit"):
                    caller = _named_function_region(play_code, caller_name)
                    if caller is None:
                        continue
                    caller_body, caller_offset = caller
                    for invocation in _code_matches(
                        caller_body, re.compile(r"\bdispatchPsychNoteHitPre\s*\("),
                    ):
                        pre_native_refs.append(_ref(
                            engine_root, play_path,
                            _line_at(play_code, caller_offset + invocation.start()),
                        ))
                if not pre_native_refs:
                    pre_choices = []
                    pre_branch_ref = None

    post_region = _named_function_region(play_code, "dispatchPsychNoteHit")
    post_choices: list[str] = []
    post_branch_ref: SourceRef | None = None
    post_native_refs: list[SourceRef] = []
    if post_region is not None:
        post_body, post_offset = post_region
        branch = re.search(r"\bvar\s+callback\s*(?::\s*[^=;]+)?=\s*([^;]+)", post_body)
        callback_adapter = re.search(r"\bPsychNoteCallbacks\.dispatch\s*\(\s*callback\s*,", post_body)
        runtime_bridge = re.search(
            r"function\s*\(\s*name\s*,\s*args\s*,\s*family\s*\)\s*return\s+"
            r"PsychRuntimeBindings\.dispatch\s*\(\s*this\s*,\s*name\s*,\s*args\s*,\s*family\s*\)",
            post_body,
        )
        finish = _named_function_region(play_code, "finishGoodNoteHit")
        finish_wires_adapter = False
        if finish is not None:
            finish_body, finish_offset = finish
            guarded_call = re.search(
                r"\bif\s*\(\s*psychSource\s*\)\s*dispatchPsychNoteHit\s*\(\s*note\s*,\s*playerOne\s*\)",
                finish_body,
            )
            finish_wires_adapter = guarded_call is not None and re.search(
                r"\bvar\s+psychSource\s*=\s*sourceScoreLedgerActive\s*\(\s*\)\s*&&\s*!sourceScoreNightmare\b",
                finish_body,
            ) is not None
            if guarded_call is not None and finish_wires_adapter:
                post_native_refs.append(_ref(
                    engine_root, play_path,
                    _line_at(play_code, finish_offset + guarded_call.start()),
                ))
        choices = _literal_callback_choices(branch.group(1)) if branch is not None else []
        if (set(choices) == {"goodNoteHit", "opponentNoteHit"}
                and callback_adapter is not None and runtime_bridge is not None and finish_wires_adapter):
            for caller_name in ("goodNoteHit", "dispatchHxcAutoNoteHit"):
                caller = _named_function_region(play_code, caller_name)
                if caller is None:
                    continue
                caller_body, caller_offset = caller
                for invocation in _code_matches(
                    caller_body, re.compile(r"\bfinishGoodNoteHit\s*\("),
                ):
                    post_native_refs.append(_ref(
                        engine_root, play_path,
                        _line_at(play_code, caller_offset + invocation.start()),
                    ))
            if post_native_refs:
                post_choices = choices
                post_branch_ref = _ref(
                    engine_root, play_path,
                    _line_at(play_code, post_offset + branch.start()),
                )

    dispatch_pattern = re.compile(r"\bPsychRuntimeBindings\s*\.\s*dispatch\s*\(")
    for match in _code_matches(play_code, dispatch_pattern):
        opening = play_code.find("(", match.start())
        arguments, end = _extract_call_arguments(play_code, opening)
        if len(arguments) < 3 or arguments[0].strip() != "this":
            continue
        callback_expression = arguments[1].strip()
        literal = re.fullmatch(r"(['\"])([A-Za-z_$][\w$]*)\1", callback_expression)
        call_ref = _ref(engine_root, play_path, _line_at(play_code, match.start()))
        if literal is not None:
            routes[literal.group(2)].append(call_ref)
            continue

        in_pre_helper = pre_region is not None and (
            pre_region[1] <= match.start() < pre_region[1] + len(pre_region[0])
        )
        in_post_helper = post_region is not None and (
            post_region[1] <= match.start() < post_region[1] + len(post_region[0])
        )
        choices = (
            pre_choices if in_pre_helper and callback_expression == "callback"
            else post_choices if in_post_helper and callback_expression == "name"
            else []
        )
        branch_ref = pre_branch_ref if in_pre_helper else post_branch_ref if in_post_helper else None
        native_refs = pre_native_refs if in_pre_helper else post_native_refs if in_post_helper else []
        dynamic_sites.append({
            "dialect": "Psych chart hooks",
            "receiver": "PsychRuntimeBindings.dispatch",
            "callback_expression": callback_expression,
            "literal_callback_choices": choices,
            "name_resolution": "dynamic-with-literal-alternatives" if choices else "dynamic-unresolved",
            "arguments": arguments[2:],
            "source": asdict(call_ref),
            "return_use": _call_result_use(play_code, match.start(), end),
        })
        if choices and branch_ref is not None:
            for name in choices:
                routes[name].extend([call_ref, branch_ref, *native_refs])
    return routes, dynamic_sites


def _dispatch_contracts(root: Path, code: str, path: Path, dialect: str) -> list[dict[str, object]]:
    patterns = [SCRIPT_CALL] if dialect == "Nightmare Vision HScript" else [PSYCH_DISPATCH_CALL]
    dispatches: list[dict[str, object]] = []
    for regex in patterns:
        for match in _code_matches(code, regex):
            if _is_function_declaration(code, match.start()):
                continue
            opening = code.find("(", match.start())
            arguments, end = _extract_call_arguments(code, opening)
            if not arguments:
                continue
            callback_expression = arguments[0]
            literal = re.fullmatch(r"""(['"])(.*?)\1""", callback_expression.strip())
            callback = literal.group(2) if literal else None
            choices = _literal_callback_choices(callback_expression)
            payload = arguments[1] if len(arguments) > 1 else None
            payload_expressions = []
            if payload and payload.startswith("[") and payload.endswith("]"):
                payload_expressions = [part for part, _ in _split_top_level(payload[1:-1])]
            dispatches.append({
                "callback": callback,
                "callback_literal_choices": choices,
                "callback_expression": callback_expression,
                "name_resolution": "literal" if callback is not None else "dynamic-with-literal-alternatives" if choices else "dynamic-expression",
                "receiver": match.group(1) if dialect == "Nightmare Vision HScript" else match.group(0).split("(")[0],
                "arguments": arguments[1:],
                "callback_payload_expression": payload,
                "callback_payload_items": payload_expressions,
                "source": asdict(_ref(root, path, _line_at(code, match.start()))),
                "sequence_index": len(dispatches),
                "return_use": _call_result_use(code, match.start(), end),
            })
    dispatches.sort(key=lambda item: (item["source"]["line"], item["sequence_index"]))
    for order, dispatch in enumerate(dispatches, 1):
        dispatch["sequence_index"] = order
    return dispatches


def _callback_alias_inventory(engine_root: Path) -> list[dict[str, object]]:
    path = engine_root / "source" / "EngineCompat.hx"
    if not path.is_file():
        return []
    code = _read_code(path)
    function = _named_function_region(code, "callbackNames")
    result: list[dict[str, object]] = []
    if function is not None:
        body, body_offset = function
        cases = list(re.finditer(r"\bcase\s+([^:\n]+):", body))
        for index, case in enumerate(cases):
            end = cases[index + 1].start() if index + 1 < len(cases) else len(body)
            branch = body[case.end():end]
            inputs = [value for _, value in re.findall(r"""(['"])([^'"]+)\1""", case.group(1))]
            outputs = [match.group(2) for match in _code_matches(branch, APPEND_HOOK)]
            if not inputs or not outputs:
                continue
            append_refs = [
                asdict(_ref(engine_root, path, _line_at(code, body_offset + case.end() + match.start())))
                for match in _code_matches(branch, APPEND_HOOK)
            ]
            result.append({
                "host_callback_spellings": inputs,
                "script_callback_spellings": list(dict.fromkeys(outputs)),
                "source": asdict(_ref(engine_root, path, _line_at(code, body_offset + case.start()))),
                "append_sites": append_refs,
                "evidence_kind": "literal-callbackNames-branch",
                "behavioral_verification": "unverified",
            })
    # This callback name is produced by a conditional ABI adapter rather than
    # callbackNames(): the ordinary noteMiss route becomes noteMissPress for a
    # Psych ghost miss (null note, player flag, numeric direction).
    play_path = engine_root / "source" / "PlayState.hx"
    play_code = _read_code(play_path) if play_path.is_file() else ""
    caller = _named_function_region(play_code, "callHscript")
    miss_press = _named_function_region(code, "psychMissPressArguments")
    if caller and miss_press:
        caller_body, caller_offset = caller
        miss_body, miss_offset = miss_press
        helper_call = re.search(r"EngineCompat\.psychMissPressArguments\s*\(\s*func_name\s*,\s*args\s*\)", caller_body)
        rename = re.search(r"func_name\s*=\s*(['\"])noteMissPress\1", caller_body)
        condition = re.search(r"canonicalCallback\(name\)\s*!=\s*(['\"])noteMiss\1", miss_body)
        returned_direction = re.search(r"return\s*\[\s*args\[2\]\s*\]", miss_body)
        if helper_call and rename and condition and returned_direction:
            call_ref = asdict(_ref(engine_root, play_path, _line_at(play_code, caller_offset + helper_call.start())))
            rename_ref = asdict(_ref(engine_root, play_path, _line_at(play_code, caller_offset + rename.start())))
            result.append({
                "host_callback_spellings": ["noteMiss"],
                "script_callback_spellings": ["noteMissPress"],
                "source": call_ref,
                "append_sites": [rename_ref],
                "evidence_kind": "conditional-argument-adapter",
                "conditions": "Psych noteMiss call with null note, player flag, and numeric direction",
                "argument_mapping": "direction from args[2] becomes the sole noteMissPress argument",
                "adapter_evidence": [
                    asdict(_ref(engine_root, path, _line_at(code, miss_offset + condition.start()))),
                    asdict(_ref(engine_root, path, _line_at(code, miss_offset + returned_direction.start()))),
                ],
                "behavioral_verification": "unverified",
            })
    return result


def _dynamic_dispatch_sites(engine_root: Path) -> list[dict[str, object]]:
    sites: list[dict[str, object]] = []
    _psych_runtime_routes, psych_runtime_dynamic = _psych_runtime_dispatch_inventory(engine_root)
    _source_gameover_routes, source_gameover_dynamic = _source_gameover_callback_routes(engine_root)
    sites.extend(source_gameover_dynamic)
    for path in iter_haxe_files(engine_root):
        code = _read_code(path)
        psych_dispatch = re.compile(
            r"\b(?:callOnScripts|callOnLuas|callOnHScript|callOnHaxe|callOnLua|callAllHScript|callHscript)\s*\("
        )
        for match in _code_matches(code, psych_dispatch):
            if _is_function_declaration(code, match.start()):
                continue
            opening = code.find("(", match.start())
            arguments, end = _extract_call_arguments(code, opening)
            if not arguments:
                continue
            callback_expression = arguments[0]
            if re.fullmatch(r"(['\"])[A-Za-z_$][\w$]*\1", callback_expression.strip()):
                continue
            choices = _literal_callback_choices(callback_expression)
            sites.append({
                "dialect": "Psych chart hooks",
                "receiver": match.group(0).split("(")[0],
                "callback_expression": callback_expression,
                "literal_callback_choices": choices,
                "name_resolution": "dynamic-with-literal-alternatives" if choices else "dynamic-unresolved",
                "arguments": arguments[1:],
                "source": asdict(_ref(engine_root, path, _line_at(code, match.start()))),
                "return_use": _call_result_use(code, match.start(), end),
            })
        for match in _code_matches(code, SCRIPT_CALL):
            if _is_function_declaration(code, match.start()):
                continue
            receiver = match.group(1)
            if receiver not in {"nightmareVisionScripts", "scripts", "scriptGroup", "script", "newScript"}:
                continue
            opening = code.find("(", match.start())
            arguments, end = _extract_call_arguments(code, opening)
            if not arguments:
                continue
            callback_expression = arguments[0]
            if re.fullmatch(r"""(['"])[A-Za-z_$][\w$]*\1""", callback_expression.strip()):
                continue
            choices = _literal_callback_choices(callback_expression)
            sites.append({
                "dialect": "Nightmare Vision HScript",
                "receiver": receiver,
                "callback_expression": callback_expression,
                "literal_callback_choices": choices,
                "name_resolution": "dynamic-with-literal-alternatives" if choices else "dynamic-unresolved",
                "arguments": arguments[1:],
                "source": asdict(_ref(engine_root, path, _line_at(code, match.start()))),
                "return_use": _call_result_use(code, match.start(), end),
            })
        if path.name == "PlayState.hx":
            sites.extend(psych_runtime_dynamic)
        if path.name == "PlayState.hx":
            for match in _code_matches(code, re.compile(r"\bcallNightmareVision\s*\(")):
                if _is_function_declaration(code, match.start()):
                    continue
                opening = code.find("(", match.start())
                arguments, end = _extract_call_arguments(code, opening)
                if not arguments or re.fullmatch(r"""(['"])[A-Za-z_$][\w$]*\1""", arguments[0].strip()):
                    continue
                choices = _literal_callback_choices(arguments[0])
                sites.append({
                    "dialect": "Nightmare Vision HScript",
                    "receiver": "callNightmareVision",
                    "callback_expression": arguments[0],
                    "literal_callback_choices": choices,
                    "name_resolution": "dynamic-with-literal-alternatives" if choices else "dynamic-unresolved",
                    "arguments": arguments[1:],
                    "source": asdict(_ref(engine_root, path, _line_at(code, match.start()))),
                    "return_use": _call_result_use(code, match.start(), end),
                })
    return sites


def _nightmare_vision_reflection_evidence(engine_root: Path) -> dict[str, object]:
    play_path = engine_root / "source" / "PlayState.hx"
    interp_path = engine_root / "source" / "NightmareVisionScriptInterp.hx"
    result: dict[str, object] = {"status": "unverified", "seed_aliases": [], "class_parent": None, "resolver": []}
    if play_path.is_file():
        code = _read_code(play_path)
        aliases = []
        common = _named_function_region(code, "seedNightmareVisionCommon")
        if common:
            body, body_offset = common
            preset = re.search(r"\bvar\s+preset\s*:\s*Map\s*<[^;=]+>\s*=\s*\[", body)
            if preset:
                opening = body.find("[", preset.start())
                region = _balanced_region(body, opening, "[", "]")
                for alias in re.finditer(r"""(['"])(PlayState|game)\1\s*=>\s*([^,\n}]+)""", region):
                    aliases.append({
                        "name": alias.group(2),
                        "expression": alias.group(3).strip(),
                        "source": asdict(_ref(engine_root, play_path, _line_at(code, body_offset + opening + alias.start()))),
                    })
        seed = _named_function_region(code, "seedNightmareVision")
        if seed:
            body, body_offset = seed
            for match in re.finditer(r"""\bvariables\s*\.\s*set\s*\(\s*(['"])(PlayState|game)\1\s*,\s*([^,)]+)""", body):
                aliases.append({
                    "name": match.group(2),
                    "expression": match.group(3).strip(),
                    "source": asdict(_ref(engine_root, play_path, _line_at(code, body_offset + match.start()))),
                })
            parent = re.search(r"\bbindClassParent\s*\(\s*PlayState\s*\)", body)
            if parent:
                result["class_parent"] = asdict(_ref(engine_root, play_path, _line_at(code, body_offset + parent.start())))
        result["seed_aliases"] = aliases
    if interp_path.is_file():
        code = _read_code(interp_path)
        patterns = [
            r"\bclassParents\s*:", r"\bfunction\s+bindClassParent\s*\(",
            r"\bfunction\s+usesClassParent\s*\(", r"\bfunction\s+resolve\s*\(",
            r"\boverride\s+function\s+(?:get|set)\s*\(", r"\bparentFields\s*:",
            r"\bfunction\s+set_parent\s*\(", r"\bType\.getInstanceFields\s*\(",
            r"\bReflect\.(?:getProperty|setProperty)\s*\(\s*parent\s*,",
        ]
        for pattern in patterns:
            match = re.search(pattern, code)
            if match:
                result["resolver"].append(asdict(_ref(engine_root, interp_path, _line_at(code, match.start()))))
    alias_names = {item["name"] for item in result["seed_aliases"]}
    result["seed_alias_status"] = {
        "PlayState_class": "present" if "PlayState" in alias_names else "not-found",
        "game_instance": "present" if "game" in alias_names else "not-found",
    }
    result["status"] = (
        "dynamic-path-present-unverified"
        if result["class_parent"] and result["resolver"] and {"PlayState", "game"}.issubset(alias_names)
        else "not-established"
    )
    return result


def _build_contract_inventory(entries: list[ApiEntry], roots: dict[str, Path], engine_root: Path) -> list[dict[str, object]]:
    test_root = engine_root / "tools" / "tests"
    test_refs: dict[str, list[dict[str, object]]] = defaultdict(list)
    entries_by_name: dict[str, list[ApiEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_name[entry.name].append(entry)
    test_name_pattern = (
        re.compile(r"\b(?:" + "|".join(re.escape(name) for name in sorted(entries_by_name, key=len, reverse=True)) + r")\b")
        if entries_by_name else None
    )
    for test_path in sorted(test_root.glob("test_*.py")) if test_root.is_dir() and test_name_pattern is not None else []:
        try:
            test_text = test_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        has_runner = any(token in test_text for token in ("--interp", "--run", "subprocess.run(", "HAXE_COMMAND"))
        has_assertions = any(token in test_text for token in ("assertEqual", "assertIn", "assertTrue", "assertRaises"))
        evidence_kind = "test-file-semantic-candidate" if has_runner and has_assertions else "name-reference-only"
        path_label = test_path.relative_to(engine_root).as_posix()
        seen_names: set[str] = set()
        assert test_name_pattern is not None
        for found in test_name_pattern.finditer(test_text):
            name = found.group(0)
            if name in seen_names:
                continue
            seen_names.add(name)
            line = _line_at(test_text, found.start())
            test_refs[name].append({
                "path": path_label,
                "line": line,
                "evidence_kind": evidence_kind,
                "behavior_proof": False,
            })

    dispatch_by_dialect: dict[str, list[dict[str, object]]] = {}
    dynamic_donor_sites: list[dict[str, object]] = []
    dispatch_dialects = {"Psych chart hooks", "Nightmare Vision HScript"}
    for dialect, donor_root in roots.items():
        if dialect not in dispatch_dialects:
            continue
        candidate_paths = [Path(ref.path) for entry in entries if entry.dialect == dialect for ref in entry.source]
        unique_paths = sorted({(donor_root / path).resolve() for path in candidate_paths}, key=str)
        sites: list[dict[str, object]] = []
        for path in unique_paths:
            if not path.is_file():
                continue
            code = _read_code(path)
            sites.extend(_dispatch_contracts(donor_root, code, path, dialect))
        dynamic_donor_sites.extend(site for site in sites if site["callback"] is None)
        dispatch_by_dialect[dialect] = sites

    for entry in entries:
        all_test_evidence = test_refs.get(entry.name, [])
        test_summary = {
            "name_reference_count": sum(item["evidence_kind"] == "name-reference-only" for item in all_test_evidence),
            "semantic_test_candidates": sum(item["evidence_kind"] == "test-file-semantic-candidate" for item in all_test_evidence),
            "behavior_proof_count": 0,
        }
        test_evidence_sample = [
            item for evidence_kind in ("test-file-semantic-candidate", "name-reference-only")
            for item in [ref for ref in all_test_evidence if ref["evidence_kind"] == evidence_kind][:2]
        ]
        contract: dict[str, object] = {
            "signature_status": "not-applicable",
            "signature": None,
            "parameters": [],
            "declared_return_type": None,
            "return_evidence": [],
            "units": [],
            "units_status": "not-stated",
            "side_effect_evidence": {"calls": [], "writes": []},
            "test_evidence": test_evidence_sample,
            "test_evidence_total_count": len(all_test_evidence),
            "test_evidence_sample_is_complete": len(test_evidence_sample) == len(all_test_evidence),
            "test_evidence_sample_limit_per_kind": 2,
            "behavioral_verification": "unverified",
        }
        donor_root = roots.get(entry.dialect)
        if donor_root and entry.source:
            source_path = donor_root / entry.source[0].path
            code, raw = _read_code(source_path), source_path.read_text(encoding="utf-8", errors="replace") if source_path.is_file() else ""
            if entry.group == "registered functions":
                contract.update(_registration_contract(donor_root, source_path, code, raw, LUA_CALLBACK, entry.name))
            elif entry.group == "seeded globals":
                expression = PSYCH_SET if entry.dialect == "Psych HScript" else NV_SET
                contract.update(_seed_contract(donor_root, source_path, code, raw, expression, entry.name))
                if not contract.get("signature"):
                    contract["signature_status"] = "seeded-value"
                    contract.setdefault("binding_expression", None)
            elif entry.group == "dispatched callbacks":
                calls = [site for site in dispatch_by_dialect.get(entry.dialect, []) if site["callback"] == entry.name]
                contract.update({
                    "signature_status": "call-sites-only",
                    "dispatch_sites": calls,
                    "signature": None,
                    "parameters": [],
                    "return_contract": "see donor call-site return_use; callback ABI is not declared by the dispatch call",
                })
            elif entry.group == "PlayState member surface":
                parsed = _method_contract(code, entry.name, entry.source[0].line) if entry.kind.endswith("method") else _field_contract(code, entry.name, entry.source[0].line)
                contract.update(parsed)
                contract["units_status"] = "not-stated-in-source-declaration"
        contract["test_evidence"] = test_evidence_sample
        contract["behavioral_verification"] = "unverified"
        contract["test_evidence_summary"] = test_summary
        contract["coverage_status"] = entry.status
        contract["coverage_evidence_labels"] = [
            evidence for evidence in entry.engine_evidence
            if not re.match(r"^(.*):(\d+)$", evidence)
        ]
        contract["coverage_evidence_refs"] = [
            {"path": match.group(1), "line": int(match.group(2))}
            for evidence in entry.engine_evidence
            if (match := re.match(r"^(.*):(\d+)$", evidence))
        ]
        evidence_kind = "none"
        if entry.status == "implemented":
            if entry.group == "dispatched callbacks":
                evidence_kind = "callback-name-alias" if any("EngineCompat.hx" in ref for ref in entry.engine_evidence) else "literal-dispatch"
            elif entry.group == "seeded globals":
                evidence_kind = (
                    "explicit-installed-source-binder"
                    if "wired source binder call-chain" in entry.engine_evidence
                    else "literal-seed-or-map-binding"
                )
            elif entry.group == "registered functions":
                evidence_kind = "static-engine-binding"
        elif entry.group == "PlayState member surface" and entry.status == "unverified":
            evidence_kind = "dynamic-class-parent-reflection"
        elif entry.status == "names-only":
            evidence_kind = "text-mention-only"
        contract["coverage_evidence_kind"] = evidence_kind
        contract["failure_behavior"] = contract.get("failure_behavior", "not-stated-in-nearby-source")
        side_effects = contract.get("side_effect_evidence")
        if not isinstance(side_effects, dict):
            side_effects = {}
        side_effects.setdefault("calls", contract.get("body_calls", []))
        side_effects.setdefault("writes", contract.get("body_writes", []))
        side_effects.setdefault("classification", "syntactic source observations, not a complete semantic effect analysis")
        contract["side_effect_evidence"] = side_effects
        contract.pop("body_calls", None)
        contract.pop("body_writes", None)
        # Reachable helper registrations carry preprocessor and call-chain
        # provenance that the ordinary inline callback parser cannot infer.
        for key in ("registration_conditions", "registration_chain"):
            if key in entry.contract:
                contract[key] = entry.contract[key]
        entry.contract = contract
    return dynamic_donor_sites


def _balanced_region(text: str, opening: int, left: str, right: str) -> str:
    """Return a bracketed region, ignoring bracket characters inside strings."""
    depth = 0
    quote = ""
    i = opening
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 1
            elif char == quote:
                quote = ""
        elif char in ("'", '\"'):
            quote = char
        elif char == left:
            depth += 1
        elif char == right:
            depth -= 1
            if depth == 0:
                return text[opening : i + 1]
        i += 1
    return text[opening:]


def _inside_string_mask(text: str) -> bytearray:
    """Mark string contents so source-like text inside literals is ignored."""
    mask = bytearray(len(text))
    quote = ""
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                mask[i] = 1
                if i + 1 < len(text):
                    mask[i + 1] = 1
                    i += 1
            elif char == quote:
                quote = ""
            else:
                mask[i] = 1
        elif char in ("'", '\"'):
            quote = char
        i += 1
    return mask


def _code_matches(text: str, regex: re.Pattern[str]) -> Iterable[re.Match[str]]:
    mask = _inside_string_mask(text)
    for match in regex.finditer(text):
        if not mask[match.start()]:
            yield match


def _code_identifiers(text: str, candidates: set[str]) -> set[str]:
    mask = _inside_string_mask(text)
    return {
        match.group(0)
        for match in re.finditer(r"\b[A-Za-z_$][\w$]*\b", text)
        if match.group(0) in candidates and not mask[match.start()]
    }


def _add_entry(entries: dict[tuple[str, str, str], ApiEntry], entry: ApiEntry) -> None:
    key = (entry.dialect, entry.group, entry.name)
    found = entries.get(key)
    if found is None:
        entries[key] = entry
        return
    found.source.extend(ref for ref in entry.source if ref not in found.source)


LUA_CALLBACK = re.compile(
    r"\b(?:Lua_helper\s*\.\s*add_callback\s*\(\s*[^,\n]+,\s*|"
    r"(?:[A-Za-z_$][\w$]*\s*\.\s*)?addLocalCallback\s*\(\s*)"
    r"(['\"])([A-Za-z_$][\w$]*)\1",
    re.IGNORECASE,
)
PSYCH_SET = re.compile(r"\bset\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1\s*,")
NV_SET = re.compile(r"\bset\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1\s*,")
PSYCH_HOOK_CALL = re.compile(
    r"\b(?:callOn(?:Scripts|Luas|HScript|Haxe|Lua)|[A-Za-z_$][\w$]*(?:Script|Lua)\.call|"
    r"(?:script|newScript)\.call)"
    r"\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1"
)
NV_HOOK_CALL = re.compile(
    r"\b(?:scripts|scriptGroup|script)\s*\.\s*call\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1"
)
DIRECT_BIND = re.compile(
    r"(?:\b(?:interp\s*\.\s*)?variables\s*\.\s*set|\bvariables\s*\.\s*set)"
    r"\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1"
)
BINDER_SET = re.compile(
    r"\bset\s*\(\s*(?:vars|variables)\s*,\s*(['\"])([A-Za-z_$][\w$]*)\1\s*,"
)
MAP_BIND = re.compile(r"(['\"])([A-Za-z_$][\w$]*)\1\s*=>")
APPEND_HOOK = re.compile(r"\bappendName\s*\(\s*result\s*,\s*(['\"])([A-Za-z_$][\w$]*)\1")
DYNAMIC_BIND_PREFIX = re.compile(
    r"\b(?:[A-Za-z_$][\w$]*\s*\.\s*)?variables\s*\.\s*set\s*\(\s*(['\"])([^'\"]*)\1\s*\+\s*([A-Za-z_$][\w$]*)"
)
METHOD_DECL = re.compile(
    r"(?m)^\s*((?:(?:public|private|static|override|dynamic|inline|@:keep)\s+)*)"
    r"function\s+([A-Za-z_$][\w$]*)\s*\("
)
FIELD_DECL = re.compile(
    r"^\s*((?:(?:public|private|static|inline|@:keep|final)\s+)*)"
    r"(?:var|final)\s+([A-Za-z_$][\w$]*)\b"
)


def _class_member_names(code: str, class_name: str) -> dict[str, tuple[str, int]]:
    """Collect top-level public/default-public methods and fields from one class."""
    declaration = re.search(rf"\bclass\s+{re.escape(class_name)}\b", code)
    if declaration is None:
        return {}
    opening = code.find("{", declaration.end())
    if opening < 0:
        return {}
    region = _balanced_region(code, opening, "{", "}")
    members: dict[str, tuple[str, int]] = {}
    depth = 0
    quote = ""
    line_offset = 0
    for line in region.splitlines(keepends=True):
        if depth == 1:
            method = METHOD_DECL.match(line)
            if method and "private" not in method.group(1).split():
                members[method.group(2)] = ("method", _line_at(code, opening + line_offset + method.start()))
            field = FIELD_DECL.match(line)
            if field and "private" not in field.group(1).split():
                members.setdefault(
                    field.group(2),
                    ("field", _line_at(code, opening + line_offset + field.start())),
                )
        i = 0
        while i < len(line):
            char = line[i]
            if quote:
                if char == "\\":
                    i += 1
                elif char == quote:
                    quote = ""
            elif char in ("'", '\"'):
                quote = char
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            i += 1
        line_offset += len(line)
    return members


def _binding_kind(code: str, match_end: int) -> str:
    tail = code[match_end : match_end + 180].lstrip()
    if tail.startswith("function") or re.match(r"\([^\n]*\)\s*->", tail):
        return "function"
    if re.match(r"(?:[A-Za-z_$][\w$]*\.)*[A-Z][A-Za-z0-9_.]*\s*[,)]", tail):
        return "class/value"
    return "value"


def _named_function_region(code: str, name: str) -> tuple[str, int] | None:
    """Return one named Haxe method body and its source offset."""
    match = re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", code)
    if match is None:
        return None
    opening = code.find("{", match.end())
    if opening < 0:
        return None
    return _balanced_region(code, opening, "{", "}"), opening


def _source_gameover_callback_routes(
    engine_root: Path,
) -> tuple[dict[str, dict[str, list[SourceRef]]], list[dict[str, object]]]:
    """Trace literal GameOverSubstate hook calls through the owner dispatcher.

    The source owner routes the same substate callback name to either Psych's
    callback broadcaster or Nightmare Vision's script group. Count only names
    passed literally by the actual substate into a matching installed route.
    """
    routes: dict[str, dict[str, list[SourceRef]]] = {
        "Psych chart hooks": defaultdict(list),
        "Nightmare Vision HScript": defaultdict(list),
    }
    dynamic_sites: list[dict[str, object]] = []
    play_path = engine_root / "source" / "PlayState.hx"
    substate_path = engine_root / "source" / "GameOverSubstate.hx"
    runtime_path = engine_root / "source" / "PsychRuntimeBindings.hx"
    if not play_path.is_file() or not substate_path.is_file():
        return routes, dynamic_sites

    play_code = _read_code(play_path)
    substate_code = _read_code(substate_path)
    source_call = _named_function_region(play_code, "sourceGameOverCall")
    if source_call is None:
        return routes, dynamic_sites
    source_body, source_offset = source_call
    if not re.search(r"\bsourceScoreOwner\b", source_body) or not re.search(r"\bsourceScoreNightmare\b", source_body):
        return routes, dynamic_sites

    if not re.search(
        r"function\s+sourceGameOverMode\s*\(\s*\)\s*:\s*Int\s+return\s+"
        r"!sourceScoreOwner\s*\?\s*0\s*:\s*sourceScoreNightmare\s*\?\s*2\s*:\s*1\s*;",
        play_code,
    ):
        return routes, dynamic_sites

    psych_route = False
    psych_route_ref: SourceRef | None = None
    if runtime_path.is_file():
        runtime_code = _read_code(runtime_path)
        dispatch = _named_function_region(runtime_code, "dispatch")
        if dispatch is not None and re.search(
            r"\bpublic\s+static\s+function\s+dispatch\s*\(\s*host\s*:\s*PlayState\s*,\s*"
            r"name\s*:\s*String\s*,\s*args\s*:\s*Array\s*<\s*Dynamic\s*>",
            runtime_code,
        ) and re.search(r"\breturn\s+dispatchScopes\s*\(\s*host\s*,\s*name\s*,\s*args\s*,\s*family\b", dispatch[0]):
            match = re.search(
                r"PsychRuntimeBindings\s*\.\s*dispatch\s*\(\s*this\s*,\s*callback\s*,\s*args\b",
                source_body,
            )
            if match is not None:
                psych_route = True
                psych_route_ref = _ref(engine_root, play_path,
                                       _line_at(play_code, source_offset + match.start()))

    nv_route = False
    nv_route_ref: SourceRef | None = None
    call_nv = _named_function_region(play_code, "callNightmareVision")
    if call_nv is not None and re.search(
        r"nightmareVisionScripts\s*\.\s*call\s*\(\s*event\s*,\s*args\s*\)", call_nv[0]
    ):
        match = re.search(r"\bcallNightmareVision\s*\(\s*callback\s*,\s*args\s*\)", source_body)
        if match is not None:
            nv_route = True
            nv_route_ref = _ref(engine_root, play_path,
                                _line_at(play_code, source_offset + match.start()))

    call_pattern = re.compile(r"\b[A-Za-z_$][\w$]*\s*\.\s*sourceGameOverCall\s*\(")
    for match in _code_matches(substate_code, call_pattern):
        opening = substate_code.find("(", match.start())
        arguments, end = _extract_call_arguments(substate_code, opening)
        if not arguments:
            continue
        callback = re.fullmatch(r"(['\"])([A-Za-z_$][\w$]*)\1", arguments[0].strip())
        if callback is None:
            continue
        mode_candidates = _source_gameover_modes_at(substate_code, match.start())
        name = callback.group(2)
        caller_ref = _ref(engine_root, substate_path, _line_at(substate_code, match.start()))
        for dialect, route_ref in (
            ("Psych chart hooks", psych_route_ref if psych_route else None),
            ("Nightmare Vision HScript", nv_route_ref if nv_route else None),
        ):
            expected_mode = 1 if dialect == "Psych chart hooks" else 2
            if route_ref is None or expected_mode not in mode_candidates:
                continue
            routes[dialect][name].extend([caller_ref, route_ref])
            dynamic_sites.append({
                "dialect": dialect,
                "receiver": "sourceGameOverCall",
                "callback_expression": "callback",
                "literal_callback_choices": [name],
                "name_resolution": "dynamic-with-literal-alternatives",
                "arguments": arguments[1:],
                "source": asdict(route_ref),
                "caller_source": asdict(caller_ref),
                "return_use": _call_result_use(substate_code, match.start(), end),
                "behavioral_verification": "unverified",
            })
    return routes, dynamic_sites


def _source_gameover_modes_at(code: str, offset: int) -> set[int]:
    """Return source modes proven to reach a GameOverSubstate callsite.

    Only simple ``sourceMode`` equality guards and early returns are evaluated.
    When surrounding flow is ambiguous, an empty set prevents a static false
    positive instead of assuming the shared wrapper serves both dialects.
    """
    function_match = None
    for candidate in re.finditer(r"\bfunction\s+[A-Za-z_$][\w$]*\s*\([^)]*\)", code):
        if candidate.start() > offset:
            break
        opening = code.find("{", candidate.end())
        if opening < 0:
            continue
        body = _balanced_region(code, opening, "{", "}")
        if opening < offset < opening + len(body) - 1:
            function_match = (opening, body)
    if function_match is None:
        return set()

    function_offset, body = function_match
    local_offset = offset - function_offset
    candidates = {1, 2}
    saw_mode_guard = False
    guards = re.compile(
        r"\bif\s*\(\s*sourceMode\s*(==|!=)\s*(0|1|2)"
        r"(?:\s*&&[^)]*)?\s*\)\s*(\{)?"
    )
    for guard in guards.finditer(body):
        if guard.start() > local_offset:
            continue
        operator, raw_mode = guard.group(1), int(guard.group(2))
        condition_modes = ({raw_mode} if operator == "==" else {1, 2} - {raw_mode})
        saw_mode_guard = True
        if guard.group(3):
            opening = function_offset + guard.end() - 1
            guarded = _balanced_region(code, opening, "{", "}")
            guarded_end = guard.end() + len(guarded) - 1
        else:
            statement_end = body.find(";", guard.end())
            if statement_end < 0:
                continue
            guarded = body[guard.end():statement_end + 1]
            guarded_end = statement_end + 1
        if guard.end() <= local_offset < guarded_end:
            candidates.intersection_update(condition_modes)
        elif guarded_end <= local_offset and re.search(r"\breturn\s*;", guarded):
            # Do not infer through an else branch; only the simple early-return
            # shape is used by the source GameOver create path.
            tail = body[guarded_end:]
            if not re.match(r"\s*else\b", tail):
                candidates.difference_update(condition_modes)
    return candidates if saw_mode_guard else set()


def _literal_loop_bindings(code: str) -> list[tuple[str, int]]:
    """Expand literal suffix loops that register `variables.set(prefix + item, ...)`."""
    result: list[tuple[str, int]] = []
    loop = re.compile(r"\bfor\s*\(\s*([A-Za-z_$][\w$]*)\s+in\s*\[")
    for match in loop.finditer(code):
        opening = code.find("[", match.start(), match.end())
        array = _balanced_region(code, opening, "[", "]")
        if not array.endswith("]"):
            continue
        suffixes = re.findall(r"(['\"])([A-Za-z_$][\w$]*)\1", array)
        if not suffixes:
            continue
        array_end = opening + len(array)
        body_open = code.find("{", array_end)
        if body_open < 0:
            continue
        body = _balanced_region(code, body_open, "{", "}")
        if not body.endswith("}"):
            continue
        item_names = {match.group(1)}
        item_names.update(
            alias.group(1)
            for alias in re.finditer(
                rf"\bvar\s+([A-Za-z_$][\w$]*)\s*=\s*{re.escape(match.group(1))}\b", body
            )
        )
        for binding in _code_matches(body, DYNAMIC_BIND_PREFIX):
            if binding.group(3) not in item_names:
                continue
            for _, suffix in suffixes:
                result.append((binding.group(2) + suffix, body_open + binding.start()))
    return result


def _source_binding_audit(
    engine_root: Path,
) -> tuple[dict[str, dict[str, list[SourceRef]]], list[dict[str, object]]]:
    """Collect only source presets reached through statically wired host paths.

    Names in a helper or preset table are candidates, not evidence. A route is
    eligible only when its host construction, callback/installer handoff, and
    literal bind site are all found in the current source tree.
    """
    bindings: dict[str, dict[str, list[SourceRef]]] = defaultdict(lambda: defaultdict(list))
    routes: list[dict[str, object]] = []
    play_path = engine_root / "source" / "PlayState.hx"
    play_code = _read_code(play_path)

    def method(path: Path, code: str, name: str) -> tuple[str, int] | None:
        return _named_function_region(code, name)

    def first_ref(
        root: Path, path: Path, code: str, region: tuple[str, int] | None,
        pattern: re.Pattern[str],
    ) -> tuple[re.Match[str] | None, SourceRef | None]:
        if region is None:
            return None, None
        body, offset = region
        match = next(iter(_code_matches(body, pattern)), None)
        if match is None:
            return None, None
        return match, _ref(root, path, _line_at(code, offset + match.start()))

    def method_refs(
        root: Path, path: Path, code: str, name: str, pattern: re.Pattern[str],
    ) -> list[tuple[re.Match[str], SourceRef]]:
        region = method(path, code, name)
        if region is None:
            return []
        body, offset = region
        return [
            (match, _ref(root, path, _line_at(code, offset + match.start())))
            for match in _code_matches(body, pattern)
        ]

    def direct_bindings(
        root: Path, path: Path, code: str, method_name: str, pattern: re.Pattern[str],
    ) -> list[tuple[str, SourceRef]]:
        result: list[tuple[str, SourceRef]] = []
        region = method(path, code, method_name)
        if region is None:
            return result
        body, offset = region
        for match in _code_matches(body, pattern):
            result.append((match.group(2), _ref(root, path, _line_at(code, offset + match.start()))))
        return result

    def append_route(
        route_name: str,
        dialect: str,
        steps: list[tuple[str, SourceRef | None]],
        candidate_bindings: list[tuple[str, SourceRef, str | None]],
    ) -> None:
        wired = bool(steps) and all(ref is not None for _, ref in steps)
        step_records = [
            {"step": label, "status": "found" if ref is not None else "not-found",
             "source": asdict(ref) if ref is not None else None}
            for label, ref in steps
        ]
        route_refs = [ref for _, ref in steps if ref is not None]
        proven = candidate_bindings if wired else []
        for name, bind_ref, _condition in proven:
            destination = bindings[dialect].setdefault(name, [])
            for ref in [bind_ref, *route_refs]:
                if ref not in destination:
                    destination.append(ref)
        routes.append({
            "name": route_name,
            "dialect": dialect,
            "status": "wired" if wired else "not-wired",
            "evidence_kind": "explicit-static-call-chain",
            "chain": step_records,
            "candidate_binding_names": sorted({name for name, _, _ in candidate_bindings}),
            "binding_names": sorted({name for name, _, _ in proven}),
            "binding_sources": [
                {"name": name, "source": asdict(ref), "condition": condition}
                for name, ref, condition in proven
            ],
            "behavioral_verification": "unverified",
        })

    # Psych plain .hx owner setup: PlayState installs PsychRuntimeBindings,
    # whose SourceIrisBridge branch installs the source preset.
    runtime_path = engine_root / "source" / "PsychRuntimeBindings.hx"
    runtime_code = _read_code(runtime_path)
    psych_binder_path = engine_root / "source" / "PsychHscriptSourceBindings.hx"
    psych_binder_code = _read_code(psych_binder_path)
    psych_callback_path = engine_root / "source" / "PsychSourceCallbackRegistry.hx"
    psych_callback_code = _read_code(psych_callback_path)
    make_region = method(play_path, play_code, "makeHaxeState")
    make_body = make_region[0] if make_region else ""
    make_offset = make_region[1] if make_region else 0
    plain_bridge_match = next(iter(_code_matches(
        make_body, re.compile(r"plainPsych\s*\?\s*PluginManager\.addVarsToInterp\s*\(\s*new\s+SourceIrisBridge\s*\(")
    )), None)
    lua_bridge_match = next(iter(_code_matches(
        make_body, re.compile(
            r"translatedLua\s*\?\s*PluginManager\.addVarsToInterp\s*\(\s*"
            r"new\s+LuaCompatInterp\s*\(\s*\)\s*\)"
        )
    )), None)
    seed_compat_match = next(iter(_code_matches(
        make_body, re.compile(r"\bseedEngineCompat\s*\(\s*interp\s*,")
    )), None)
    plain_bridge_ref = (
        _ref(engine_root, play_path, _line_at(play_code, make_offset + plain_bridge_match.start()))
        if plain_bridge_match else None
    )
    lua_bridge_ref = (
        _ref(engine_root, play_path, _line_at(play_code, make_offset + lua_bridge_match.start()))
        if lua_bridge_match else None
    )
    seed_compat_ref = (
        _ref(engine_root, play_path, _line_at(play_code, make_offset + seed_compat_match.start()))
        if seed_compat_match else None
    )
    seed_compat_region = method(play_path, play_code, "seedEngineCompat")
    seed_compat_body = seed_compat_region[0] if seed_compat_region else ""
    seed_compat_offset = seed_compat_region[1] if seed_compat_region else 0
    construct = re.search(
        r"\bvar\s+([A-Za-z_$][\w$]*)\s*(?::\s*[^=]+)?=\s*new\s+PsychRuntimeBindings\s*\(",
        seed_compat_body,
    )
    construct_ref = (
        _ref(engine_root, play_path, _line_at(play_code, seed_compat_offset + construct.start()))
        if construct is not None else None
    )
    runtime_install_ref = None
    if construct is not None:
        install_match = re.search(
            rf"\b{re.escape(construct.group(1))}\s*\.\s*install\s*\(",
            seed_compat_body[construct.end():],
        )
        if install_match is not None:
            runtime_install_ref = _ref(
                engine_root, play_path,
                _line_at(play_code, seed_compat_offset + construct.end() + install_match.start()),
            )

    runtime_install_region = method(runtime_path, runtime_code, "install")
    _, owner_install_ref = first_ref(
        engine_root, runtime_path, runtime_code, runtime_install_region,
        re.compile(
            r"\bif\s*\(\s*Std\.isOfType\s*\(\s*owner\s*,\s*SourceIrisBridge\s*\)\s*\)\s*"
            r"installHscriptPreset\s*\(\s*owner\s*,\s*null\s*\)"
        ),
    )
    hscript_preset_call = re.compile(
        r"new\s+PsychHscriptSourceBindings\s*\([^;]+?\)\s*\.\s*install\s*\(", re.S
    )
    _, psych_binder_install_ref = first_ref(
        engine_root, runtime_path, runtime_code,
        method(runtime_path, runtime_code, "installHscriptPreset"), hscript_preset_call,
    )
    callback_scope_ref = first_ref(
        engine_root, runtime_path, runtime_code,
        method(runtime_path, runtime_code, "installHscriptPreset"),
        re.compile(r"\battachCallbackScope\s*\(\s*scope\s*\)"),
    )[1]
    callback_bridge_ref = first_ref(
        engine_root, runtime_path, runtime_code,
        method(runtime_path, runtime_code, "installHscriptPreset"),
        re.compile(r"host\.psychSourceCallbacks\.bridge\s*\(\s*ownerRoot\s*,\s*scope\s*,\s*origin\s*,\s*parent\s*\)"),
    )[1]
    registry_facade_ref = first_ref(
        engine_root, psych_callback_path, psych_callback_code,
        method(psych_callback_path, psych_callback_code, "bridge"),
        re.compile(r"selfFacade\s*:\s*function\s*\("),
    )[1]
    psych_candidates = direct_bindings(
        engine_root, psych_binder_path, psych_binder_code, "install", DIRECT_BIND,
    )
    psych_binding_conditions = {
        "this": "set only when callbackBridge.selfFacade is callable",
        "ErrorHandledRuntimeShader": "compiled only under !flash && sys",
    }
    psych_candidates_with_conditions = [
        (name, ref, psych_binding_conditions.get(name)) for name, ref in psych_candidates
    ]
    append_route(
        "Psych plain HScript owner preset",
        "Psych HScript",
        [
            ("PlayState.makeHaxeState creates SourceIrisBridge for plain HScript", plain_bridge_ref),
            ("PlayState.makeHaxeState calls seedEngineCompat(interp)", seed_compat_ref),
            ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
            ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
            ("PsychRuntimeBindings.install seeds a SourceIrisBridge owner", owner_install_ref),
            ("installHscriptPreset installs PsychHscriptSourceBindings", psych_binder_install_ref),
            ("installHscriptPreset attaches and supplies callback scope", callback_scope_ref),
            ("PsychSourceCallbackRegistry.bridge provides source facades", callback_bridge_ref if registry_facade_ref else None),
        ],
        psych_candidates_with_conditions,
    )

    module_region = method(runtime_path, runtime_code, "module")
    module_body = module_region[0] if module_region else ""
    module_offset = module_region[1] if module_region else 0
    bridge_match = next(iter(_code_matches(module_body, re.compile(r"embedded\s*=\s*new\s+SourceIrisBridge\s*\("))), None)
    embedded_install_match = next(iter(_code_matches(
        module_body, re.compile(r"installHscriptPreset\s*\(\s*embedded\s*,")
    )), None)
    bridge_ref = (
        _ref(engine_root, runtime_path, _line_at(runtime_code, module_offset + bridge_match.start()))
        if bridge_match else None
    )
    embedded_install_ref = (
        _ref(engine_root, runtime_path, _line_at(runtime_code, module_offset + embedded_install_match.start()))
        if embedded_install_match else None
    )
    _, run_call_ref = first_ref(
        engine_root, runtime_path, runtime_code, runtime_install_region,
        re.compile(r"\bvar\s+run\s*=\s*function\s*\([^)]*\)[\s\S]*?module\s*\(\)")
    )
    append_route(
        "Psych embedded runHaxeCode preset",
        "Psych HScript",
        [
            ("PlayState.makeHaxeState creates SourceIrisBridge for plain HScript", plain_bridge_ref),
            ("PlayState.makeHaxeState calls seedEngineCompat(interp)", seed_compat_ref),
            ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
            ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
            ("PsychRuntimeBindings.install exposes a runHaxeCode closure using module()", run_call_ref),
            ("PsychRuntimeBindings.module creates SourceIrisBridge", bridge_ref),
            ("PsychRuntimeBindings.module installs HScript preset", embedded_install_ref),
            ("installHscriptPreset installs PsychHscriptSourceBindings", psych_binder_install_ref),
            ("installHscriptPreset attaches and supplies callback scope", callback_scope_ref),
            ("PsychSourceCallbackRegistry.bridge provides source facades", callback_bridge_ref if registry_facade_ref else None),
        ],
        psych_candidates_with_conditions,
    )

    # Psych Lua achievement callbacks are registered by the translated Lua
    # runtime, then delegated to the same owner service used by HScript.
    integration_path = engine_root / "source" / "PsychAchievementsIntegration.hx"
    integration_code = _read_code(integration_path)
    lua_bindings_path = engine_root / "source" / "PsychAchievementsLuaBindings.hx"
    lua_bindings_code = _read_code(lua_bindings_path)
    achievements_bindings_path = engine_root / "source" / "PsychAchievementsBindings.hx"
    achievements_bindings_code = _read_code(achievements_bindings_path)
    lua_compat_branch = re.compile(
        r"\belse\s+if\s*\(\s*Std\.isOfType\s*\(\s*owner\s*,\s*LuaCompatInterp\s*\)\s*\)\s*\{"
        r"(?=[^}]*\bPsychAchievementsIntegration\.installLua\s*\(\s*host\s*,\s*owner\s*,\s*origin\s*\))"
        r"(?=[^}]*\bPsychStandardServices\.installLua\s*\(\s*host\s*,\s*owner\s*,\s*origin\s*\))"
        r"[^}]*\}"
    )
    lua_install_ref = first_ref(
        engine_root, runtime_path, runtime_code, runtime_install_region,
        lua_compat_branch,
    )[1]
    lua_integration_region = method(integration_path, integration_code, "installLua")
    lua_runtime_ref = first_ref(
        engine_root, integration_path, integration_code, lua_integration_region,
        re.compile(r"\bruntime\s*=\s*runtimeFor\s*\(\s*host\s*,\s*interp\.variables\.get\s*\(\s*['\"]Paths['\"]\s*\)\s*,\s*origin\s*\)"),
    )[1]
    lua_runtime_guard_ref = first_ref(
        engine_root, integration_path, integration_code, lua_integration_region,
        re.compile(r"\bif\s*\(\s*runtime\s*==\s*null\s*\)\s*return\s*;"),
    )[1]
    lua_binding_handoff_ref = first_ref(
        engine_root, integration_path, integration_code, lua_integration_region,
        re.compile(r"PsychAchievementsLuaBindings\s*\.\s*install\s*\(\s*interp\s*,\s*runtime\.service\s*,\s*report\s*\)"),
    )[1]
    lua_candidates = direct_bindings(
        engine_root, lua_bindings_path, lua_bindings_code, "install", DIRECT_BIND,
    )
    lua_candidate_conditions = {
        "getAchievementScore": "registered on each active LuaCompatInterp",
        "setAchievementScore": "registered on each active LuaCompatInterp",
        "addAchievementScore": "registered on each active LuaCompatInterp",
        "unlockAchievement": "registered on each active LuaCompatInterp",
        "isAchievementUnlocked": "registered on each active LuaCompatInterp",
        "achievementExists": "registered on each active LuaCompatInterp",
    }
    append_route(
        "Psych Lua achievements callbacks",
        "Psych Lua",
        [
            ("PlayState.makeHaxeState creates LuaCompatInterp for translated Lua", lua_bridge_ref),
            ("PlayState.makeHaxeState seeds compatibility bindings", seed_compat_ref),
            ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
            ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
            ("PsychRuntimeBindings.install routes LuaCompatInterp to achievements and standard services", lua_install_ref),
            ("PsychAchievementsIntegration.installLua resolves the owner runtime", lua_runtime_ref),
            ("installLua returns when the owner runtime is unavailable", lua_runtime_guard_ref),
            ("installLua delegates callback registration to the owner binding", lua_binding_handoff_ref),
        ],
        [(name, ref, lua_candidate_conditions.get(name)) for name, ref in lua_candidates],
    )

    # The donor HScript global is likewise exposed only after a SourceIrisBridge
    # reaches the owner integration and its class-token binder.
    hscript_integration_region = method(integration_path, integration_code, "installHscript")
    hscript_preset_integration_ref = first_ref(
        engine_root, psych_binder_path, psych_binder_code, method(psych_binder_path, psych_binder_code, "install"),
        re.compile(r"PsychAchievementsIntegration\s*\.\s*installHscript\s*\(\s*host\s*,\s*interp\s*,\s*origin\s*\)"),
    )[1]
    hscript_bridge_guard_ref = first_ref(
        engine_root, integration_path, integration_code, hscript_integration_region,
        re.compile(r"\bif\s*\(\s*!\s*Std\.isOfType\s*\(\s*interp\s*,\s*SourceIrisBridge\s*\)\s*\)\s*return\s*;"),
    )[1]
    hscript_runtime_ref = first_ref(
        engine_root, integration_path, integration_code, hscript_integration_region,
        re.compile(r"\bruntime\s*=\s*runtimeFor\s*\(\s*host\s*,\s*interp\.variables\.get\s*\(\s*['\"]Paths['\"]\s*\)\s*,\s*origin\s*\)"),
    )[1]
    hscript_binding_handoff_ref = first_ref(
        engine_root, integration_path, integration_code, hscript_integration_region,
        re.compile(
            r"PsychAchievementsBindings\s*\.\s*install\s*\(\s*"
            r"\(\s*cast\s+interp\s*:\s*SourceIrisBridge\s*\)\s*\.evaluator\s*,\s*runtime\.service"
        ),
    )[1]
    hscript_candidates = direct_bindings(
        engine_root, achievements_bindings_path, achievements_bindings_code, "install", DIRECT_BIND,
    )
    append_route(
        "Psych HScript Achievements global",
        "Psych HScript",
        [
            ("PlayState.makeHaxeState creates SourceIrisBridge for plain HScript", plain_bridge_ref),
            ("PlayState.makeHaxeState calls seedEngineCompat(interp)", seed_compat_ref),
            ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
            ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
            ("PsychRuntimeBindings.install seeds a SourceIrisBridge owner", owner_install_ref),
            ("installHscriptPreset installs PsychHscriptSourceBindings", psych_binder_install_ref),
            ("PsychHscriptSourceBindings.install routes to achievement integration", hscript_preset_integration_ref),
            ("PsychAchievementsIntegration.installHscript requires SourceIrisBridge", hscript_bridge_guard_ref),
            ("installHscript resolves the owner runtime", hscript_runtime_ref),
            ("installHscript delegates the class token to owner bindings", hscript_binding_handoff_ref),
        ],
        [(name, ref, "seeded only in SourceIrisBridge owner interpreters")
         for name, ref in hscript_candidates if name == "Achievements"],
    )

    # Language and Discord are owner-scoped services installed by the shared
    # standard-services bridge. Trace the concrete engine entry and the final
    # per-interpreter binding call so detached literal registrations cannot be
    # mistaken for reachable APIs.
    standard_path = engine_root / "source" / "PsychStandardServices.hx"
    standard_code = _read_code(standard_path)
    language_bindings_path = engine_root / "source" / "PsychLanguageBindings.hx"
    language_bindings_code = _read_code(language_bindings_path)
    discord_bindings_path = engine_root / "source" / "PsychDiscordBindings.hx"
    discord_bindings_code = _read_code(discord_bindings_path)

    lua_standard_ref = first_ref(
        engine_root, runtime_path, runtime_code, runtime_install_region,
        lua_compat_branch,
    )[1]
    standard_lua_region = method(standard_path, standard_code, "installLua")
    standard_lua_runtime_ref = first_ref(
        engine_root, standard_path, standard_code, standard_lua_region,
        re.compile(r"\bruntimeFor\s*\(\s*host\s*,\s*interp\.variables\.get\s*\(\s*['\"]Paths['\"]\s*\)\s*,\s*origin\s*\)"),
    )[1]
    standard_lua_guard_ref = first_ref(
        engine_root, standard_path, standard_code, standard_lua_region,
        re.compile(r"\bif\s*\(\s*owner\s*==\s*null\s*\)\s*return\s*;"),
    )[1]

    def psych_lua_service_route(
        route_name: str,
        binding_path: Path,
        binding_code: str,
        helper_name: str,
        expected_names: tuple[str, ...],
        owner_field: str,
    ) -> None:
        service_call_ref = first_ref(
            engine_root, standard_path, standard_code, standard_lua_region,
            re.compile(
                rf"\b{re.escape(helper_name)}\.installLua\s*\(\s*interp\s*,\s*owner\.{re.escape(owner_field)}\s*\)"
            ),
        )[1]
        binding_region = method(binding_path, binding_code, "installLua")
        direct = direct_bindings(engine_root, binding_path, binding_code, "installLua", DIRECT_BIND)
        refs_by_name = {name: ref for name, ref in direct}
        registrations = [
            (name, refs_by_name.get(name)) for name in expected_names
        ]
        append_route(
            route_name,
            "Psych Lua",
            [
                ("PlayState.makeHaxeState creates LuaCompatInterp", lua_bridge_ref),
                ("PlayState.makeHaxeState seeds compatibility bindings", seed_compat_ref),
                ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
                ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
                ("PsychRuntimeBindings.install routes LuaCompatInterp to achievements and standard services", lua_standard_ref),
                ("PsychStandardServices.installLua resolves the owner runtime", standard_lua_runtime_ref),
                ("installLua returns when the owner runtime is unavailable", standard_lua_guard_ref),
                (f"PsychStandardServices.installLua delegates to {helper_name}", service_call_ref),
                *[(f"{helper_name}.installLua registers {name}", ref) for name, ref in registrations],
            ],
            [(name, ref, "registered on each active LuaCompatInterp")
             for name, ref in registrations if ref is not None],
        )

    psych_lua_service_route(
        "Psych Lua Language callbacks",
        language_bindings_path,
        language_bindings_code,
        "PsychLanguageBindings",
        ("getTranslationPhrase", "getFileTranslation"),
        "language",
    )
    psych_lua_service_route(
        "Psych Lua Discord callbacks",
        discord_bindings_path,
        discord_bindings_code,
        "PsychDiscordBindings",
        ("changeDiscordPresence", "changeDiscordClientID"),
        "discord",
    )

    standard_hscript_region = method(standard_path, standard_code, "installHscript")
    standard_hscript_guard_ref = first_ref(
        engine_root, standard_path, standard_code, standard_hscript_region,
        re.compile(r"\bif\s*\(\s*!Std\.isOfType\s*\(\s*interp\s*,\s*SourceIrisBridge\s*\)\s*\)\s*return\s*;"),
    )[1]
    standard_hscript_runtime_ref = first_ref(
        engine_root, standard_path, standard_code, standard_hscript_region,
        re.compile(r"\bruntimeFor\s*\(\s*host\s*,\s*interp\.variables\.get\s*\(\s*['\"]Paths['\"]\s*\)\s*,\s*origin\s*\)"),
    )[1]
    standard_hscript_owner_guard_ref = first_ref(
        engine_root, standard_path, standard_code, standard_hscript_region,
        re.compile(r"\bif\s*\(\s*owner\s*==\s*null\s*\)\s*return\s*;"),
    )[1]
    psych_binder_standard_ref = first_ref(
        engine_root, psych_binder_path, psych_binder_code,
        method(psych_binder_path, psych_binder_code, "install"),
        re.compile(r"PsychStandardServices\.installHscript\s*\(\s*host\s*,\s*interp\s*,\s*origin\s*\)"),
    )[1]

    def psych_hscript_import_route(
        route_name: str,
        language: bool,
    ) -> None:
        binding_path = language_bindings_path if language else discord_bindings_path
        binding_code = language_bindings_code if language else discord_bindings_code
        helper_name = "PsychLanguageBindings" if language else "PsychDiscordBindings"
        owner_field = "language" if language else "discord"
        import_name = "backend.Language" if language else "backend.DiscordClient"
        service_install_ref = first_ref(
            engine_root, standard_path, standard_code, standard_hscript_region,
            re.compile(
                rf"\b{re.escape(helper_name)}\.install\s*\(\s*evaluator\s*,\s*owner\.{owner_field}\s*\)"
            ),
        )[1]
        binding_import_ref = first_ref(
            engine_root, binding_path, binding_code, method(binding_path, binding_code, "install"),
            re.compile(rf"\bbindImport\s*\(\s*['\"]{re.escape(import_name)}['\"]\s*,\s*type\s*\)"),
        )[1]
        candidate = [(import_name, binding_import_ref, "owner class token bound to source import")]
        common_steps = [
            ("PlayState.makeHaxeState creates SourceIrisBridge", plain_bridge_ref),
            ("PlayState.makeHaxeState calls seedEngineCompat(interp)", seed_compat_ref),
            ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
            ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
            ("PsychRuntimeBindings.install seeds a SourceIrisBridge owner", owner_install_ref),
        ]
        install_preset_region = method(runtime_path, runtime_code, "installHscriptPreset")
        preset_binding_ref = first_ref(
            engine_root, runtime_path, runtime_code, install_preset_region, hscript_preset_call,
        )[1]
        hscript_steps = [
            *common_steps,
            ("installHscriptPreset installs PsychHscriptSourceBindings", preset_binding_ref),
            ("PsychHscriptSourceBindings.install routes to standard services", psych_binder_standard_ref),
            ("PsychStandardServices.installHscript requires SourceIrisBridge", standard_hscript_guard_ref),
            ("installHscript resolves the owner runtime", standard_hscript_runtime_ref),
            ("installHscript returns when the owner runtime is unavailable", standard_hscript_owner_guard_ref),
            (f"installHscript delegates to {helper_name}", service_install_ref),
            (f"{helper_name}.install binds {import_name}", binding_import_ref),
        ]
        append_route(route_name, "Psych HScript", hscript_steps, candidate)

        # runHaxeCode creates another SourceIrisBridge through the same preset.
        # Keep its reachability separate from the plain interpreter route.
        embedded_steps = [
            ("PlayState.makeHaxeState creates SourceIrisBridge for plain HScript", plain_bridge_ref),
            ("PlayState.makeHaxeState calls seedEngineCompat(interp)", seed_compat_ref),
            ("PlayState.seedEngineCompat constructs PsychRuntimeBindings", construct_ref),
            ("PlayState.seedEngineCompat calls runtime.install()", runtime_install_ref),
            ("PsychRuntimeBindings.install exposes a runHaxeCode closure using module()", run_call_ref),
            ("PsychRuntimeBindings.module creates SourceIrisBridge", bridge_ref),
            ("PsychRuntimeBindings.module installs HScript preset", embedded_install_ref),
            ("PsychHscriptSourceBindings.install routes to standard services", psych_binder_standard_ref),
            ("PsychStandardServices.installHscript requires SourceIrisBridge", standard_hscript_guard_ref),
            ("installHscript resolves the owner runtime", standard_hscript_runtime_ref),
            ("installHscript returns when the owner runtime is unavailable", standard_hscript_owner_guard_ref),
            (f"installHscript delegates to {helper_name}", service_install_ref),
            (f"{helper_name}.install binds {import_name}", binding_import_ref),
        ]
        append_route(route_name.replace("plain HScript", "embedded runHaxeCode"),
            "Psych HScript", embedded_steps, candidate)

    psych_hscript_import_route("Psych HScript Language import (plain HScript)", True)
    psych_hscript_import_route("Psych HScript DiscordClient import (plain HScript)", False)

    # Nightmare Vision's gameplay loader stores the seeder as `configure`
    # and invokes it while loading the chart scope. This reaches both the
    # shared owner preset and the per-PlayState field snapshot.
    nv_binder_path = engine_root / "source" / "NightmareVisionSourceBindings.hx"
    nv_binder_code = _read_code(nv_binder_path)
    gameplay_path = engine_root / "source" / "NightmareVisionGameplayScripts.hx"
    gameplay_code = _read_code(gameplay_path)
    init_region = method(play_path, play_code, "initializeNightmareVisionScripts")
    init_body = init_region[0] if init_region else ""
    init_offset = init_region[1] if init_region else 0
    constructor_call = next(iter(_code_matches(
        init_body, re.compile(r"new\s+NightmareVisionGameplayScripts\s*\(")
    )), None)
    constructor_ref = None
    configured_seed = False
    if constructor_call is not None:
        args, _ = _extract_call_arguments(init_body, init_body.find("(", constructor_call.start()))
        configured_seed = len(args) >= 4 and args[3].strip() == "seedNightmareVision"
        constructor_ref = _ref(
            engine_root, play_path, _line_at(play_code, init_offset + constructor_call.start()),
        ) if configured_seed else None
    startup_load_match = next(iter(_code_matches(
        init_body, re.compile(r"nightmareVisionScripts\s*\.\s*loadScope\s*\(\s*(['\"])stage\1")
    )), None)
    startup_load_ref = (
        _ref(engine_root, play_path, _line_at(play_code, init_offset + startup_load_match.start()))
        if startup_load_match else None
    )
    _, configure_ref = first_ref(
        engine_root, gameplay_path, gameplay_code, method(gameplay_path, gameplay_code, "loadScope"),
        re.compile(r"\bconfigure\s*\(\s*interp\s*,\s*entry\s*,\s*null\s*\)"),
    )
    seed_common_ref = first_ref(
        engine_root, play_path, play_code, method(play_path, play_code, "seedNightmareVision"),
        re.compile(r"\bseedNightmareVisionCommon\s*\("),
    )[1]
    seed_owner_ref = first_ref(
        engine_root, play_path, play_code, method(play_path, play_code, "seedNightmareVisionCommon"),
        re.compile(r"NightmareVisionSourceBindings\s*\.\s*bindOwner\s*\("),
    )[1]
    seed_gameplay_match, seed_gameplay_ref = first_ref(
        engine_root, play_path, play_code, method(play_path, play_code, "seedNightmareVision"),
        re.compile(r"NightmareVisionSourceBindings\s*\.\s*bindGameplay\s*\("),
    )
    seed_gameplay_args: list[str] = []
    if seed_gameplay_match is not None:
        seed_function = method(play_path, play_code, "seedNightmareVision")
        assert seed_function is not None
        seed_body, _ = seed_function
        seed_gameplay_args, _ = _extract_call_arguments(seed_body, seed_body.find("(", seed_gameplay_match.start()))
    init_script_is_function = (
        len(seed_gameplay_args) >= 5
        and re.match(r"function\s*\(", seed_gameplay_args[4].strip()) is not None
    )

    # Expand the gameplay names only where both the helper's literal name list
    # and the chart host's literal fields map contain the key.
    gameplay_names: dict[str, SourceRef] = {}
    names_match = re.search(r"\bgameplayNames\s*:\s*Array\s*<\s*String\s*>\s*=\s*\[", nv_binder_code)
    if names_match is not None:
        names_open = nv_binder_code.find("[", names_match.start(), names_match.end())
        names_region = _balanced_region(nv_binder_code, names_open, "[", "]")
        for match in re.finditer(r"(['\"])([A-Za-z_$][\w$]*)\1", names_region):
            gameplay_names[match.group(2)] = _ref(
                engine_root, nv_binder_path,
                _line_at(nv_binder_code, names_open + match.start()),
            )

    gameplay_fields: dict[str, SourceRef] = {}
    seed_region = method(play_path, play_code, "seedNightmareVision")
    seed_body = seed_region[0] if seed_region else ""
    seed_offset = seed_region[1] if seed_region else 0
    fields_match = re.search(r"\bvar\s+fields\s*:\s*Map\s*<[^=]+?=\s*\[", seed_body)
    if fields_match is not None:
        fields_open = seed_body.find("[", fields_match.start(), fields_match.end())
        fields_region = _balanced_region(seed_body, fields_open, "[", "]")
        for match in _code_matches(fields_region, MAP_BIND):
            gameplay_fields[match.group(2)] = _ref(
                engine_root, play_path,
                _line_at(play_code, seed_offset + fields_open + match.start()),
            )
    nv_gameplay_bind_method = method(nv_binder_path, nv_binder_code, "bindGameplay")
    nv_gameplay_body = nv_gameplay_bind_method[0] if nv_gameplay_bind_method else ""
    dynamic_gameplay_loop = (
        re.search(r"\bfor\s*\(\s*name\s+in\s+gameplayNames\s*\)", nv_gameplay_body) is not None
        and re.search(r"fields\s*!=\s*null\s*&&\s*fields\.exists\s*\(\s*name\s*\)", nv_gameplay_body) is not None
        and re.search(r"set\s*\(\s*vars\s*,\s*name\s*,\s*fields\.get\s*\(\s*name\s*\)\s*\)", nv_gameplay_body) is not None
    )
    gameplay_field_bindings: list[tuple[str, SourceRef, str | None]] = []
    if dynamic_gameplay_loop and len(seed_gameplay_args) >= 5 and seed_gameplay_args[2].strip() == "true" and seed_gameplay_args[3].strip() == "fields":
        for name in sorted(set(gameplay_names).intersection(gameplay_fields)):
            gameplay_field_bindings.append((name, gameplay_names[name], None))

    nv_owner_bindings = direct_bindings(engine_root, nv_binder_path, nv_binder_code, "bindOwner", BINDER_SET)
    # The chart seeder calls bindOwner with its three required arguments, so
    # the optional scriptContext stays null and the donor's `script` object is
    # not actually seeded by this route.
    nv_owner_bindings = [(name, ref) for name, ref in nv_owner_bindings if name != "script"]
    nv_gameplay_bindings = direct_bindings(engine_root, nv_binder_path, nv_binder_code, "bindGameplay", BINDER_SET)
    if not init_script_is_function:
        nv_gameplay_bindings = [(name, ref) for name, ref in nv_gameplay_bindings if name != "initScript"]
    constants_seed_ref = first_ref(
        engine_root, play_path, play_code,
        method(play_path, play_code, "seedNightmareVisionCommon"),
        re.compile(r"variables\s*\.\s*set\s*\(\s*(['\"])ScriptConstants\1\s*,\s*constants\b"),
    )[1]
    constants_path = engine_root / "source" / "NightmareVisionScriptConstants.hx"
    constants_code = _read_code(constants_path)
    constants_method_decl = re.search(r"\bfunction\s+getInstance\s*\(", constants_code) is not None
    if constants_seed_ref is None or not constants_method_decl:
        nv_gameplay_bindings = [(name, ref) for name, ref in nv_gameplay_bindings if name != "getInstance"]
    nv_owner_conditions = {
        "modFolder": "set only when the host modFolder argument is non-null",
    }
    nv_gameplay_conditions = {
        "getInstance": "set only when ScriptConstants.getInstance is available",
        "initScript": "set only after the host supplies a non-null owner-scoped loader",
    }
    owner_bindings_with_conditions = [
        (name, ref, nv_owner_conditions.get(name)) for name, ref in nv_owner_bindings
    ]
    gameplay_bindings_with_conditions = [
        (name, ref, nv_gameplay_conditions.get(name)) for name, ref in nv_gameplay_bindings
    ]
    gameplay_bindings_with_conditions.extend(gameplay_field_bindings)
    startup_route = [
        ("PlayState.initializeNightmareVisionScripts passes seedNightmareVision to gameplay loader", constructor_ref),
        ("PlayState.initializeNightmareVisionScripts loads chart scope", startup_load_ref),
        ("NightmareVisionGameplayScripts.loadScope invokes configure", configure_ref),
        ("seedNightmareVision calls shared owner seeder", seed_common_ref),
    ]
    append_route(
        "Nightmare Vision chart owner globals",
        "Nightmare Vision HScript",
        [*startup_route,
         ("seedNightmareVisionCommon calls bindOwner", seed_owner_ref),
         ("NightmareVisionSourceBindings.bindOwner contains literal name bindings",
          _ref(engine_root, nv_binder_path, _line_at(nv_binder_code, nv_binder_code.find("function bindOwner")))
          if "function bindOwner" in nv_binder_code else None)],
        owner_bindings_with_conditions,
    )
    bind_gameplay_method_ref = _ref(
        engine_root, nv_binder_path,
        _line_at(nv_binder_code, nv_binder_code.find("function bindGameplay")),
    ) if "function bindGameplay" in nv_binder_code else None
    append_route(
        "Nightmare Vision chart-local globals",
        "Nightmare Vision HScript",
        [*startup_route,
         ("seedNightmareVision calls bindGameplay with inPlaystate=true and fields map",
          seed_gameplay_ref if len(seed_gameplay_args) >= 5 and seed_gameplay_args[2].strip() == "true" and seed_gameplay_args[3].strip() == "fields" else None),
         ("NightmareVisionSourceBindings.bindGameplay contains literal and gameplayNames bindings",
          bind_gameplay_method_ref if dynamic_gameplay_loop else None)],
        gameplay_bindings_with_conditions,
    )
    return bindings, routes


def _extract_named(
    root: Path,
    files: Iterable[Path],
    regex: re.Pattern[str],
    dialect: str,
    group: str,
    kind: str,
    *,
    classify_value: bool = False,
) -> list[ApiEntry]:
    found: dict[tuple[str, str, str], ApiEntry] = {}
    for path in files:
        code = _read_code(path)
        for match in _code_matches(code, regex):
            entry_kind = _binding_kind(code, match.end()) if classify_value else kind
            _add_entry(found, ApiEntry(
                dialect=dialect,
                group=group,
                name=match.group(2),
                kind=entry_kind,
                source=[_ref(root, path, _line_at(code, match.start()))],
            ))
    return list(found.values())


def _active_preprocessor_conditions(code: str, offset: int) -> list[str]:
    """Return simple active Haxe ``#if`` guards before a source offset."""
    stack: list[str] = []
    for line in code[:offset].splitlines():
        directive = line.strip()
        conditional = re.fullmatch(r"#if\s+([A-Za-z_$][\w$]*)", directive)
        if conditional is not None:
            stack.append(conditional.group(1))
        elif directive.startswith("#elseif") and stack:
            branch = directive[len("#elseif"):].strip()
            stack[-1] = "elseif " + branch
        elif directive == "#else" and stack:
            stack[-1] = "else " + stack[-1]
        elif directive == "#end" and stack:
            stack.pop()
    return stack


def _psych_reachable_lua_helper_entries(root: Path, files: list[Path]) -> list[ApiEntry]:
    """Inventory callback helpers called from the pinned FunkinLua constructor.

    Psych registers some Lua APIs in helpers outside ``psychlua/``. Only
    helpers explicitly called as ``Class.addLuaCallbacks(lua)`` from the
    constructor count; unrelated callback declarations elsewhere in source do
    not become part of the donor surface.
    """
    funkin_lua = root / "source" / "psychlua" / "FunkinLua.hx"
    if not funkin_lua.is_file():
        return []
    funkin_code = _read_code(funkin_lua)
    constructor = _named_function_region(funkin_code, "new")
    if constructor is None:
        return []
    constructor_body, constructor_offset = constructor
    helper_calls = re.compile(
        r"#if\s+([A-Za-z_$][\w$]*)\s+([A-Za-z_$][\w$]*)"
        r"\s*\.\s*addLuaCallbacks\s*\(\s*lua\s*\)\s*;\s*#end"
    )
    helper_files: dict[str, tuple[Path, str, tuple[str, int], int, list[str]]] = {}
    for path in files:
        code = _read_code(path)
        for call in _code_matches(constructor_body, helper_calls):
            helper_name = call.group(2)
            if helper_name in helper_files:
                continue
            declaration = re.search(rf"\bclass\s+{re.escape(helper_name)}\b", code)
            method_declaration = re.search(
                r"\bfunction\s+addLuaCallbacks\s*\(", code,
            )
            method = _named_function_region(code, "addLuaCallbacks")
            if declaration is None or method_declaration is None or method is None:
                continue
            method_conditions = _active_preprocessor_conditions(code, method_declaration.start())
            if "LUA_ALLOWED" not in method_conditions:
                continue
            class_conditions = _active_preprocessor_conditions(code, declaration.start())
            call_condition = call.group(1)
            if any(condition != call_condition for condition in class_conditions):
                continue
            helper_files[helper_name] = (
                path, code, method, method_declaration.start(),
                list(dict.fromkeys([call_condition, *class_conditions, *method_conditions])),
            )

    entries: dict[tuple[str, str, str], ApiEntry] = {}
    for call in _code_matches(constructor_body, helper_calls):
        helper_name = call.group(2)
        resolved = helper_files.get(helper_name)
        if resolved is None:
            continue
        path, code, method, declaration_offset, conditions = resolved
        method_body, method_offset = method
        call_ref = _ref(root, funkin_lua,
                        _line_at(funkin_code, constructor_offset + call.start()))
        method_ref = _ref(root, path, _line_at(code, declaration_offset))
        for binding in _code_matches(method_body, LUA_CALLBACK):
            name = binding.group(2)
            registration_ref = _ref(root, path, _line_at(code, method_offset + binding.start()))
            entry = ApiEntry(
                dialect="Psych Lua",
                group="registered functions",
                name=name,
                kind="function",
                source=[registration_ref, method_ref, call_ref],
                contract={
                    "registration_conditions": conditions,
                    "registration_chain": [
                        {"step": f"FunkinLua.new calls {helper_name}.addLuaCallbacks(lua)",
                         "source": asdict(call_ref), "condition": call.group(1)},
                        {"step": f"{helper_name}.addLuaCallbacks is Lua-gated",
                         "source": asdict(method_ref), "condition": "LUA_ALLOWED"},
                    ],
                },
            )
            _add_entry(entries, entry)
    return list(entries.values())


def _psych_donor_entries(root: Path) -> list[ApiEntry]:
    entries: list[ApiEntry] = []
    files = list(iter_haxe_files(root))
    psychlua = [path for path in files if "psychlua" in path.parts]
    entries.extend(_extract_named(root, psychlua, LUA_CALLBACK, "Psych Lua", "registered functions", "function"))
    entries.extend(_psych_reachable_lua_helper_entries(root, files))

    hscript = root / "source" / "psychlua" / "HScript.hx"
    if hscript.is_file():
        entries.extend(_extract_named(root, [hscript], PSYCH_SET, "Psych HScript", "seeded globals", "value", classify_value=True))

    hook_files = [
        path for path in (
            root / "source" / "states" / "PlayState.hx",
            root / "source" / "substates" / "GameOverSubstate.hx",
        ) if path.is_file()
    ]
    entries.extend(_extract_named(root, hook_files, PSYCH_HOOK_CALL,
                                  "Psych chart hooks", "dispatched callbacks", "callback"))
    return entries


def _nv_donor_entries(root: Path) -> list[ApiEntry]:
    entries: list[ApiEntry] = []
    funkin_script = root / "source" / "funkin" / "scripts" / "FunkinScript.hx"
    if funkin_script.is_file():
        entries.extend(_extract_named(root, [funkin_script], NV_SET, "Nightmare Vision HScript", "seeded globals", "value", classify_value=True))

    hook_files = [
        path for path in iter_haxe_files(root)
        if path.name in {"PlayState.hx", "ScriptedState.hx", "ScriptedSubstate.hx", "GameOverSubstate.hx"}
    ]
    entries.extend(_extract_named(root, hook_files, NV_HOOK_CALL, "Nightmare Vision HScript", "dispatched callbacks", "callback"))

    nv_playstate = root / "source" / "funkin" / "states" / "PlayState.hx"
    if nv_playstate.is_file():
        code = _read_code(nv_playstate)
        methods: dict[str, ApiEntry] = {}
        for member_name, (member_kind, line_number) in _class_member_names(code, "PlayState").items():
            _add_entry(methods, ApiEntry(
                dialect="Nightmare Vision chart state",
                group="PlayState member surface",
                name=member_name,
                kind=f"reflective {member_kind}",
                source=[_ref(root, nv_playstate, line_number)],
            ))
        entries.extend(methods.values())
    return entries


def _metadata(root: Path, label: str) -> SourceMetadata:
    root = root.expanduser().resolve()
    if not root.is_dir() or not (root / "source").is_dir():
        return SourceMetadata(label, False, str(root))
    revision = "unknown"
    tracked_tree = "unknown"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            check=True, capture_output=True, text=True, timeout=5,
        )
        revision = result.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
            check=True, capture_output=True, text=True, timeout=10,
        )
        tracked_tree = "clean" if not result.stdout.strip() else "modified"
    except (OSError, subprocess.SubprocessError):
        pass
    version = "unknown"
    project = root / "Project.xml"
    if project.is_file():
        try:
            xml_root = ET.parse(project).getroot()
            app = xml_root.find("app")
            if app is not None:
                version = app.attrib.get("version", "unknown")
        except (ET.ParseError, OSError):
            pass
    if label == "Nightmare Vision":
        main = root / "source" / "Main.hx"
        if main.is_file():
            main_code = _read_code(main)
            match = re.search(r"\bNMV_VERSION\s*:\s*String\s*=\s*(['\"])(.*?)\1", main_code)
            if match:
                version = f"NMV {match.group(2)} / project {version}"
    elif label == "Psych Engine":
        main_menu = root / "source" / "states" / "MainMenuState.hx"
        if main_menu.is_file():
            main_code = _read_code(main_menu)
            match = re.search(r"\bpsychEngineVersion\s*:\s*String\s*=\s*(['\"])(.*?)\1", main_code)
            if match:
                version = f"Psych Engine {match.group(2)} / project {version}"
    return SourceMetadata(label, True, str(root), revision, version, tracked_tree, len(list(iter_haxe_files(root))))


def _engine_inventory(
    root: Path, candidate_names: set[str],
    source_binding_routes: tuple[dict[str, dict[str, list[SourceRef]]], list[dict[str, object]]] | None = None,
) -> tuple[dict[str, list[SourceRef]], dict[str, list[SourceRef]], dict[str, list[SourceRef]], list[str]]:
    direct: dict[str, list[SourceRef]] = defaultdict(list)
    text_mentions: dict[str, list[SourceRef]] = defaultdict(list)
    dynamic_hooks: dict[str, list[SourceRef]] = defaultdict(list)
    active_files = list(iter_haxe_files(root))
    code_by_path: dict[Path, str] = {path: _read_code(path) for path in active_files}
    host_callback_routes: dict[str, list[SourceRef]] = defaultdict(list)
    psych_runtime_routes, _psych_runtime_dynamic = _psych_runtime_dispatch_inventory(root)
    for name, refs in psych_runtime_routes.items():
        direct["@psych-hook:" + name].extend(refs)
    gameover_routes, _gameover_dynamic = _source_gameover_callback_routes(root)
    for dialect, names in gameover_routes.items():
        prefix = "@nv-hook:" if dialect == "Nightmare Vision HScript" else "@psych-hook:"
        for name, refs in names.items():
            direct[prefix + name].extend(refs)
    if source_binding_routes is None:
        source_binding_routes = _source_binding_audit(root)
    source_bindings, _route_records = source_binding_routes
    for dialect, names in source_bindings.items():
        for name, refs in names.items():
            direct[f"@seed:{dialect}:{name}"].extend(refs)

    binding_files = {
        "PlayState.hx", "PluginManager.hx", "LuaCompatInterp.hx", "PsychHscriptCompat.hx",
        "NightmareVisionScriptInterp.hx", "PsychRuntimeBindings.hx", "PsychSourceBindings.hx",
        "PsychReflectionBindings.hx", "PsychScoreScriptGlobals.hx", "SourceIrisBridge.hx",
        "SourceScriptTextBindings.hx",
    }
    for path, code in code_by_path.items():
        if path.name in binding_files:
            matches: list[tuple[str, int]] = [
                (match.group(2), match.start()) for match in _code_matches(code, DIRECT_BIND)
            ]
            # Nightmare Vision's common globals are assembled into a literal map
            # before being applied with variables.set(name, value).
            if path.name == "PlayState.hx":
                preset_match = re.search(r"\bvar\s+preset\s*:\s*Map\s*<[^;=]+>\s*=\s*\[", code)
                if preset_match:
                    opening = code.find("[", preset_match.start())
                    region = _balanced_region(code, opening, "[", "]")
                    matches.extend(
                        (match.group(2), opening + match.start())
                        for match in _code_matches(region, MAP_BIND)
                    )
            if path.name in {"PsychRuntimeBindings.hx", "PsychSourceBindings.hx"}:
                matches.extend(_literal_loop_bindings(code))
            for name, offset in matches:
                direct[name].append(_ref(root, path, _line_at(code, offset)))
        for match in _code_matches(code, re.compile(r"\b(?:callOnScripts|callOnLuas|callOnHScript|callOnHaxe|callOnLua|callAllHScript|callHscript)\s*\(")):
            opening = code.find("(", match.start())
            arguments, _ = _extract_call_arguments(code, opening)
            if not arguments:
                continue
            method = match.group(0).split("(")[0]
            names = _literal_callback_choices(arguments[0])
            for name in names:
                ref = _ref(root, path, _line_at(code, match.start()))
                direct["@psych-hook:" + name].append(ref)
                if method in {"callAllHScript", "callHscript"}:
                    host_callback_routes[name.lower()].append(ref)
        for match in _code_matches(code, re.compile(r"\bcallNightmareVision\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1")):
            dynamic_hooks[match.group(2)].append(_ref(root, path, _line_at(code, match.start())))
        hook_call = re.compile(r"\b(?:nightmareVisionScripts|scripts|scriptGroup|script|newScript)\s*\.\s*call\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1")
        for match in _code_matches(code, hook_call):
            direct["@nv-hook:" + match.group(2)].append(_ref(root, path, _line_at(code, match.start())))
            dynamic_hooks[match.group(2)].append(_ref(root, path, _line_at(code, match.start())))
        for match in _code_matches(code, re.compile(r"\bcallNightmareVision\s*\(\s*(['\"])([A-Za-z_$][\w$]*)\1")):
            direct["@nv-hook:" + match.group(2)].append(_ref(root, path, _line_at(code, match.start())))
        # These broad interfaces expose members dynamically; they are evidence
        # of a path to the surface, not proof for any individual method.
        class_parent = re.search(r"\bbindClassParent\s*\(\s*PlayState\s*\)", code)
        if class_parent:
            dynamic_hooks["@class-parent:PlayState"].append(_ref(root, path, _line_at(code, class_parent.start())))
        if "classParents" in code and "usesClassParent" in code and "Type.getClassFields" in code:
            dynamic_hooks["@class-parent-resolver"].append(_ref(root, path, 1))

        for name in _code_identifiers(code, candidate_names):
            text_mentions[name].append(_ref(root, path, 1))

    # callAllHScript routes through EngineCompat.callbackNames at invocation
    # time. Apply only aliases whose host spelling is actually dispatched.
    for alias in _callback_alias_inventory(root):
        alias_ref = SourceRef(alias["source"]["path"], alias["source"]["line"])
        for host_name in alias["host_callback_spellings"]:
            for callback in alias["script_callback_spellings"]:
                text_mentions[callback].append(alias_ref)
            refs = host_callback_routes.get(host_name.lower(), [])
            if not refs:
                continue
            for callback in alias["script_callback_spellings"]:
                direct["@psych-hook:" + callback].extend([alias_ref, *refs])

    # Keep mention evidence bounded and deterministic.
    return direct, text_mentions, dynamic_hooks, [str(path) for path in active_files]


def _apply_statuses(
    entries: list[ApiEntry],
    engine_root: Path,
    direct: dict[str, list[SourceRef]],
    mentions: dict[str, list[SourceRef]],
    dynamic: dict[str, list[SourceRef]],
) -> None:
    reflection = _nightmare_vision_reflection_evidence(engine_root)
    has_nv_reflection = reflection["status"] == "dynamic-path-present-unverified"
    engine_playstate = engine_root / "source" / "PlayState.hx"
    engine_code = strip_haxe_comments(engine_playstate.read_text(encoding="utf-8", errors="replace")) if engine_playstate.is_file() else ""
    engine_members = _class_member_names(engine_code, "PlayState")
    for entry in entries:
        if entry.group == "dispatched callbacks":
            prefix = "@nv-hook:" if entry.dialect.startswith("Nightmare Vision") else "@psych-hook:"
            direct_key = prefix + entry.name
        else:
            direct_key = entry.name
        binder_key = f"@seed:{entry.dialect}:{entry.name}"
        binder_evidence = direct.get(binder_key, [])
        evidence = binder_evidence or direct.get(direct_key, [])
        if entry.group == "PlayState member surface":
            # The current host's Nightmare Vision interpreter exposes matching
            # PlayState members through a dynamic class-parent lookup.
            if has_nv_reflection and entry.name in engine_members:
                entry.status = "unverified"
                entry.engine_evidence.append(f"dynamic PlayState class-parent reflection; matching {engine_members[entry.name][0]} declaration")
            elif entry.name in engine_members:
                entry.status = "names-only"
                entry.engine_evidence.append(f"matching {engine_members[entry.name][0]} declaration without confirmed script binding")
            else:
                entry.status = "missing"
            continue
        if evidence:
            entry.status = "implemented"
            if binder_evidence:
                entry.engine_evidence.append("wired source binder call-chain")
            entry.engine_evidence.extend(f"{ref.path}:{ref.line}" for ref in evidence[:3])
        elif entry.name in mentions:
            entry.status = "names-only"
            refs = mentions[entry.name]
            entry.engine_evidence.extend(f"{Path(ref.path).name} (mention only)" for ref in refs[:2])
        else:
            entry.status = "missing"


def _example_corpora(examples_root: Path, engine_root: Path) -> dict[str, object]:
    roots = [
        {"dialect": "Psych", "path": str((examples_root / "psych").resolve()), "available": (examples_root / "psych").is_dir()},
        {"dialect": "Nightmare Vision", "path": str((examples_root / "nightmare vision").resolve()), "available": (examples_root / "nightmare vision").is_dir()},
    ]
    legacy_prefix = "/run/media/cammie/External Storage/FNF-Example-Mods"
    legacy_modules = []
    tests_root = engine_root / "tools" / "tests"
    if tests_root.is_dir():
        for path in sorted(tests_root.glob("test_*.py")):
            try:
                if legacy_prefix in path.read_text(encoding="utf-8", errors="replace"):
                    legacy_modules.append(path.relative_to(engine_root).as_posix())
            except OSError:
                continue
    return {
        "root": str(examples_root.resolve()),
        "available": examples_root.is_dir(),
        "dialect_roots": roots,
        "legacy_linux_test_modules": legacy_modules,
        "note": "The Windows corpus roots are local evidence inputs; CI can retain fixture tests and snapshots when absent.",
    }


def audit(
    engine_root: Path = REPO_ROOT,
    psych_root: Path = DEFAULT_PSYCH_ROOT,
    nv_root: Path = DEFAULT_NV_ROOT,
    examples_root: Path = DEFAULT_EXAMPLES_ROOT,
) -> dict[str, object]:
    engine_root = engine_root.expanduser().resolve()
    psych_root = psych_root.expanduser().resolve()
    nv_root = nv_root.expanduser().resolve()
    examples_root = examples_root.expanduser().resolve()
    metadata = [
        _metadata(engine_root, "Engine"),
        _metadata(psych_root, "Psych Engine"),
        _metadata(nv_root, "Nightmare Vision"),
    ]
    entries: list[ApiEntry] = []
    if metadata[1].available:
        entries.extend(_psych_donor_entries(psych_root))
    if metadata[2].available:
        entries.extend(_nv_donor_entries(nv_root))
    source_binding_routes = _source_binding_audit(engine_root)
    direct, mentions, dynamic, engine_files = _engine_inventory(
        engine_root, {entry.name for entry in entries}, source_binding_routes,
    )
    _apply_statuses(entries, engine_root, direct, mentions, dynamic)
    roots = {
        "Psych Lua": psych_root,
        "Psych HScript": psych_root,
        "Psych chart hooks": psych_root,
        "Nightmare Vision HScript": nv_root,
        "Nightmare Vision chart state": nv_root,
    }
    dynamic_donor_sites = _build_contract_inventory(entries, roots, engine_root)
    reflection = _nightmare_vision_reflection_evidence(engine_root)
    aliases = _callback_alias_inventory(engine_root)
    dynamic_engine_sites = _dynamic_dispatch_sites(engine_root)
    sorted_entries = [asdict(item) for item in sorted(entries, key=lambda e: (e.dialect, e.group, e.name.lower()))]
    contract_inventory = {
        "schema_version": 2,
        "generated": date.today().isoformat(),
        "source_metadata": [asdict(item) for item in metadata],
        "status_definitions": {
            "implemented": "A literal engine binding, hook call, recognized callback-name alias, or explicit statically wired source-binder call chain was found. This is static support evidence only.",
            "unverified": "A broad class-parent/reflection route appears to expose a matching member; behavior is not proven.",
            "names-only": "The name occurs in engine code without a direct binding or mapped dispatch route.",
            "missing": "No binding or route was found by this static audit.",
            "behavioral_verification": "unverified unless an explicitly maintained test manifest later supplies execution/assertion proof; test name references are not proof.",
            "test_evidence": "Counts are exact; up to two test references per evidence class are sampled. A semantic candidate only indicates a test file contains runner/assertion markers; it is not proof.",
        },
        "entries": [
            {"dialect": item["dialect"], "group": item["group"], "name": item["name"],
             "kind": item["kind"], "source": item["source"], "contract": item["contract"]}
            for item in sorted_entries
        ],
        "callback_aliases": aliases,
        "source_binding_routes": source_binding_routes[1],
        "dynamic_dispatch_sites": {"donor": dynamic_donor_sites, "engine": dynamic_engine_sites},
        "nightmare_vision_reflection": reflection,
        "example_corpora": _example_corpora(examples_root, engine_root),
    }
    return {
        "generated": date.today().isoformat(),
        "metadata": [asdict(item) for item in metadata],
        "entries": sorted_entries,
        "contract_inventory": contract_inventory,
        "callback_aliases": aliases,
        "source_binding_routes": source_binding_routes[1],
        "example_corpora": contract_inventory["example_corpora"],
        "dynamic_dispatch": {
            "nightmare_vision_playstate_reflection": reflection["status"] == "dynamic-path-present-unverified",
            "nightmare_vision_reflection": reflection,
            "nightmare_vision_dispatch_names": sorted(name for name in dynamic if not name.startswith("@")),
            "donor_dynamic_sites": dynamic_donor_sites,
            "engine_dynamic_sites": dynamic_engine_sites,
        },
        "engine_source_file_count": len(engine_files),
    }


def _summaries(entries: list[dict[str, object]]) -> list[tuple[str, str, Counter[str]]]:
    groups: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for entry in entries:
        groups[(str(entry["dialect"]), str(entry["group"]))][str(entry["status"])] += 1
    return [(dialect, group, counts) for (dialect, group), counts in sorted(groups.items())]


def render_markdown(report: dict[str, object], full_list: bool = False) -> str:
    metadata = report["metadata"]
    entries = report["entries"]
    assert isinstance(metadata, list) and isinstance(entries, list)
    lines = [
        "# Chart scripting API coverage audit",
        "",
        f"Generated: {report['generated']}",
        "",
        "This is a static source audit. `implemented` means a literal binding, direct dispatch, explicit callback-name alias, or fully traced source-binder call chain was found; `names-only` means the name occurs without such evidence; `unverified` marks broad reflective reachability; `missing` means no route was found. Every `implemented` entry remains behaviorally unverified unless separately supported by an execution-and-assertion test.",
        "",
        "## Source snapshots",
        "",
        "| Source | Version | Revision | Tracked tree | Haxe files | Path |",
        "|---|---|---|---|---:|---|",
    ]
    for source in metadata:
        assert isinstance(source, dict)
        state = f"{source['version']}" if source["available"] else "unavailable"
        lines.append(f"| {source['label']} | {state} | {source['revision']} | {source['tracked_tree']} | {source['source_files']} | `{source['path']}` |")
    lines += ["", "## Coverage summary", "", "| Dialect | Inventory | Implemented | Unverified | Names only | Missing |", "|---|---|---:|---:|---:|---:|"]
    for dialect, group, counts in _summaries(entries):
        total = sum(counts.values())
        lines.append(f"| {dialect} | {group} | {counts['implemented']} | {counts['unverified']} | {counts['names-only']} | {counts['missing']} |")
    if not entries:
        lines.append("| - | No local donor inventory | 0 | 0 | 0 | 0 |")

    routes = report.get("source_binding_routes", [])
    lines += ["", "## Wired source binder routes", ""]
    if not isinstance(routes, list) or not routes:
        lines.append("No source-binder routes were audited.")
    else:
        for route in routes:
            if not isinstance(route, dict):
                continue
            chain = route.get("chain", [])
            found_steps = [step for step in chain if isinstance(step, dict) and step.get("status") == "found"]
            chain_names = " → ".join(str(step.get("step", "")) for step in found_steps)
            binding_count = len(route.get("binding_names", []))
            lines.append(
                f"- **{route.get('dialect')} / {route.get('name')}**: `{route.get('status')}`; "
                f"{binding_count} globals supported by the complete static chain. {chain_names}. "
                "Behavior remains unverified."
            )

    lines += ["", "## Uncovered names", ""]
    gaps = [entry for entry in entries if entry["status"] in {"missing", "names-only", "unverified"}]
    if not gaps:
        lines.append("No uncovered names were found in the available donor sources.")
    else:
        bucketed: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
        for entry in gaps:
            bucketed[(str(entry["dialect"]), str(entry["group"]), str(entry["status"]))].append(entry)
        cap = None if full_list else 18
        for (dialect, group, status), rows in sorted(bucketed.items()):
            names = sorted(str(row["name"]) for row in rows)
            visible = names if cap is None else names[:cap]
            suffix = "" if len(visible) == len(names) else f" … (+{len(names) - len(visible)} more)"
            lines.append(f"- **{dialect} / {group} / {status} ({len(names)}):** `{', '.join(visible)}`{suffix}")

    dynamic = report["dynamic_dispatch"]
    assert isinstance(dynamic, dict)
    lines += ["", "## Dynamic surfaces", ""]
    lines.append(f"- Engine HScript uses Nightmare Vision `PlayState` class-parent reflection: `{str(dynamic['nightmare_vision_playstate_reflection']).lower()}`. Member-by-member coverage is marked unverified where a matching engine declaration exists.")
    names = dynamic["nightmare_vision_dispatch_names"]
    lines.append(f"- Literal Nightmare Vision event dispatches currently found in engine: {len(names)}.")
    lines.append("- Runtime-computed callback names and members reachable through dynamic objects cannot be enumerated by this audit.")
    corpora = report.get("example_corpora", {})
    if isinstance(corpora, dict):
        lines += ["", "## Local example corpus", ""]
        lines.append(f"- Windows example root: `{corpora.get('root', 'unavailable')}` ({'available' if corpora.get('available') else 'unavailable'}).")
        roots = corpora.get("dialect_roots", [])
        if isinstance(roots, list):
            for item in roots:
                if isinstance(item, dict):
                    lines.append(f"- {item['dialect']}: `{item['path']}` ({'available' if item['available'] else 'unavailable'}).")
        legacy = corpora.get("legacy_linux_test_modules", [])
        if isinstance(legacy, list):
            lines.append(f"- Existing tests with the former Linux example-root literal: {len(legacy)} modules; use the Windows roots above for local corpus evidence.")
    lines += ["", "## Reproduction", "", "```powershell", "python tools/audit_script_api_coverage.py --output tools/reports/script-api-coverage.md --contract-output tools/reports/script-api-contracts.json", "```", ""]
    lines.insert(-1, "Use `--json-output <path>` for full coverage evidence and `--contract-output <path>` for the source contract snapshot. Contract snapshots keep exact test-reference counts and sample at most two files per evidence class; neither name references nor semantic candidates are behavior proofs.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help="engine checkout root")
    parser.add_argument("--psych-root", type=Path, default=DEFAULT_PSYCH_ROOT, help="Psych Engine donor checkout")
    parser.add_argument("--nightmare-vision-root", type=Path, default=DEFAULT_NV_ROOT, help="Nightmare Vision donor checkout")
    parser.add_argument("--examples-root", type=Path, default=DEFAULT_EXAMPLES_ROOT, help="local Psych/NV example corpus root (with psych and nightmare vision subfolders)")
    parser.add_argument("--output", type=Path, help="write compact Markdown report")
    parser.add_argument("--json-output", type=Path, help="write complete machine-readable inventory")
    parser.add_argument("--contract-output", type=Path, help="write source-backed signatures, defaults, call sites, and validation evidence")
    parser.add_argument("--full-list", action="store_true", help="include all static uncovered names in Markdown")
    parser.add_argument("--require-donors", action="store_true", help="fail when either donor checkout is absent")
    args = parser.parse_args(argv)

    report = audit(args.repo_root, args.psych_root, args.nightmare_vision_root, args.examples_root)
    missing = [source["label"] for source in report["metadata"][1:] if not source["available"]]
    if args.require_donors and missing:
        print("Missing donor checkout(s): " + ", ".join(missing), file=sys.stderr)
        return 2
    markdown = render_markdown(report, args.full_list)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(markdown, encoding="utf-8")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.contract_output:
        args.contract_output.parent.mkdir(parents=True, exist_ok=True)
        args.contract_output.write_text(json.dumps(report["contract_inventory"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not args.output and not args.json_output and not args.contract_output:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
