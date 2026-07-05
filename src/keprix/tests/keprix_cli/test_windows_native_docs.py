from pathlib import Path


def test_windows_native_install_path_docs_match_installer() -> None:
    doc = Path("website/docs/user-guide/windows-native.md").read_text()
    install = Path("scripts/install.ps1").read_text()

    assert "%LOCALAPPDATA%\\keprix\\keprix\\venv\\Scripts" in doc
    assert "Get-Command keprix        # should print C:\\Users\\<you>\\AppData\\Local\\keprix\\keprix\\venv\\Scripts\\keprix.exe" in doc
    assert '$keprixBin = "$InstallDir\\venv\\Scripts"' in install
