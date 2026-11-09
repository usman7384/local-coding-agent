from settings import get_path, load


def test_plain_pair_goes_to_main():
    """A line 'name = demo' outside any section should be stored under 'main'."""
    assert load("name = demo") == {"main": {"name": "demo"}}


def test_section_collects_following_pairs():
    """Pairs after a '[server]' header should be stored in the 'server' section."""
    cfg = load("[server]\nhost = example.org\nport = 8080")
    assert cfg["server"] == {"host": "example.org", "port": 8080}


def test_comments_are_ignored():
    """Text after '#' or ';' is a comment and should not become part of the value."""
    cfg = load("mode = fast  # tuned\nlevel = 3 ; max")
    assert cfg["main"] == {"mode": "fast", "level": 3}


def test_boolean_words():
    """Words like yes/off should be read as the booleans True/False."""
    cfg = load("debug = yes\ncache = off")
    assert cfg["main"] == {"debug": True, "cache": False}


def test_dotted_lookup():
    """Looking up 'db.user' should return the 'user' key of section 'db'."""
    cfg = load("[db]\nuser = admin")
    assert get_path(cfg, "db.user") == "admin"
