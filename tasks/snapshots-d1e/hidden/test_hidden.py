import pytest

from snapshots import list_snapshots, load_snapshot, prune, save_snapshot


def test_negative_number_counts_back(tmp_path):
    for text in ["x", "y", "z"]:
        save_snapshot(tmp_path, text)
    assert load_snapshot(tmp_path, -1) == "z"
    assert load_snapshot(tmp_path, -3) == "x"


def test_prune_zero_removes_all(tmp_path):
    save_snapshot(tmp_path, "a")
    save_snapshot(tmp_path, "b")
    assert prune(tmp_path, 0) == [1, 2]
    assert list_snapshots(tmp_path) == []


def test_prune_more_than_exist(tmp_path):
    save_snapshot(tmp_path, "a")
    assert prune(tmp_path, 5) == []
    assert list_snapshots(tmp_path) == [1]


def test_prune_negative_rejected(tmp_path):
    with pytest.raises(ValueError):
        prune(tmp_path, -1)


def test_numbering_continues_after_prune(tmp_path):
    for text in "abc":
        save_snapshot(tmp_path, text)
    prune(tmp_path, 1)
    assert save_snapshot(tmp_path, "d") == 4
    assert list_snapshots(tmp_path) == [3, 4]


def test_load_from_empty_folder(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_snapshot(tmp_path)


def test_unicode_round_trip(tmp_path):
    save_snapshot(tmp_path, "héllo — ✓\nline two")
    assert load_snapshot(tmp_path) == "héllo — ✓\nline two"


def test_lookalike_names_ignored(tmp_path):
    for name in ["snap-abcd.txt", "snap-0007.txt.tmp", "snap-0003.log", "xsnap-0001.txt"]:
        (tmp_path / name).write_text("junk")
    (tmp_path / "snap-0010.txt").write_text("ten")
    assert list_snapshots(tmp_path) == [10]
    assert save_snapshot(tmp_path, "next") == 11
