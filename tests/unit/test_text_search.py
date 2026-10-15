"""HU-24: normalización de texto para la búsqueda sin acentos."""

from app.core.text_search import ACCENTED, PLAIN, _sqlite_translate, normalize_text


def test_accent_maps_have_same_length():
    assert len(ACCENTED) == len(PLAIN)


def test_normalize_text_removes_accents_and_lowercases():
    assert normalize_text("ÁNGELA Núñez João Çà") == "angela nunez joao ca"


def test_sqlite_translate_keeps_null():
    assert _sqlite_translate(None, ACCENTED, PLAIN) is None
