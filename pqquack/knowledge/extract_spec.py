"""Extract a structured knowledge cache from ``PowerQueryLanguageSpecification.pdf``.

Dev-time only. Produces ``m_spec.json`` consumed at runtime by
:class:`pqquack.knowledge.store.KnowledgeStore`. Per goal section 4, if the asset
cannot be opened or parsed this returns a structured fallback (``available:
False``) instead of raising, so a broken/missing PDF never blocks the product.

The extraction is deliberately conservative: it catalogs the M standard library
(function names per library), M enumerations and their members, type tokens, and
classifies libraries into *transformation* vs *access/connector* (source
acquisition) to support the connector-isolation rule (goal section 8). It does
not attempt to capture full per-function semantics; that is layered in over time.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

# Libraries whose functions acquire data from an external source. Their functions
# are connector / source-acquisition logic and must be isolated from business
# transformation logic (goal section 8), never used as transformation guidance.
ACCESS_LIBRARIES: frozenset[str] = frozenset(
    {
        "Sql", "Odbc", "OleDb", "Web", "OData", "Json", "Csv", "Xml", "Excel",
        "Access", "File", "Folder", "SharePoint", "Salesforce", "Oracle",
        "MySQL", "PostgreSQL", "Snowflake", "GoogleBigQuery", "AzureStorage",
        "SapBusinessWarehouse", "SapHana", "Teradata", "Db2", "Informix",
        "Sybase", "Hdfs", "AnalysisServices", "Cube", "DB2", "Vertica",
        "Impala", "Spark", "Databricks", "Kusto", "Exchange", "ActiveDirectory",
    }
)

# Known M enumerations (members appear as ``Enum.Member``); used to capture their
# values (e.g. JoinKind.Inner) which drive join-kind and ordering semantics.
ENUMERATION_LIBRARIES: frozenset[str] = frozenset(
    {
        "JoinKind", "JoinAlgorithm", "Order", "Occurrence", "RoundingMode",
        "MissingField", "ExtraValues", "GroupKind", "TextEncoding", "Day",
        "RelativePosition", "QuoteStyle", "JoinSide", "Precision", "TraceLevel",
        "ByteOrder", "Compression", "CsvStyle", "WebMethod",
    }
)

# Type tokens we report presence/frequency for (drives the type-mapping layer).
TYPE_TOKENS: tuple[str, ...] = (
    "text", "number", "Int64.Type", "Int32.Type", "Int16.Type", "Int8.Type",
    "date", "datetime", "datetimezone", "time", "duration", "logical", "binary",
    "any", "Currency.Type", "Percentage.Type",
)

_FUNCTION_RE = re.compile(r"\b([A-Z][A-Za-z0-9]+)\.([A-Z][A-Za-z0-9]+)\b")


def _read_pdf_text(pdf_path: Path) -> str | None:
    """Return the concatenated text of the PDF, or ``None`` on any failure."""
    try:
        import pypdf  # imported lazily so a missing/broken dep degrades gracefully
    except Exception:
        return None
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None


def _fallback(reason: str) -> dict:
    return {
        "source": "PowerQueryLanguageSpecification.pdf",
        "available": False,
        "reason": reason,
        "libraries": {},
        "functions": {},
        "enumerations": {},
        "access_libraries": [],
        "type_tokens": {},
        "function_count": 0,
    }


def extract(pdf_path: str | Path) -> dict:
    """Extract the M-spec knowledge cache from the PDF.

    Returns a dict ready to serialize to ``m_spec.json``. Always returns a usable
    structure; ``available`` is ``False`` when the PDF could not be read.
    """
    path = Path(pdf_path)
    if not path.exists():
        return _fallback(f"asset not found: {path}")

    text = _read_pdf_text(path)
    if not text:
        return _fallback("could not extract text (missing/broken PDF reader or unreadable PDF)")

    pairs = _FUNCTION_RE.findall(text)

    functions: dict[str, set[str]] = defaultdict(set)
    enumerations: dict[str, set[str]] = defaultdict(set)
    for lib, member in pairs:
        qualified = f"{lib}.{member}"
        if lib in ENUMERATION_LIBRARIES:
            # Enumeration members are clean identifiers; drop the ``.Type`` token
            # and footnote-numbered artifacts (e.g. ``RightAnti5``).
            if member.isalpha() and member != "Type":
                enumerations[lib].add(qualified)
        else:
            # Skip the ``Lib.Type`` tokens (handled as type tokens, not functions).
            if member != "Type":
                functions[lib].add(qualified)

    lib_counts = Counter({lib: len(fns) for lib, fns in functions.items()})

    access_present = sorted(lib for lib in functions if lib in ACCESS_LIBRARIES)
    type_tokens = {tok: text.count(tok) for tok in TYPE_TOKENS if text.count(tok)}

    return {
        "source": "PowerQueryLanguageSpecification.pdf",
        "available": True,
        "note": (
            "Function lists are extracted from PDF text and may contain minor "
            "concatenation artifacts. Authoritative for library coverage and "
            "access/transformation classification, not per-function semantics."
        ),
        "libraries": dict(lib_counts.most_common()),
        "functions": {lib: sorted(fns) for lib, fns in sorted(functions.items())},
        "enumerations": {lib: sorted(vals) for lib, vals in sorted(enumerations.items())},
        "access_libraries": access_present,
        "type_tokens": type_tokens,
        "function_count": sum(len(fns) for fns in functions.values()),
    }
