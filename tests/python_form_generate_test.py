import ctypes
import json
import os
import pathlib
import tempfile


def read_and_free_utf8(lib, ptr):
    if not ptr:
        return None
    try:
        return ctypes.string_at(ptr).decode("utf-8")
    finally:
        lib.textecode_free(ptr)


def load_lib(dll_path):
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(dll_path.parent))

    lib = ctypes.CDLL(str(dll_path))
    lib.textecode_generate.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.textecode_generate.restype = ctypes.c_int
    lib.textecode_restore.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.textecode_restore.restype = ctypes.c_int
    lib.textecode_last_error.argtypes = []
    lib.textecode_last_error.restype = ctypes.c_void_p
    lib.textecode_free.argtypes = [ctypes.c_void_p]
    lib.textecode_free.restype = None
    return lib


def call_or_raise(lib, func_name, *args):
    rc = getattr(lib, func_name)(*args)
    if rc != 0:
        message = read_and_free_utf8(lib, lib.textecode_last_error()) or f"{func_name} failed"
        raise AssertionError(message)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("usage: python python_form_generate_test.py <path-to-dll> <path-to-sample-e>")

    dll_path = pathlib.Path(sys.argv[1]).resolve()
    sample_path = pathlib.Path(sys.argv[2]).resolve()
    if not dll_path.is_file():
        raise FileNotFoundError(dll_path)
    if not sample_path.is_file():
        raise FileNotFoundError(sample_path)

    lib = load_lib(dll_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = pathlib.Path(tmp_dir)
        generated_project = temp_root / "sample_project" / "sample.eproject"
        restored_e = temp_root / "roundtrip.e"

        call_or_raise(lib, "textecode_generate", str(sample_path).encode("utf-8"), str(generated_project).encode("utf-8"))
        if not generated_project.is_file():
            raise AssertionError("generate did not produce a project file")

        snapshot_files = sorted(generated_project.parent.rglob("*.eform.json"))
        if not snapshot_files:
            raise AssertionError("generate did not produce any form snapshot files")

        for path in snapshot_files:
            if path.stat().st_size == 0:
                raise AssertionError(f"snapshot file is empty: {path.name}")
            snapshot = load_json(path)
            if snapshot.get("FormatVersion") != 2:
                raise AssertionError(f"unexpected snapshot format version in {path.name}")
            if not snapshot.get("Elements"):
                raise AssertionError(f"snapshot file {path.name} has no elements")

        call_or_raise(lib, "textecode_restore", str(generated_project).encode("utf-8"), str(restored_e).encode("utf-8"))
        if not restored_e.is_file() or restored_e.stat().st_size == 0:
            raise AssertionError("restore did not produce a non-empty .e file")

    print("[ok] real form sample generate/restore")


if __name__ == "__main__":
    main()
