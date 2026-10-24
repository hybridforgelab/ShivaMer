import re
import textwrap

import pytest
from fastapi.testclient import TestClient

from converter import escape_label, to_mermaid
from main import app

NODE = re.compile(r'^\s*(n\d+)(?:\[/|\(\[|\{|\[)"(.*)"(?:/\]|\]\)|\}|\])$')
EDGE = re.compile(r'^\s*(n\d+) -->(?:\|"(.*)"\|)? (n\d+)$')


def graph(source: str):
    """Return (labels by id, set of (src label, edge label, dst label))."""
    out = to_mermaid(textwrap.dedent(source))
    labels, edges = {}, set()
    for line in out.splitlines()[1:]:
        if m := NODE.match(line):
            labels[m[1]] = m[2]
        elif m := EDGE.match(line):
            edges.add((m[1], m[2], m[3]))
    return labels, {(labels[a], lab, labels[b]) for a, lab, b in edges}


def test_code_after_if_continues_instead_of_hanging_off_end():
    _, edges = graph(
        """
        age = int(input('Age: '))
        if age >= 18:
            print('A')
        else:
            print('B')
        print('after')
        """
    )
    assert ("A", None, "after") in edges
    assert ("B", None, "after") in edges
    assert ("after", None, "End") in edges
    assert not any(src == "End" for src, _, _ in edges)


def test_if_without_else_falls_through():
    _, edges = graph(
        """
        if x:
            y = 1
        z = 2
        """
    )
    assert ("x?", "No", "z = 2") in edges
    assert ("y = 1", None, "z = 2") in edges


def test_condition_label_is_the_code_verbatim():
    labels, _ = graph("if age >= 18:\n    pass\n")
    assert "age #gt;= 18?" in labels.values()


def test_function_becomes_subgraph_with_loop():
    src = """
    def fizzbuzz(n):
        for i in range(1, n+1):
            if i % 15 == 0:
                print("FizzBuzz")
            elif i % 3 == 0:
                print("Fizz")
            else:
                print(i)
    """
    out = to_mermaid(textwrap.dedent(src))
    assert 'subgraph sg1["def fizzbuzz(n)"]' in out
    _, edges = graph(src)
    assert ("fizzbuzz(n)", None, "for i in range(1, n + 1)") in edges
    assert ("for i in range(1, n + 1)", "next", "i % 15 == 0?") in edges
    assert ("i % 15 == 0?", "No", "i % 3 == 0?") in edges
    for leaf in ("FizzBuzz", "Fizz", "i"):
        assert (leaf, None, "for i in range(1, n + 1)") in edges
    assert ("for i in range(1, n + 1)", "done", "End") in edges


def test_while_loop_returns():
    _, edges = graph(
        """
        def countdown(n):
            while n > 0:
                print(n)
                n -= 1
            return "go!"
        """
    )
    assert ("n #gt; 0?", "Yes", "n") in edges
    assert ("n -= 1", None, "n #gt; 0?") in edges
    assert ("n #gt; 0?", "No", "return 'go!'") in edges
    assert ("return 'go!'", None, "End") in edges


def test_break_and_continue():
    _, edges = graph(
        """
        while True:
            if a:
                break
            if b:
                continue
            step()
        done()
        """
    )
    assert ("a?", "Yes", "done()") in edges
    assert ("b?", "Yes", "True?") in edges
    assert ("step()", None, "True?") in edges


def test_return_stops_the_flow():
    _, edges = graph(
        """
        def f(x):
            if x:
                return 1
            return 2
        """
    )
    assert ("x?", "Yes", "return 1") in edges
    assert ("x?", "No", "return 2") in edges
    assert ("return 1", None, "End") in edges
    assert ("return 1", None, "return 2") not in edges


def test_multiple_targets_are_kept():
    labels, _ = graph("a = b = 1\n")
    assert "a = b = 1" in labels.values()


def test_try_except_finally():
    _, edges = graph(
        """
        try:
            risky()
        except ValueError as e:
            handle(e)
        finally:
            cleanup()
        """
    )
    assert ("try", "error", "except ValueError as e") in edges
    assert ("risky()", None, "finally") in edges
    assert ("handle(e)", None, "finally") in edges


def test_match_without_wildcard_has_no_match_edge():
    _, edges = graph(
        """
        match cmd:
            case "go" | "run":
                go()
        """
    )
    assert ("match cmd", "'go' #124; 'run'", "go()") in edges
    assert ("match cmd", "no match", "End") in edges


def test_ids_are_deterministic_per_request():
    src = "\n".join(f"x{i} = 1" for i in range(40))
    assert to_mermaid(src) == to_mermaid(src)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('He said "hi"', "He said #quot;hi#quot;"),
        ("a | b", "a #124; b"),
        ("<b>x</b> #1", "#lt;b#gt;x#lt;/b#gt; #35;1"),
        ("x" * 100, "x" * 79 + "…"),
        ("a\nb", "a<br/>b"),
    ],
)
def test_escape_label(raw, expected):
    assert escape_label(raw) == expected


client = TestClient(app)


def test_api_convert_and_errors():
    assert client.post("/convert", json={"code": "x = 1"}).status_code == 200
    r = client.post("/convert", json={"code": "if"})
    assert r.status_code == 400 and r.json()["detail"].startswith("SyntaxError")
    assert client.post("/convert", json={"code": "x" * 20_001}).status_code == 422


def test_cors_only_allows_known_origins():
    ok = client.options(
        "/convert",
        headers={"Origin": "https://shivamer.hybridforgelab.com", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers["access-control-allow-origin"] == "https://shivamer.hybridforgelab.com"
    assert "access-control-allow-credentials" not in ok.headers
    bad = client.options(
        "/convert", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"}
    )
    assert "access-control-allow-origin" not in bad.headers
