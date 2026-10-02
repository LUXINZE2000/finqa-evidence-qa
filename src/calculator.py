"""No eval/exec: bounded Decimal operations and evidence quote validation."""
import re
from decimal import Decimal, InvalidOperation, localcontext


def number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a number")
    text = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    percent = text.endswith("%")
    text = text.removesuffix("%")
    try:
        result = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Invalid numeric value") from exc
    if not result.is_finite() or abs(result) > Decimal("1e30"):
        raise ValueError("Number out of range")
    return result / 100 if percent else result


def quoted_numbers(text):
    # OCR often repeats signed amounts as "-170 ( 170 )". The parenthesized
    # duplicate is not evidence for a positive 170.
    normalized = re.sub(
        r"(-\s*\$?\s*([\d,]+(?:\.\d+)?))\s*\(\s*\2\s*\)",
        r"\1", text)
    pattern = r"\(\s*\$?\s*[\d,]+(?:\.\d+)?\s*%?\s*\)|(?<![\w])[-+]?\s*\$?\s*\d[\d,]*(?:\.\d+)?\s*%?"
    return [number(x) for x in re.findall(pattern, normalized)]


def validate_and_calculate(payload, evidence):
    if payload.get("status") == "abstain":
        return {"status": "abstain", "reason": str(payload.get("reason", "Insufficient evidence"))}
    if payload.get("status") != "answer":
        raise ValueError("Unknown answer status")
    sources = {c["id"]: c["text"] for c in evidence}
    operands = payload.get("operands", [])
    steps = payload.get("steps", [])
    if not 1 <= len(operands) <= 20 or not 1 <= len(steps) <= 12:
        raise ValueError("Answer must have 1–20 operands and 1–12 steps")
    values, citations = {}, set()
    for i, operand in enumerate(operands):
        cid, quote = operand["evidence_id"], operand["quote"]
        if cid not in sources or not quote or quote not in sources[cid]:
            raise ValueError("Citation or exact source quote is invalid")
        value = number(operand["value"])
        if value not in quoted_numbers(quote):
            raise ValueError("Operand value does not occur in its source quote")
        values[f"n{i}"] = value
        citations.add(cid)
    # Constants support percentage conversion and conventional averages. The
    # evaluator still checks formula choice; this validator is not semantic proof.
    def resolve(ref):
        if ref in values:
            return values[ref]
        if ref in {"const_1", "const_2", "const_3", "const_4", "const_100", "const_1000", "const_1000000"}:
            return number(ref[6:])
        raise ValueError(f"Invalid or forward reference: {ref}")
    with localcontext() as ctx:
        ctx.prec = 28
        for i, step in enumerate(steps):
            op, refs = step["op"], step["args"]
            if len(refs) != (1 if op == "identity" else 2):
                raise ValueError("Invalid operation arity")
            args = [resolve(r) for r in refs]
            if op == "identity":
                result = args[0]
            elif op == "add":
                result = args[0] + args[1]
            elif op == "subtract":
                result = args[0] - args[1]
            elif op == "multiply":
                result = args[0] * args[1]
            elif op == "divide":
                if args[1] == 0:
                    raise ValueError("Division by zero")
                result = args[0] / args[1]
            else:
                raise ValueError("Unsupported operation")
            values[f"s{i}"] = number(result)
    result = values[f"s{len(steps)-1}"]
    kind = payload.get("kind")
    if kind not in {"number", "percent"}:
        raise ValueError("kind must be number or percent")
    unit = str(payload.get("unit", ""))
    return {"status": "answer", "value": str(result), "kind": kind, "unit": unit,
            "citations": sorted(citations), "operands": operands, "steps": steps}
