"""
Utility tools — text processing, formatting and safe arithmetic.
"""

from __future__ import annotations

import ast
import json
import math
import operator

# A deliberately tiny expression evaluator. eval() on user/model input would
# be a remote-code-execution hole, so we walk the AST and only allow maths.
_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_NAMES = {"pi": math.pi, "e": math.e, "tau": math.tau}
_FUNCS = {
    name: getattr(math, name)
    for name in ("sqrt", "log", "log10", "log2", "sin", "cos", "tan", "floor", "ceil", "exp", "fabs")
}
_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})


def _evaluate(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("only numbers are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _evaluate(node.left), _evaluate(node.right)
        if type(node.op) is ast.Pow and abs(right) > 1000:
            raise ValueError("exponent too large")
        return _BINARY[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_evaluate(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*(_evaluate(arg) for arg in node.args))
    raise ValueError("unsupported expression")


def register(mcp):

    @mcp.tool()
    def calculate(expression: str) -> str:
        """
        Evaluate a maths expression safely.
        Supports + - * / // % **, brackets, pi/e, and sqrt, log, sin, cos,
        tan, floor, ceil, abs, round, min, max.
        """
        try:
            result = _evaluate(ast.parse(expression, mode="eval"))
        except ZeroDivisionError:
            return "That's a division by zero."
        except Exception:
            return f'I couldn\'t evaluate "{expression}". Keep it to plain arithmetic.'

        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"{expression} = {result:,}" if isinstance(result, int) else f"{expression} = {result:,.6g}"

    @mcp.tool()
    def format_json(data: str) -> str:
        """Pretty-print a JSON string."""
        try:
            return json.dumps(json.loads(data), indent=2, ensure_ascii=False)
        except json.JSONDecodeError as error:
            return f"Invalid JSON: {error}"

    @mcp.tool()
    def word_count(text: str) -> dict:
        """Count words, characters, lines and estimated reading time."""
        words = text.split()
        return {
            "characters": len(text),
            "characters_no_spaces": len(text.replace(" ", "")),
            "words": len(words),
            "lines": len(text.splitlines()),
            "sentences": sum(text.count(mark) for mark in ".!?"),
            "reading_time_minutes": round(len(words) / 200, 1),
        }
