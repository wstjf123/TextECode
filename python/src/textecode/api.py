from __future__ import annotations

from pathlib import Path
from threading import Lock

from ._native import NativeBridge

_default_lock = Lock()
_default_client: TextECode | None = None


class TextECode:
    def __init__(self, dll_path: str | Path | None = None) -> None:
        self._bridge = NativeBridge(dll_path)

    @property
    def dll_path(self) -> Path:
        return self._bridge.dll_path

    def close(self) -> None:
        self._bridge.close()

    def __enter__(self) -> TextECode:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def version(self) -> str:
        return self._bridge.version()

    def generate(self, input_e_file: str | Path, output_project_file: str | Path) -> Path:
        return self._bridge.generate(input_e_file, output_project_file)

    def restore(self, input_project_file: str | Path, output_e_file: str | Path) -> Path:
        return self._bridge.restore(input_project_file, output_e_file)


def get_default_bridge() -> TextECode:
    global _default_client
    if _default_client is not None:
        return _default_client
    with _default_lock:
        if _default_client is None:
            _default_client = TextECode()
        return _default_client


def version() -> str:
    return get_default_bridge().version()


def generate(input_e_file: str | Path, output_project_file: str | Path) -> Path:
    return get_default_bridge().generate(input_e_file, output_project_file)


def restore(input_project_file: str | Path, output_e_file: str | Path) -> Path:
    return get_default_bridge().restore(input_project_file, output_e_file)
