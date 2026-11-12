import pytest

from router import MethodNotAllowed, Router
from segments import split_path


def make():
    router = Router()
    router.add("/users/<int:id>", "user_detail")
    router.add("/users/me", "user_me")
    router.add("/files/<path:rest>", "file_get", methods=("GET", "HEAD"))
    router.add("/posts", "post_create", methods=("POST",))
    return router


def test_split_ignores_empty_and_trailing():
    """Splitting "/a//b/" should give ["a", "b"] and "/" should give an empty list."""
    assert split_path("/a//b/") == ["a", "b"]
    assert split_path("/") == []


def test_percent_escapes_decoded():
    """Splitting "/hello%20world/x" should give ["hello world", "x"]."""
    assert split_path("/hello%20world/x") == ["hello world", "x"]


def test_int_param_converted():
    """Matching GET "/users/42" should return ("user_detail", {"id": 42}) with 42 as an int."""
    assert make().match("GET", "/users/42") == ("user_detail", {"id": 42})


def test_static_beats_parameter():
    """Matching GET "/users/me" should pick user_me even though "/users/<int:id>" also exists."""
    assert make().match("GET", "/users/me")[0] == "user_me"


def test_path_param_takes_rest():
    """Matching GET "/files/a/b/c.txt" should give the rest "a/b/c.txt" as one parameter."""
    assert make().match("GET", "/files/a/b/c.txt") == ("file_get", {"rest": "a/b/c.txt"})


def test_missing_and_wrong_method():
    """An unknown path such as "/nope" raises LookupError and GET on the POST-only "/posts" raises MethodNotAllowed."""
    with pytest.raises(LookupError):
        make().match("GET", "/nope")
    with pytest.raises(MethodNotAllowed):
        make().match("GET", "/posts")
