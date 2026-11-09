from snapshots import list_snapshots, load_snapshot, prune, save_snapshot


def test_save_numbers_and_load_latest(tmp_path):
    """Saving two copies of some text should number them 1 and 2, and reading without a number returns the newest."""
    assert save_snapshot(tmp_path, "first") == 1
    assert save_snapshot(tmp_path, "second") == 2
    assert load_snapshot(tmp_path) == "second"


def test_unrelated_files_ignored(tmp_path):
    """Unrelated files in the folder, like notes.txt, should not be listed."""
    (tmp_path / "notes.txt").write_text("x")
    save_snapshot(tmp_path, "a")
    assert list_snapshots(tmp_path) == [1]


def test_prune_keeps_newest(tmp_path):
    """Trimming four saved copies down to the newest 2 should delete numbers 1 and 2 and keep 3 and 4."""
    for text in "abcd":
        save_snapshot(tmp_path, text)
    assert prune(tmp_path, 2) == [1, 2]
    assert list_snapshots(tmp_path) == [3, 4]


def test_load_specific_number(tmp_path):
    """Reading saved copy number 1 should return the text saved first."""
    save_snapshot(tmp_path, "one")
    save_snapshot(tmp_path, "two")
    assert load_snapshot(tmp_path, 1) == "one"
