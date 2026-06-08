"""Assemble parsed queries into a clean, CTE-based SQL pipeline (goal sections 9, 13).

Reconstructs the transformation pipeline rather than transpiling line-by-line:
each query becomes a chain of named CTEs (one per supported transformation step),
and the dependency graph stitches queries together so the final output query is a
single ``SELECT``. Never emits temporary tables or procedural logic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pqquack.convert.args import parse_call
from pqquack.convert.mexpr import quote_ident
from pqquack.convert.rules.tables import RULES, StepContext
from pqquack.convert.source import detect_source
from pqquack.convert.targets import Target, get_target
from pqquack.enums import TargetRuntime
from pqquack.graph import AnalysisResult, analyze
from pqquack.knowledge import KnowledgeStore
from pqquack.parser import Query

# Patterns that must never appear in generated SQL (goal sections 3, 9, 27).
_FORBIDDEN = [
    r"\bcreate\s+(global\s+|local\s+)?temp(orary)?\s+table\b",
    r"\binto\s+#",
    r"\btable\s+variable\b",
    r"\bdeclare\s+@",
    r"\bcursor\b",
    r"#temp",
]


@dataclass
class QueryPlan:
    name: str
    ctes: list[tuple[str, str]]
    result: str
    columns: list[str] | None = None
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)


@dataclass
class ConversionResult:
    sql: str
    target_runtime: TargetRuntime
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unsupported: list[str] = field(default_factory=list)
    markers: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return not self.unsupported and "<source" not in self.sql

    @property
    def forbidden_constructs(self) -> list[str]:
        """Any forbidden (temp-table / procedural) constructs found — must be empty."""
        lowered = self.sql.lower()
        return [p for p in _FORBIDDEN if re.search(p, lowered)]

    @property
    def temp_table_free(self) -> bool:
        return not self.forbidden_constructs


def _transformation_steps(query: Query):
    """Yield (step, call) for steps that are supported/known Table.* transforms."""
    steps = []
    for step in query.steps:
        if step.name == "$output":
            continue
        call = parse_call(step.text)
        if call is None:
            continue  # source/navigation/bare-ref step -> folded into the base
        if call.func in RULES or call.func.startswith("Table."):
            steps.append((step, call))
    return steps


def build_query_plan(
    query: Query, target: Target, query_names: set[str]
) -> QueryPlan:
    """Build the CTE chain and final relation name for a single query."""
    source = detect_source(query, target, query_names)
    notes = list(source.notes)
    warnings = list(source.warnings)
    markers = list(source.markers)
    unsupported: list[str] = []

    qid = quote_ident(query.name)
    ctes: list[tuple[str, str]] = []
    current = source.relation
    columns: list[str] | None = None

    trans = _transformation_steps(query)
    for idx, (step, call) in enumerate(trans):
        is_last = idx == len(trans) - 1
        cte_name = qid if is_last else quote_ident(f"{query.name}__{step.name}")
        ctx = StepContext(input_relation=current, columns=columns, query_names=query_names)

        handler = RULES.get(call.func)
        if handler is None:
            reason = f"{call.func}: not yet supported (deterministic)"
            unsupported.append(f"{query.name}.{step.name}: {reason}")
            proj = "*" if columns is None else ", ".join(quote_ident(c) for c in columns)
            body = f"SELECT {proj} FROM {current} /* UNSUPPORTED: {reason} */"
        else:
            result = handler(call, ctx)
            if result.unsupported:
                unsupported.append(f"{query.name}.{step.name}: {result.unsupported}")
                proj = "*" if columns is None else ", ".join(quote_ident(c) for c in columns)
                body = f"SELECT {proj} FROM {current} /* UNSUPPORTED: {result.unsupported} */"
            else:
                body = result.sql or ""
                columns = result.columns
                notes.extend(result.notes)
                warnings.extend(result.warnings)
        ctes.append((cte_name, body))
        current = cte_name

    if not trans:
        # Pure source/reference query: expose it under its own name.
        ctes.append((qid, f"SELECT * FROM {source.relation}"))

    notes.extend(markers)  # surface compatibility markers alongside notes
    return QueryPlan(
        name=query.name,
        ctes=ctes,
        result=qid,
        columns=columns,
        notes=notes,
        warnings=warnings,
        unsupported=unsupported,
    )


def _assemble(ctes: list[tuple[str, str]], final_relation: str, columns: list[str] | None) -> str:
    proj = "*" if columns is None else ", ".join(quote_ident(c) for c in columns)
    final = f"SELECT {proj} FROM {final_relation}"
    if not ctes:
        return final + ";"
    blocks = ",\n".join(f"{name} AS (\n    {body}\n)" for name, body in ctes)
    return f"WITH {blocks}\n{final};"


def convert_query(
    query: Query,
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB,
    store: KnowledgeStore | None = None,
) -> ConversionResult:
    """Convert a single parsed query to SQL."""
    target = get_target(target_runtime)
    plan = build_query_plan(query, target, {query.name})
    sql = _assemble(plan.ctes, plan.result, plan.columns)
    return ConversionResult(
        sql=sql,
        target_runtime=target_runtime,
        notes=plan.notes,
        warnings=plan.warnings,
        unsupported=plan.unsupported,
    )


def _reachable(output: str, edges: dict[str, set[str]]) -> set[str]:
    seen: set[str] = set()
    stack = [output]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(edges.get(node, set()))
    return seen


def _topo_order(nodes: set[str], edges: dict[str, set[str]]) -> list[str]:
    """Dependencies first (a query appears after the queries it references)."""
    order: list[str] = []
    visited: set[str] = set()

    def visit(n: str) -> None:
        if n in visited:
            return
        visited.add(n)
        for dep in sorted(edges.get(n, set())):
            if dep in nodes:
                visit(dep)
        order.append(n)

    for n in sorted(nodes):
        visit(n)
    return order


def convert_analysis(
    analysis: AnalysisResult,
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB,
    store: KnowledgeStore | None = None,
    output: str | None = None,
) -> ConversionResult:
    """Convert a whole analyzed document into one stitched SQL pipeline."""
    target = get_target(target_runtime)
    graph = analysis.graph

    if analysis.has_cycle:
        chains = "; ".join(c.chain for c in analysis.cycles)
        return ConversionResult(
            sql=f"-- Conversion blocked: circular reference(s): {chains}",
            target_runtime=target_runtime,
            warnings=["Circular references must be resolved before SQL generation."],
            unsupported=[f"circular: {chains}"],
        )

    outputs = graph.outputs()
    chosen = output or (outputs[0] if outputs else None)
    if chosen is None:
        return ConversionResult(
            sql="-- No output query found.",
            target_runtime=target_runtime,
            warnings=["No final output query could be identified."],
        )

    needed = _reachable(chosen, graph.edges)
    order = _topo_order(needed, graph.edges)

    all_ctes: list[tuple[str, str]] = []
    notes: list[str] = []
    warnings: list[str] = []
    unsupported: list[str] = []
    final_columns: list[str] | None = None

    for name in order:
        plan = build_query_plan(graph.queries[name], target, graph.names)
        all_ctes.extend(plan.ctes)
        notes.extend(plan.notes)
        warnings.extend(plan.warnings)
        unsupported.extend(plan.unsupported)
        if name == chosen:
            final_columns = plan.columns

    sql = _assemble(all_ctes, quote_ident(chosen), final_columns)
    return ConversionResult(
        sql=sql,
        target_runtime=target_runtime,
        notes=notes,
        warnings=warnings,
        unsupported=unsupported,
    )


def convert_text(
    text: str,
    target_runtime: TargetRuntime = TargetRuntime.DUCKDB,
    store: KnowledgeStore | None = None,
    output: str | None = None,
) -> ConversionResult:
    """Convenience: analyze a Power Query document and convert it end to end."""
    analysis = analyze(text, store=store)
    if len(analysis.queries) == 1 and not analysis.has_cycle:
        return convert_query(analysis.queries[0], target_runtime, store)
    return convert_analysis(analysis, target_runtime, store, output)
