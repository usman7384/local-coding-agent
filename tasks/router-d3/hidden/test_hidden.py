import pytest

from convert import format_value, parse_spec, take, to_int, to_str
from router import MethodNotAllowed, Router, build, match_route, pick, step
from segments import decode, encode, is_hex, join_path, split_path


def test_is_hex():
    assert is_hex("2F")
    assert is_hex("a0")
    assert not is_hex("g0")
    assert not is_hex("2")
    assert not is_hex("200")


def test_decode_cases():
    assert decode("a%20b") == "a b"
    assert decode("%41%42") == "AB"
    assert decode("100%") == "100%"
    assert decode("%zz") == "%zz"
    assert decode("%4") == "%4"
    assert decode("a%2fb") == "a/b"


def test_split_keeps_encoded_slash_in_segment():
    assert split_path("a%2Fb/c") == ["a/b", "c"]
    assert split_path("") == []
    assert split_path("x") == ["x"]
    assert split_path("//x//y//") == ["x", "y"]


def test_encode_and_join():
    assert encode("a b/c%") == "a%20b%2Fc%25"
    assert encode("plain") == "plain"
    assert join_path(["a", "b"]) == "/a/b"
    assert join_path([]) == "/"


def test_to_int_and_to_str():
    assert to_int("007") == 7
    assert to_int("0") == 0
    for bad in ("", "-1", "1.5", "x"):
        with pytest.raises(ValueError):
            to_int(bad)
    assert to_str("abc") == "abc"
    with pytest.raises(ValueError):
        to_str("")


def test_parse_spec():
    assert parse_spec("users") is None
    assert parse_spec("<int:id>") == ("int", "id")
    assert parse_spec("<path:rest>") == ("path", "rest")
    assert parse_spec("<name>") == ("str", "name")
    with pytest.raises(ValueError):
        parse_spec("<float:x>")


def test_take():
    assert take("int", ["5", "x"]) == (5, 1)
    assert take("str", ["a", "b"]) == ("a", 1)
    assert take("path", ["a", "b", "c"]) == ("a/b/c", 3)
    with pytest.raises(ValueError):
        take("int", [])
    with pytest.raises(ValueError):
        take("path", [])
    with pytest.raises(ValueError):
        take("int", ["x"])


def test_format_value():
    assert format_value("int", 7) == "7"
    assert format_value("str", "a b") == "a%20b"
    assert format_value("path", "a b/c") == "a%20b/c"


def test_step_and_match_route():
    assert step("a", ["a", "b"]) == ({}, 1, 1)
    assert step(("int", "n"), ["4", "b"]) == ({"n": 4}, 1, 0)
    with pytest.raises(ValueError):
        step("a", [])
    with pytest.raises(ValueError):
        step("a", ["b"])
    assert match_route(["a", ("int", "n")], ["a", "3"]) == ({"n": 3}, [1, 0])
    assert match_route(["a"], ["a", "b"]) is None
    assert match_route(["a", "b"], ["a"]) is None
    assert match_route([("int", "n")], ["x"]) is None
    assert match_route([], []) == ({}, [])


def test_pick_and_build():
    found = [([0, 1], "low", {}, ("GET",)), ([1, 0], "high", {"a": 1}, ("GET",))]
    assert pick(found, "GET") == ("high", {"a": 1})
    assert pick(found, "POST") is None
    tie = [([1], "first", {}, ("GET",)), ([1], "second", {}, ("GET",))]
    assert pick(tie, "GET")[0] == "first"
    specs = ["users", ("int", "id"), "my files"]
    assert build(specs, {"id": 3}) == "/users/3/my%20files"


def test_router_matching_rules():
    router = Router()
    router.add("/a/<str:x>/c", "param_mid")
    router.add("/a/b/<str:y>", "static_mid")
    router.add("/a/<path:rest>", "greedy")
    router.add("/a", "a_put", methods=["PUT"])
    assert router.match("GET", "/a/b/c") == ("static_mid", {"y": "c"})
    assert router.match("GET", "/a/z/c/") == ("param_mid", {"x": "z"})
    assert router.match("GET", "/a/z/d/e") == ("greedy", {"rest": "z/d/e"})
    assert router.match("PUT", "/a") == ("a_put", {})
    with pytest.raises(MethodNotAllowed):
        router.match("GET", "/a")
    with pytest.raises(LookupError):
        router.match("GET", "/")
    assert not issubclass(MethodNotAllowed, LookupError)


def test_method_fallthrough_and_decoding():
    router = Router()
    router.add("/item/<int:id>", "get_item")
    router.add("/item/<int:id>", "set_item", methods=("POST",))
    router.add("/name/<str:n>", "greet")
    assert router.match("POST", "/item/2") == ("set_item", {"id": 2})
    assert router.match("GET", "/item/2") == ("get_item", {"id": 2})
    assert router.match("GET", "/name/a%20b") == ("greet", {"n": "a b"})
    with pytest.raises(LookupError):
        router.match("GET", "/item/x")
    with pytest.raises(MethodNotAllowed):
        router.match("DELETE", "/item/2")


def test_url_for():
    router = Router()
    router.add("/users/<int:id>/files/<path:rest>", "f")
    router.add("/home", "home")
    assert router.url_for("home") == "/home"
    assert router.url_for("f", id=5, rest="a b/c") == "/users/5/files/a%20b/c"
    path = router.url_for("f", id=1, rest="x/y")
    assert router.match("GET", path) == ("f", {"id": 1, "rest": "x/y"})
    with pytest.raises(LookupError):
        router.url_for("missing")
    with pytest.raises(KeyError):
        router.url_for("f", id=1)
