from __future__ import annotations

import ctypes
import os
import sys
from contextlib import ExitStack
from importlib import resources
from pathlib import Path
from typing import Final

from .errors import NativeBridgeCallError, NativeBridgeLoadError

_DLL_ENV_VAR: Final[str] = "TEXTECODE_NATIVE_DLL"
_DLL_NAME: Final[str] = "TextECode.NativeBridge.dll"


class NativeBridge:
    def __init__(self, dll_path: str | Path | None = None) -> None:
        self._resource_stack = ExitStack()
        self._dll_directory_handle = None
        self._dll_path = self._resolve_dll_path(dll_path)
        self._library = self._load_library(self._dll_path)
        self._bind_signatures()

    @property
    def dll_path(self) -> Path:
        return self._dll_path

    def close(self) -> None:
        self._resource_stack.close()
        if self._dll_directory_handle is not None:
            self._dll_directory_handle.close()
            self._dll_directory_handle = None

    def __enter__(self) -> NativeBridge:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def version(self) -> str:
        return self._read_and_free_utf8(self._library.textecode_version())

    def generate(self, input_e_file: str | Path, output_project_file: str | Path) -> Path:
        result = self._library.textecode_generate(
            self._encode_path(input_e_file),
            self._encode_path(output_project_file),
        )
        self._raise_on_error(result, "generate")
        return Path(output_project_file)

    def restore(self, input_project_file: str | Path, output_e_file: str | Path) -> Path:
        result = self._library.textecode_restore(
            self._encode_path(input_project_file),
            self._encode_path(output_e_file),
        )
        self._raise_on_error(result, "restore")
        return Path(output_e_file)

    def _bind_signatures(self) -> None:
        self._library.textecode_generate.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._library.textecode_generate.restype = ctypes.c_int

        self._library.textecode_restore.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._library.textecode_restore.restype = ctypes.c_int

        self._library.textecode_last_error.argtypes = []
        self._library.textecode_last_error.restype = ctypes.c_void_p

        self._library.textecode_version.argtypes = []
        self._library.textecode_version.restype = ctypes.c_void_p

        self._library.textecode_free.argtypes = [ctypes.c_void_p]
        self._library.textecode_free.restype = None

    def _resolve_dll_path(self, dll_path: str | Path | None) -> Path:
        candidates: list[Path] = []
        if dll_path is not None:
            candidates.append(Path(dll_path))
        env_path = os.environ.get(_DLL_ENV_VAR)
        if env_path:
            candidates.append(Path(env_path))

        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()

        package_file = resources.files("textecode").joinpath("bin", "win-x64", _DLL_NAME)
        package_path = self._resource_stack.enter_context(resources.as_file(package_file))
        candidates.append(Path(package_path))

        if Path(package_path).is_file():
            return Path(package_path).resolve()

        formatted = "\n".join(f"- {candidate}" for candidate in candidates)
        raise NativeBridgeLoadError(
            "Unable to locate TextECode native bridge DLL. Checked:\n"
            f"{formatted}\n"
            f"Set {_DLL_ENV_VAR} or bundle {_DLL_NAME} into the package."
        )

    def _load_library(self, dll_path: Path) -> ctypes.CDLL:
        if sys.platform != "win32":
            raise NativeBridgeLoadError(
                "textecode currently supports Windows only and requires a win-x64 TextECode.NativeBridge.dll"
            )
        if hasattr(os, "add_dll_directory"):
            self._dll_directory_handle = os.add_dll_directory(str(dll_path.parent))
        try:
            return ctypes.CDLL(str(dll_path))
        except OSError as exc:
            self.close()
            raise NativeBridgeLoadError(f"Failed to load native bridge DLL: {dll_path}") from exc

    def _raise_on_error(self, result: int, operation: str) -> None:
        if result == 0:
            return
        message = self._read_and_free_utf8(self._library.textecode_last_error())
        if not message:
            message = f"{operation} failed with exit code {result}"
        raise NativeBridgeCallError(message)

    def _read_and_free_utf8(self, ptr: int) -> str:
        if not ptr:
            return ""
        try:
            return ctypes.string_at(ptr).decode("utf-8")
        finally:
            self._library.textecode_free(ptr)

    @staticmethod
    def _encode_path(path: str | Path) -> bytes:
        return str(Path(path)).encode("utf-8")
