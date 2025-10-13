from __future__ import annotations

import ast
import itertools
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="ShivaMer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class ConvertReq(BaseModel):
    code: str = Field(min_length=1)

class ConvertResp(BaseModel):
    mermaid: str

_id_counter = itertools.count()
def nid(prefix="n") -> str:
    return f"{prefix}{next(_id_counter)}"

class MermaidBuilder:
    def __init__(self):
        self.lines = ["flowchart TD"]
        self.edges = []
    def add_node(self, node_id: str, label: str, shape: str = "rect"):
        label = (label or "").replace('"', '\\"')
        if shape == "diamond":
            self.lines.append(f'    {node_id}{{"{label}"}}')
        elif shape == "round":
            self.lines.append(f'    {node_id}("{label}")')
        else:
            self.lines.append(f'    {node_id}["{label}"]')
    def add_edge(self, a: str, b: str, text: str | None = None):
        if text:
            text = text.replace('"', '\\"')
            self.edges.append(f'    {a} -->|{text}| {b}')
        else:
            self.edges.append(f'    {a} --> {b}')
    def build(self) -> str:
        return "\n".join(self.lines + self.edges)

def summarize_expr(node) -> str:
    """Return a readable label for an AST node."""
    try:
        return ast.unparse(node)
    except Exception:
        return getattr(node, "id", None) or getattr(node, "attr", None) or node.__class__.__name__

def _is_input_call(node):
    """Detect input('...') or int(input('...')) and return the prompt text if present."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "input":
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "int" and node.args:
        inner = node.args[0]
        if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "input":
            if inner.args and isinstance(inner.args[0], ast.Constant) and isinstance(inner.args[0].value, str):
                return inner.args[0].value
    return None

def _pretty_call_label(node):
    """For print('...') show only the text; otherwise fall back to unparse."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print" and node.args:
        arg0 = node.args[0]
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            return arg0.value
    return summarize_expr(node)

def flow_from_ast(tree: ast.AST) -> str:
    mb = MermaidBuilder()
    mb.lines = ["flowchart TD"]
    letters = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    def lid():
        try:
            return next(letters)
        except StopIteration:
            return nid("n")

    def add_input_node(text: str) -> str:
        node_id = lid()
        safe = text.replace('"', '\\"')
        mb.lines.append(f'    {node_id}[/"{safe}"/]')
        return node_id

    def add_node(label: str, shape: str = "rect") -> str:
        node_id = lid()
        if shape in ("start", "end"):
            mb.add_node(node_id, label, "round")
        elif shape == "decision":
            mb.add_node(node_id, label, "diamond")
        else:
            mb.add_node(node_id, label)
        return node_id

    start = add_node("Start", "start")
    # single global End
    global_end = add_node("End", "end")

    def build_block(stmts, prev_id, connect_first=True):
        first_created = None
        last = prev_id
        for s in stmts:
            nonlocal_prev = last if connect_first or first_created is not None else None
            f, l = handle_stmt(s, nonlocal_prev, suppress_connect=(not connect_first and first_created is None))
            if first_created is None:
                first_created = f
            last = l
        if first_created is None:
            return (prev_id, prev_id)
        return (first_created, last)

    def handle_stmt(stmt, prev_id, suppress_connect=False):
        if isinstance(stmt, ast.Assign):
            prompt = _is_input_call(stmt.value)
            if prompt is not None:
                n = add_input_node(prompt)
                if not suppress_connect and prev_id:
                    mb.add_edge(prev_id, n)
                return (n, n)
            lab = f"{summarize_expr(stmt.targets[0])} = {summarize_expr(stmt.value)}"
            n = add_node(lab)
            if not suppress_connect and prev_id:
                mb.add_edge(prev_id, n)
            return (n, n)

        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            lab = _pretty_call_label(stmt.value)
            n = add_node(lab)
            if not suppress_connect and prev_id:
                mb.add_edge(prev_id, n)
            return (n, n)

        if isinstance(stmt, ast.If):
            cond = summarize_expr(stmt.test)
            # Capitalize simple variable name on the left: idade >= 18 -> Idade >= 18
            if isinstance(stmt.test, ast.Compare) and isinstance(stmt.test.left, ast.Name):
                left = stmt.test.left.id
                cond_pretty = left[:1].upper() + left[1:] + " " + cond[len(left):]
            else:
                cond_pretty = cond
            d = add_node(f"{cond_pretty}?", "decision")
            if not suppress_connect and prev_id:
                mb.add_edge(prev_id, d)

            # branches
            y_first, y_last = build_block(stmt.body, d, connect_first=False)
            n_first, n_last = build_block(stmt.orelse or [], d, connect_first=False)

            # link branches to the global End
            mb.add_edge(d, y_first if y_first != d else global_end, "Yes")
            mb.add_edge(d, n_first if n_first != d else global_end, "No")
            if y_last != d:
                mb.add_edge(y_last, global_end)
            if n_last != d:
                mb.add_edge(n_last, global_end)

            # return global_end as last to avoid extra edge later
            return (d, global_end)

        if isinstance(stmt, ast.Return):
            r = add_node(f"return {summarize_expr(getattr(stmt, 'value', None) or '')}")
            if not suppress_connect and prev_id:
                mb.add_edge(prev_id, r)
            mb.add_edge(r, global_end)
            return (r, global_end)

        # generic fallback
        lab = summarize_expr(stmt)[:80]
        n = add_node(lab)
        if not suppress_connect and prev_id:
            mb.add_edge(prev_id, n)
        return (n, n)

    if isinstance(tree, ast.Module):
        first, last = build_block(tree.body, start, connect_first=True)
        if last != global_end:
            mb.add_edge(last, global_end)
        return mb.build()
    else:
        raise ValueError("Invalid code.")

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/")
def root():
    return {"message": "ShivaMer API. Use /convert (POST) or /docs."}

@app.post("/convert", response_model=ConvertResp)
def convert(req: ConvertReq):
    try:
        tree = ast.parse(req.code)
    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"SyntaxError: {e.msg} (line {e.lineno})")
    return ConvertResp(mermaid=flow_from_ast(tree))
