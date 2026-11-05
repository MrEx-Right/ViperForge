"""
ViperForge — Chain Graph Helpers
Qt-free helpers for the block graph shared by the engine, validator and macros.

Nodes are indices into a session list; edges are (src, dst, port_type) tuples
where port_type is "success" or "failure". Like the canvas, each node uses at
most one outgoing edge per port — extra edges on the same port are ignored.
"""

from typing import Iterable, List, Optional, Sequence, Tuple

Edge = Tuple[int, int, str]

SUCCESS = "success"
FAILURE = "failure"

_EXIT = -1   # virtual end-of-chain node used for post-dominator analysis


def has_branches(edges: Optional[Iterable[Edge]]) -> bool:
    return any(pt == FAILURE for _, _, pt in edges or ())


def outgoing(count: int, edges: Iterable[Edge]) -> Tuple[List[Optional[int]], List[Optional[int]]]:
    """Returns (success_target, failure_target) per node, None where unconnected."""
    succ: List[Optional[int]] = [None] * count
    fail: List[Optional[int]] = [None] * count
    for src, dst, port in edges:
        if not (0 <= src < count and 0 <= dst < count):
            continue
        targets = fail if port == FAILURE else succ
        if targets[src] is None:
            targets[src] = dst
    return succ, fail


def roots(count: int, edges: Iterable[Edge]) -> List[int]:
    """Nodes with no incoming edge, in list order — each starts its own flow."""
    succ, fail = outgoing(count, edges)
    has_in = {t for t in succ + fail if t is not None}
    return [i for i in range(count) if i not in has_in]


def chain_order(count: int, edges: Iterable[Edge]) -> List[int]:
    """Depth-first order from each root (success before failure), then leftovers."""
    succ, fail = outgoing(count, edges)
    ordered: List[int] = []
    seen = set()

    def walk(n: Optional[int]) -> None:
        if n is None or n in seen:
            return
        seen.add(n)
        ordered.append(n)
        walk(succ[n])
        walk(fail[n])

    for r in roots(count, edges):
        walk(r)
    ordered.extend(i for i in range(count) if i not in seen)
    return ordered


def find_cycle(count: int, edges: Iterable[Edge]) -> Optional[List[int]]:
    """Returns one cycle as [a, b, ..., a] if the graph has any, else None."""
    succ, fail = outgoing(count, edges)
    WHITE, GREY, BLACK = 0, 1, 2
    color = [WHITE] * count
    stack: List[int] = []

    def visit(n: int) -> Optional[List[int]]:
        color[n] = GREY
        stack.append(n)
        for nxt in (succ[n], fail[n]):
            if nxt is None:
                continue
            if color[nxt] == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if color[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[n] = BLACK
        return None

    for n in range(count):
        if color[n] == WHITE:
            found = visit(n)
            if found:
                return found
    return None


def immediate_post_dominators(count: int, edges: Iterable[Edge]) -> List[Optional[int]]:
    """
    For each node, the first node every path from it must pass through
    (None = end of chain). This is where the success and failure paths of
    a branch join back together. The graph must be acyclic.
    """
    edges = list(edges)
    succ, fail = outgoing(count, edges)

    # Post-order guarantees every successor is handled before its predecessor.
    order: List[int] = []
    seen = set()

    def visit(n: int) -> None:
        seen.add(n)
        for nxt in (succ[n], fail[n]):
            if nxt is not None and nxt not in seen:
                visit(nxt)
        order.append(n)

    for n in range(count):
        if n not in seen:
            visit(n)

    pdom = {_EXIT: frozenset([_EXIT])}
    for n in order:
        nexts = [succ[n] if succ[n] is not None else _EXIT]
        if fail[n] is not None:
            nexts.append(fail[n])
        pdom[n] = frozenset.intersection(*(pdom[x] for x in nexts)) | {n}

    # Post-dominators of a node form a chain; the nearest one has the largest set.
    result: List[Optional[int]] = []
    for n in range(count):
        nearest = max(pdom[n] - {n}, key=lambda d: len(pdom[d]))
        result.append(None if nearest == _EXIT else nearest)
    return result


def remap_edges(edges: Iterable[Edge], new_index: Sequence[Optional[int]]) -> List[Edge]:
    """Re-point edges after nodes were reordered/dropped (new_index[old] -> new or None)."""
    out: List[Edge] = []
    for src, dst, port in edges:
        if 0 <= src < len(new_index) and 0 <= dst < len(new_index):
            ns, nd = new_index[src], new_index[dst]
            if ns is not None and nd is not None:
                out.append((ns, nd, port))
    return out
