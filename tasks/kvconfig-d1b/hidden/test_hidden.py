import pytest

from settings import get_path, load


def test_comment_char_inside_quotes_kept():
    cfg = load('color = "#ff0000"\nsep = \';\'')
    assert cfg["main"] == {"color": "#ff0000", "sep": ";"}


def test_quoted_words_stay_strings():
    cfg = load('flag = "yes"\ncount = \'12\'')
    assert cfg["main"] == {"flag": "yes", "count": "12"}


def test_negative_integers():
    cfg = load("offset = -15\nlabel = -x")
    assert cfg["main"] == {"offset": -15, "label": "-x"}


def test_duplicate_key_reports_line():
    with pytest.raises(ValueError, match="line 3"):
        load("[a]\nk = 1\nk = 2")


def test_same_key_in_two_sections_allowed():
    cfg = load("[a]\nk = 1\n[b]\nk = 2")
    assert cfg["a"]["k"] == 1 and cfg["b"]["k"] == 2


def test_empty_section_name_rejected():
    with pytest.raises(ValueError, match="line 2"):
        load("x = 1\n[  ]")


def test_missing_equals_reports_line():
    with pytest.raises(ValueError, match="line 3"):
        load("a = 1\n\njust words")


def test_defaults_are_overridden():
    cfg = load("retries = 5", defaults={"retries": 1, "verbose": False})
    assert cfg["main"] == {"retries": 5, "verbose": False}


def test_keys_and_sections_case_insensitive():
    cfg = load("[Paths]\nHOME = /srv")
    assert cfg == {"main": {}, "paths": {"home": "/srv"}}
    assert get_path(cfg, "PATHS.Home") == "/srv"


def test_lookup_fallbacks():
    cfg = load("a = 1\n; only a comment\n\n")
    assert get_path(cfg, "a") == 1
    assert get_path(cfg, "missing.key", "dflt") == "dflt"
    assert get_path(cfg, "b") is None
