from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path

import pytest

from textecode import TextECode
from textecode import api as api_module
from textecode import cli as cli_module
from textecode import _native as native_module
from textecode.errors import NativeBridgeLoadError


class FakeHandle:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeBridge:
    def __init__(self, dll_path: str | Path | None = None) -> None:
        self.dll_path = Path(dll_path or "C:/fake/TextECode.NativeBridge.dll")
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def version(self) -> str:
        return "1.2.3"

    def generate(self, input_e_file: str | Path, output_project_file: str | Path) -> Path:
        return Path(output_project_file)

    def restore(self, input_project_file: str | Path, output_e_file: str | Path) -> Path:
        return Path(output_e_file)


def make_bridge() -> native_module.NativeBridge:
    bridge = native_module.NativeBridge.__new__(native_module.NativeBridge)
    bridge._resource_stack = ExitStack()
    bridge._dll_directory_handle = None
    bridge._library = None
    return bridge


def test_text_ecode_close_and_context_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "NativeBridge", FakeBridge)

    with TextECode("C:/explicit/TextECode.NativeBridge.dll") as client:
        assert client.dll_path == Path("C:/explicit/TextECode.NativeBridge.dll")
        assert client.version() == "1.2.3"
        bridge = client._bridge

    assert bridge.closed is True


def test_get_default_bridge_reuses_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "NativeBridge", FakeBridge)
    monkeypatch.setattr(api_module, "_default_client", None)

    first = api_module.get_default_bridge()
    second = api_module.get_default_bridge()

    assert first is second
    assert first.version() == "1.2.3"
    first.close()
    monkeypatch.setattr(api_module, "_default_client", None)


def test_native_bridge_resolves_explicit_dll_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    explicit = tmp_path / "explicit.dll"
    env_dll = tmp_path / "env.dll"
    explicit.write_bytes(b"dll")
    env_dll.write_bytes(b"dll")
    monkeypatch.setenv(native_module._DLL_ENV_VAR, str(env_dll))

    bridge = make_bridge()
    resolved = bridge._resolve_dll_path(explicit)

    assert resolved == explicit.resolve()
    bridge.close()


def test_native_bridge_resolves_env_dll_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_dll = tmp_path / "env.dll"
    env_dll.write_bytes(b"dll")
    monkeypatch.setenv(native_module._DLL_ENV_VAR, str(env_dll))

    bridge = make_bridge()
    resolved = bridge._resolve_dll_path(None)

    assert resolved == env_dll.resolve()
    bridge.close()


def test_native_bridge_missing_dll_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    missing_package_root = tmp_path / "missing"
    monkeypatch.delenv(native_module._DLL_ENV_VAR, raising=False)
    monkeypatch.setattr(native_module.resources, "files", lambda _: missing_package_root)

    bridge = make_bridge()
    with pytest.raises(NativeBridgeLoadError, match="Unable to locate TextECode native bridge DLL"):
        bridge._resolve_dll_path(None)
    bridge.close()


def test_native_bridge_non_windows_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bridge = make_bridge()
    monkeypatch.setattr(native_module.sys, "platform", "linux")

    with pytest.raises(NativeBridgeLoadError, match="supports Windows only"):
        bridge._load_library(tmp_path / "TextECode.NativeBridge.dll")


def test_native_bridge_load_failure_closes_handle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bridge = make_bridge()
    handle = FakeHandle()

    monkeypatch.setattr(native_module.sys, "platform", "win32")
    monkeypatch.setattr(native_module.os, "add_dll_directory", lambda _: handle)
    monkeypatch.setattr(native_module.ctypes, "CDLL", lambda _: (_ for _ in ()).throw(OSError("bad dll")))

    with pytest.raises(NativeBridgeLoadError, match="Failed to load native bridge DLL"):
        bridge._load_library(tmp_path / "TextECode.NativeBridge.dll")

    assert handle.closed is True
    assert bridge._dll_directory_handle is None


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (["textecode", "version", "--dll", "C:/native.dll"], "1.2.3"),
        (["textecode", "generate", "in.e", "out.eproject"], "out.eproject"),
        (["textecode", "restore", "in.eproject", "out.e"], "out.e"),
    ],
)
def test_cli_main_routes_commands(
    argv: list[str],
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, tuple[str, ...], str | None]] = []

    class FakeClient:
        def __init__(self, dll_path: str | None = None) -> None:
            self._dll_path = dll_path

        def version(self) -> str:
            calls.append(("version", (), self._dll_path))
            return "1.2.3"

        def generate(self, input_e_file: str, output_project_file: str) -> Path:
            calls.append(("generate", (input_e_file, output_project_file), self._dll_path))
            return Path(output_project_file)

        def restore(self, input_project_file: str, output_e_file: str) -> Path:
            calls.append(("restore", (input_project_file, output_e_file), self._dll_path))
            return Path(output_e_file)

    monkeypatch.setattr(cli_module, "TextECode", FakeClient)
    monkeypatch.setattr("sys.argv", argv)

    assert cli_module.main() == 0
    assert capsys.readouterr().out.strip() == expected
    assert calls


def test_cli_parser_requires_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["textecode"])
    with pytest.raises(SystemExit) as exc_info:
        cli_module.main()
    assert exc_info.value.code == 2


def test_native_bridge_close_clears_directory_handle() -> None:
    bridge = make_bridge()
    handle = FakeHandle()
    bridge._dll_directory_handle = handle

    bridge.close()

    assert handle.closed is True
    assert bridge._dll_directory_handle is None
