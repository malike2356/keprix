from __future__ import annotations

from keprix.__main__ import main


def test_package_entrypoint_prints_version_without_starting_agent(capsys) -> None:
    assert main(["--version"]) == 0

    captured = capsys.readouterr()
    assert captured.out.startswith("Keprix ")


def test_package_entrypoint_version_alias(capsys) -> None:
    assert main(["version"]) == 0

    captured = capsys.readouterr()
    assert captured.out.startswith("Keprix ")
