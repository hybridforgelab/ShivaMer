"""Python source -> Mermaid flowchart.

The graph is built with "pending edges": every statement handler receives the
list of dangling edges (source node + optional edge label) that must point at
the next node, and returns the new list once it is done. Branches simply return
the union of their exits, so code after an ``if`` keeps flowing instead of
being attached to the End node.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

MAX_LABEL = 80

Pending = list[tuple[str, str | None]]


def escape_label(text: str) -> str:
    """Make arbitrary text safe inside a quoted Mermaid label."""
    text = " ".join(text.split()) if "\n" not in text else text
    if len(text) > MAX_LABEL:
        text = text[: MAX_LABEL - 1] + "…"
    text = (
        text.replace("#", "#35;")
        .replace('"', "#quot;")
        .replace("|", "#124;")
        .replace("<", "#lt;")
        .replace(">", "#gt;")
    )
    return "<br/>".join(line.rstrip() for line in text.splitlines()) or " "


def code(node: ast.AST) -> str:
    try:
        return ast.unparse(node)
    except (RecursionError, ValueError, AttributeError):
        return node.__class__.__name__


def _input_prompt(node: ast.AST) -> str | None:
    """Return the prompt of the first input() call inside node, if any."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == "input":
            if sub.args and isinstance(sub.args[0], ast.Constant) and isinstance(sub.args[0].value, str):
                return sub.args[0].value
            return code(sub)
    return None


def _print_text(node: ast.AST) -> str | None:
    """For print('literal') return the literal, for print(x) the arguments."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
        if len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
        return ", ".join(code(a) for a in node.args) or "print()"
    return None


SHAPES = {
    "rect": ('["', '"]'),
    "round": ('(["', '"])'),
    "decision": ('{"', '"}'),
    "io": ('[/"', '"/]'),
}


@dataclass
class Loop:
    head: str
    breaks: Pending = field(default_factory=list)


@dataclass
class Scope:
    end: str
    loops: list[Loop] = field(default_factory=list)


class FlowBuilder:
    def __init__(self) -> None:
        self._count = 0
        self._blocks: list[list[str]] = [[]]
        self.edges: list[str] = []
        self._scopes: list[Scope] = []

    # -- low level ---------------------------------------------------------
    def node(self, label: str, shape: str = "rect") -> str:
        self._count += 1
        node_id = f"n{self._count}"
        left, right = SHAPES[shape]
        self._blocks[-1].append(f"{node_id}{left}{escape_label(label)}{right}")
        return node_id

    def edge(self, src: str, dst: str, label: str | None = None) -> None:
        if label:
            self.edges.append(f'{src} -->|"{escape_label(label)}"| {dst}')
        else:
            self.edges.append(f"{src} --> {dst}")

    def connect(self, pending: Pending, dst: str) -> None:
        for src, label in pending:
            self.edge(src, dst, label)

    def step(self, pending: Pending, label: str, shape: str = "rect") -> Pending:
        n = self.node(label, shape)
        self.connect(pending, n)
        return [(n, None)]

    # -- scopes ------------------------------------------------------------
    def subgraph(self, title: str, body) -> None:
        self._count += 1
        sg_id = f"sg{self._count}"
        self._blocks.append([])
        body()
        inner = self._blocks.pop()
        self._blocks[-1].append(f'subgraph {sg_id}["{escape_label(title)}"]')
        self._blocks[-1].extend("    " + line for line in inner)
        self._blocks[-1].append("end")

    def flow(self, stmts: list[ast.stmt], start_label: str) -> None:
        start = self.node(start_label, "round")
        # Reserve the End id now, but declare it after the body so it is drawn last.
        self._count += 1
        end = f"n{self._count}"
        self._scopes.append(Scope(end=end))
        pending = self.block(stmts, [(start, None)])
        self._scopes.pop()
        left, right = SHAPES["round"]
        self._blocks[-1].append(f"{end}{left}End{right}")
        self.connect(pending, end)

    def build(self) -> str:
        lines = ["flowchart TD"] + self._blocks[0] + self.edges
        return "\n".join(lines[:1] + ["    " + line for line in lines[1:]])

    # -- statements --------------------------------------------------------
    def block(self, stmts: list[ast.stmt], pending: Pending) -> Pending:
        for stmt in stmts:
            pending = self.stmt(stmt, pending)
        return pending

    def stmt(self, s: ast.stmt, pending: Pending) -> Pending:
        scope = self._scopes[-1]

        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self.function(s)
            return pending
        if isinstance(s, ast.ClassDef):
            self.klass(s)
            return pending

        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
            return pending  # docstring
        if isinstance(s, ast.Pass):
            return pending

        if isinstance(s, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            value = s.value
            prompt = _input_prompt(value) if value is not None else None
            if prompt is not None:
                return self.step(pending, prompt, "io")
            return self.step(pending, code(s))

        if isinstance(s, ast.Expr):
            text = _print_text(s.value)
            if text is not None:
                return self.step(pending, text, "io")
            prompt = _input_prompt(s.value)
            if prompt is not None:
                return self.step(pending, prompt, "io")
            return self.step(pending, code(s))

        if isinstance(s, ast.If):
            d = self.node(f"{code(s.test)}?", "decision")
            self.connect(pending, d)
            yes = self.block(s.body, [(d, "Yes")])
            no = self.block(s.orelse, [(d, "No")])
            return yes + no

        if isinstance(s, ast.While):
            d = self.node(f"{code(s.test)}?", "decision")
            self.connect(pending, d)
            return self.loop(d, s, [(d, "Yes")], [(d, "No")])

        if isinstance(s, (ast.For, ast.AsyncFor)):
            d = self.node(f"for {code(s.target)} in {code(s.iter)}", "decision")
            self.connect(pending, d)
            return self.loop(d, s, [(d, "next")], [(d, "done")])

        if isinstance(s, ast.Break):
            if scope.loops:
                scope.loops[-1].breaks.extend(pending)
                return []
            return pending
        if isinstance(s, ast.Continue):
            if scope.loops:
                self.connect(pending, scope.loops[-1].head)
                return []
            return pending

        if isinstance(s, ast.Return):
            r = self.node(f"return {code(s.value)}" if s.value else "return")
            self.connect(pending, r)
            self.edge(r, scope.end)
            return []

        if isinstance(s, ast.Raise):
            r = self.node(code(s))
            self.connect(pending, r)
            self.edge(r, scope.end)
            return []

        if isinstance(s, (ast.With, ast.AsyncWith)):
            head = "with " + ", ".join(code(i) for i in s.items)
            return self.block(s.body, self.step(pending, head))

        if isinstance(s, (ast.Try, getattr(ast, "TryStar", ast.Try))):
            t = self.node("try")
            self.connect(pending, t)
            out = self.block(s.orelse, self.block(s.body, [(t, None)]))
            for h in s.handlers:
                label = "except" + (f" {code(h.type)}" if h.type else "") + (f" as {h.name}" if h.name else "")
                hn = self.node(label)
                self.edge(t, hn, "error")
                out += self.block(h.body, [(hn, None)])
            if s.finalbody:
                out = self.block(s.finalbody, self.step(out, "finally"))
            return out

        if isinstance(s, ast.Match):
            d = self.node(f"match {code(s.subject)}", "decision")
            self.connect(pending, d)
            out: Pending = []
            for case in s.cases:
                label = code(case.pattern) + (f" if {code(case.guard)}" if case.guard else "")
                out += self.block(case.body, [(d, label)])
            last = s.cases[-1].pattern if s.cases else None
            if not (isinstance(last, ast.MatchAs) and last.pattern is None and s.cases[-1].guard is None):
                out.append((d, "no match"))
            return out

        return self.step(pending, code(s))

    def loop(self, head: str, s: ast.While | ast.For | ast.AsyncFor, body_in: Pending, exit_: Pending) -> Pending:
        loop = Loop(head=head)
        scope = self._scopes[-1]
        scope.loops.append(loop)
        body_out = self.block(s.body, body_in)
        scope.loops.pop()
        self.connect(body_out, head)
        return self.block(s.orelse, exit_) + loop.breaks

    def function(self, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        prefix = "async def" if isinstance(fn, ast.AsyncFunctionDef) else "def"
        signature = f"{fn.name}({code(fn.args)})"
        saved = self._scopes
        self._scopes = []
        self.subgraph(f"{prefix} {signature}", lambda: self.flow(fn.body, signature))
        self._scopes = saved

    def klass(self, cls: ast.ClassDef) -> None:
        def body() -> None:
            for s in cls.body:
                if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.function(s)
                elif isinstance(s, ast.ClassDef):
                    self.klass(s)

        self.subgraph(f"class {cls.name}", body)


def to_mermaid(source: str) -> str:
    tree = ast.parse(source)
    fb = FlowBuilder()
    top = [s for s in tree.body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    defs = [s for s in tree.body if s not in top]
    # A file that only defines functions/classes shows just their subgraphs.
    if top or not defs:
        fb.flow(tree.body, "Start")
    else:
        fb._scopes.append(Scope(end=""))
        for s in defs:
            fb.stmt(s, [])
        fb._scopes.pop()
    return fb.build()
