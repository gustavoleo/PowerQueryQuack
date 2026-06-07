"""Message catalogs for en-US and pt-BR.

Keys are stable identifiers; values are the localized strings. Missing keys fall
back to en-US, then to the key itself, so a missing translation degrades
gracefully instead of raising.
"""

from __future__ import annotations

from pqquack.enums import Language

_EN_US: dict[str, str] = {
    "app.title": "Power Query Quack",
    "app.tagline": "From M to DuckDB, one quack at a time.",
    "upload.heading": "Upload Power Query",
    "settings.language": "Language",
    "settings.target_runtime": "Target runtime",
    "settings.output_mode": "Output mode",
    "results.dependency_graph": "Dependency Graph",
    "results.conversion_report": "Conversion Report",
    "results.generated_sql": "Generated SQL",
    "results.validation_report": "Validation Report",
    "results.compatibility_notes": "Compatibility Notes",
    "results.confidence_score": "Confidence Score",
    "feedback.question": "Was the conversion successful?",
    "feedback.correct": "Correct",
    "feedback.incorrect": "Incorrect",
    "feedback.help_me_fix_it": "Help Me Fix It",
    "validation.pass": "PASS",
    "validation.warning": "WARNING",
    "validation.fail": "FAIL",
}

_PT_BR: dict[str, str] = {
    "app.title": "Power Query Quack",
    "app.tagline": "De M para DuckDB, um quack de cada vez.",
    "upload.heading": "Enviar Power Query",
    "settings.language": "Idioma",
    "settings.target_runtime": "Runtime de destino",
    "settings.output_mode": "Modo de saída",
    "results.dependency_graph": "Grafo de Dependências",
    "results.conversion_report": "Relatório de Conversão",
    "results.generated_sql": "SQL Gerado",
    "results.validation_report": "Relatório de Validação",
    "results.compatibility_notes": "Notas de Compatibilidade",
    "results.confidence_score": "Pontuação de Confiança",
    "feedback.question": "A conversão foi bem-sucedida?",
    "feedback.correct": "Correto",
    "feedback.incorrect": "Incorreto",
    "feedback.help_me_fix_it": "Me Ajude a Corrigir",
    "validation.pass": "APROVADO",
    "validation.warning": "ATENÇÃO",
    "validation.fail": "FALHOU",
}

CATALOGS: dict[Language, dict[str, str]] = {
    Language.EN_US: _EN_US,
    Language.PT_BR: _PT_BR,
}


def t(key: str, language: Language = Language.EN_US) -> str:
    """Translate ``key`` into ``language``, falling back to en-US then the key."""
    catalog = CATALOGS.get(language, _EN_US)
    if key in catalog:
        return catalog[key]
    return _EN_US.get(key, key)
