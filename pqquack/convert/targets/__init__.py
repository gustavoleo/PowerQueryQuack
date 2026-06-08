"""Per-runtime SQL dialect handling (goal sections 3, 10-12).

``duckdb`` (default), ``gizmosql``, and ``motherduck`` differ in file access,
extensions, remote execution, and native readers. The :class:`Target` describes
those differences so the converter can choose native readers and attach
compatibility markers (goal sections 11-12).
"""

from __future__ import annotations

from dataclasses import dataclass

from pqquack.enums import TargetRuntime


@dataclass(frozen=True)
class Target:
    runtime: TargetRuntime
    # Whether local filesystem paths are reliably available at execution time.
    local_files_reliable: bool
    # A marker to attach when a generated feature may not hold on this runtime.
    local_only_marker: str | None


_TARGETS: dict[TargetRuntime, Target] = {
    TargetRuntime.DUCKDB: Target(
        runtime=TargetRuntime.DUCKDB,
        local_files_reliable=True,
        local_only_marker=None,
    ),
    TargetRuntime.GIZMOSQL: Target(
        runtime=TargetRuntime.GIZMOSQL,
        local_files_reliable=False,
        local_only_marker="Local DuckDB only — GizmoSQL compatibility not guaranteed.",
    ),
    TargetRuntime.MOTHERDUCK: Target(
        runtime=TargetRuntime.MOTHERDUCK,
        local_files_reliable=False,
        local_only_marker="Local DuckDB only — MotherDuck compatibility not guaranteed.",
    ),
}


def get_target(runtime: TargetRuntime) -> Target:
    return _TARGETS[runtime]
