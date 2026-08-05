from keprix.ui_contract.navigation import navigation_for_role


def test_files_is_visible_in_workspace_navigation() -> None:
    contract = navigation_for_role("user")
    files_item = next((item for item in contract["items"] if item["id"] == "files"), None)

    assert files_item is not None
    assert files_item["href"] == "/files"
    assert files_item["group"] == "workspace"


def test_files_is_present_in_admin_navigation() -> None:
    contract = navigation_for_role("admin")
    assert any(item["id"] == "files" for item in contract["items"])
