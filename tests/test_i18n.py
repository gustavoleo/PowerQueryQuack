"""Both languages must cover the same keys, and detection must fall back to en-US."""

from pqquack.enums import Language
from pqquack.i18n import detect_language, t
from pqquack.i18n.catalog import CATALOGS


def test_catalogs_have_identical_keys() -> None:
    en = set(CATALOGS[Language.EN_US])
    pt = set(CATALOGS[Language.PT_BR])
    assert en == pt, f"key mismatch: {en ^ pt}"


def test_translation_selects_language() -> None:
    assert t("feedback.correct", Language.EN_US) == "Correct"
    assert t("feedback.correct", Language.PT_BR) == "Correto"


def test_missing_key_falls_back_to_key() -> None:
    assert t("does.not.exist", Language.PT_BR) == "does.not.exist"


def test_detect_prefers_override() -> None:
    assert detect_language("hello world", override=Language.PT_BR) is Language.PT_BR


def test_detect_portuguese_signal() -> None:
    assert detect_language("converter esta coluna de código") is Language.PT_BR


def test_detect_defaults_to_en_us() -> None:
    assert detect_language("convert this column") is Language.EN_US
    assert detect_language(None) is Language.EN_US
