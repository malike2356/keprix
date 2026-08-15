from agent.dap.adapters import adapter_command, adapter_status


def test_adapter_commands_are_structured_argv() -> None:
    assert adapter_command("python")[1:] == ["-m", "debugpy.adapter"]
    assert adapter_command("c++") == ["lldb-dap"]
    assert all(isinstance(item["command"], list) for item in adapter_status().values())
