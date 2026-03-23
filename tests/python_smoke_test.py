import ctypes
import os
import pathlib
import sys


def read_and_free_utf8(lib, ptr):
    if not ptr:
        return None
    try:
        return ctypes.string_at(ptr).decode("utf-8")
    finally:
        lib.textecode_free(ptr)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python python_smoke_test.py <path-to-dll>")

    dll_path = pathlib.Path(sys.argv[1]).resolve()
    if not dll_path.is_file():
        raise FileNotFoundError(dll_path)

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_path.parent))

    lib = ctypes.CDLL(str(dll_path))

    lib.textecode_version.argtypes = []
    lib.textecode_version.restype = ctypes.c_void_p

    lib.textecode_last_error.argtypes = []
    lib.textecode_last_error.restype = ctypes.c_void_p

    lib.textecode_free.argtypes = [ctypes.c_void_p]
    lib.textecode_free.restype = None

    lib.textecode_restore.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.textecode_restore.restype = ctypes.c_int

    version = read_and_free_utf8(lib, lib.textecode_version())
    if not version:
        raise AssertionError("textecode_version returned an empty string")

    missing_project = str(dll_path.parent / "missing.eproject").encode("utf-8")
    out_file = str(dll_path.parent / "out.e").encode("utf-8")
    rc = lib.textecode_restore(missing_project, out_file)
    if rc == 0:
        raise AssertionError("textecode_restore unexpectedly succeeded for a missing project file")

    error_text = read_and_free_utf8(lib, lib.textecode_last_error())
    if not error_text:
        raise AssertionError("textecode_last_error returned nothing after a failure")

    print(f"Loaded {dll_path.name}")
    print(f"Version: {version}")
    print("Restore failure path and error propagation verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
