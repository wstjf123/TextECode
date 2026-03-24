import ctypes
import json
import os
import pathlib
import tempfile


SAMPLES = [
    ("QSJson/QSJson.eproject", False),
    ("@Demo/JsonView/JsonView.eproject", True),
    ("QSSmartScale/QSSmartScale.eproject", True),
]


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
    lib.textecode_version.argtypes = []
    lib.textecode_version.restype = ctypes.c_void_p
    lib.textecode_free.argtypes = [ctypes.c_void_p]
    lib.textecode_free.restype = None
    return lib


def call_or_raise(lib, func_name, *args):
    func = getattr(lib, func_name)
    rc = func(*args)
    if rc != 0:
        message = read_and_free_utf8(lib, lib.textecode_last_error()) or f"{func_name} failed"
        raise AssertionError(message)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_project_files(root):
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() != ".e"
    )


def list_original_expected_files(root):
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    )


def assert_project_fields(original_project, generated_project):
    original = load_json(original_project)
    generated = load_json(generated_project)
    for key in ("Name", "Version", "ProjectType", "SourceSet"):
        if generated.get(key) != original.get(key):
            raise AssertionError(
                f"project field mismatch for {generated_project.name}: {key} -> "
                f"expected {original.get(key)!r}, got {generated.get(key)!r}"
            )
    if not isinstance(generated.get("Dependencies"), list):
        raise AssertionError(f"generated project {generated_project.name} lost dependency information")
    if len(generated["Dependencies"]) < len(original.get("Dependencies", [])):
        raise AssertionError(f"generated project {generated_project.name} lost dependencies")


def assert_snapshot_files(generated_root, original_root):
    original_forms = sorted(path.relative_to(original_root).as_posix() for path in original_root.rglob("*.eform"))
    snapshot_files = sorted(path.relative_to(generated_root).as_posix() for path in generated_root.rglob("*.eform.json"))
    expected = sorted(f"{item}.json" for item in original_forms)
    if snapshot_files != expected:
        raise AssertionError(f"snapshot file mismatch\nexpected={expected}\nactual={snapshot_files}")
    for rel_path in snapshot_files:
        snapshot = load_json(generated_root / rel_path)
        if not snapshot.get("Form"):
            raise AssertionError(f"snapshot {rel_path} is missing Form payload")
        if not snapshot.get("Elements"):
            raise AssertionError(f"snapshot {rel_path} is missing element metadata")


def main():
    import sys

    if len(sys.argv) != 3:
        raise SystemExit("usage: python python_real_world_test.py <path-to-dll> <sample-repo-root>")

    dll_path = pathlib.Path(sys.argv[1]).resolve()
    repo_root = pathlib.Path(sys.argv[2]).resolve()
    if not dll_path.is_file():
        raise FileNotFoundError(dll_path)
    if not repo_root.is_dir():
        raise FileNotFoundError(repo_root)

    lib = load_lib(dll_path)
    version = read_and_free_utf8(lib, lib.textecode_version())
    if not version:
        raise AssertionError("textecode_version returned an empty string")

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_root = pathlib.Path(tmp_dir)
        for relative_project, expects_forms in SAMPLES:
            project_path = repo_root / relative_project
            original_root = project_path.parent
            if not project_path.is_file():
                raise FileNotFoundError(project_path)

            case_root = temp_root / project_path.stem
            restored_e = case_root / "restored.e"
            generated_root = case_root / "generated"
            generated_project = generated_root / project_path.name
            roundtrip_e = case_root / "roundtrip.e"
            generated_root.mkdir(parents=True, exist_ok=True)

            call_or_raise(lib, "textecode_restore", str(project_path).encode("utf-8"), str(restored_e).encode("utf-8"))
            if not restored_e.is_file() or restored_e.stat().st_size == 0:
                raise AssertionError(f"restore produced no .e file for {relative_project}")

            call_or_raise(lib, "textecode_generate", str(restored_e).encode("utf-8"), str(generated_project).encode("utf-8"))
            if not generated_project.is_file():
                raise AssertionError(f"generate produced no project file for {relative_project}")

            call_or_raise(lib, "textecode_restore", str(generated_project).encode("utf-8"), str(roundtrip_e).encode("utf-8"))
            if not roundtrip_e.is_file() or roundtrip_e.stat().st_size == 0:
                raise AssertionError(f"second restore produced no .e file for {relative_project}")

            original_files = list_original_expected_files(original_root)
            generated_files = list_project_files(generated_root)
            missing = [item for item in original_files if item not in generated_files]
            if missing:
                raise AssertionError(f"generated project is missing files for {relative_project}: {missing}")

            assert_project_fields(project_path, generated_project)
            if expects_forms:
                assert_snapshot_files(generated_root, original_root)

            print(f"[ok] {relative_project}")

    print(f"Real-world conversion samples verified with DLL version {version}")


if __name__ == "__main__":
    main()
