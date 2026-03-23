import ctypes
import json
import os
import pathlib
import shutil
import sys
import tempfile


def read_and_free_utf8(lib, ptr):
    if not ptr:
        return None
    try:
        return ctypes.string_at(ptr).decode("utf-8")
    finally:
        lib.textecode_free(ptr)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_relative_files(root):
    files = []
    for path in root.rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            files.append(path.relative_to(root).as_posix())
    return sorted(files)


def read_text(path):
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def assert_contains(path, markers):
    content = read_text(path)
    missing = [marker for marker in markers if marker not in content]
    if missing:
        raise AssertionError(f"{path.name} is missing markers: {missing}")


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

    lib.textecode_generate.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.textecode_generate.restype = ctypes.c_int

    fixture_dir = pathlib.Path(__file__).resolve().parent / "assets" / "full_project"
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = pathlib.Path(tmp)
        case_dir = tmp_path / "case"
        shutil.copytree(fixture_dir, case_dir)

        input_project = case_dir / "full.eproject"
        restored_e = tmp_path / "roundtrip.e"
        regenerated_root = tmp_path / "regenerated"
        regenerated_project = regenerated_root / "full.eproject"

        rc = lib.textecode_restore(
            str(input_project).encode("utf-8"),
            str(restored_e).encode("utf-8"),
        )
        if rc != 0:
            raise AssertionError(read_and_free_utf8(lib, lib.textecode_last_error()) or "restore failed")
        if not restored_e.is_file() or restored_e.stat().st_size == 0:
            raise AssertionError("restore did not produce a non-empty .e file")

        rc = lib.textecode_generate(
            str(restored_e).encode("utf-8"),
            str(regenerated_project).encode("utf-8"),
        )
        if rc != 0:
            raise AssertionError(read_and_free_utf8(lib, lib.textecode_last_error()) or "generate failed")
        if not regenerated_project.is_file():
            raise AssertionError("generate did not produce a project file")

        expected_files = list_relative_files(case_dir)
        actual_files = list_relative_files(regenerated_root)
        if actual_files != expected_files:
            raise AssertionError(
                "round-trip file set mismatch\n"
                f"expected: {expected_files}\n"
                f"actual: {actual_files}"
            )

        expected_model = load_json(case_dir / "full.eproject")
        generated_model = load_json(regenerated_project)
        for key in ("Name", "Version", "ProjectType", "SourceSet"):
            if generated_model.get(key) != expected_model.get(key):
                raise AssertionError(
                    f"round-trip project field mismatch for {key}: "
                    f"expected={expected_model.get(key)!r}, actual={generated_model.get(key)!r}"
                )
        if generated_model.get("Name") != "NativeBridgeFixture":
            raise AssertionError("round-trip project name mismatch")
        if not isinstance(generated_model.get("Dependencies"), list):
            raise AssertionError("generated project dependencies are missing")
        if not any(
            item.get("Kind") == "ELib" and item.get("FileName") == "krnln"
            for item in generated_model["Dependencies"]
            if isinstance(item, dict)
        ):
            raise AssertionError("generated project is missing the core krnln dependency")

        expected_order = load_json(case_dir / "full.eproject.order")
        generated_order = load_json(regenerated_root / "full.eproject.order")
        if generated_order != expected_order:
            raise AssertionError(
                "round-trip order model mismatch\n"
                f"expected: {expected_order}\n"
                f"actual: {generated_order}"
            )

        if read_text(regenerated_root / "src" / "@Resource" / "HelpDoc.txt") != read_text(
            case_dir / "src" / "@Resource" / "HelpDoc.txt"
        ):
            raise AssertionError("long text resource content mismatch")

        assert_contains(
            regenerated_root / "src" / "@Global.ecode",
            [".全局变量 GlobalCount, 整数型, 公开"],
        )
        assert_contains(
            regenerated_root / "src" / "@Struct.ecode",
            [".数据类型 Point, 公开", ".成员 X, 整数型", ".成员 Y, 整数型"],
        )
        assert_contains(
            regenerated_root / "src" / "@Constant.ecode",
            [
                '.常量 APP_NAME, "NativeBridgeFixture", 公开',
                ".常量 FEATURE_ENABLED, 真, 公开",
                ".常量 RETRY_LIMIT, 3, 公开",
                ".长文本 HelpDoc, 公开",
            ],
        )
        assert_contains(
            regenerated_root / "src" / "AppMain.ecode",
            [
                ".程序集 AppMain, , 公开",
                ".程序集变量 InternalCounter, 整数型",
                ".子程序 RunDemo, , 公开",
                ".参数 userName, 文本型",
                ".局部变量 currentPoint, Point",
                "Helper.LogMessage",
                "HelpDoc",
                ".如果 (isReady)",
                ".否则",
                ".如果结束",
                ".判断开始",
                ".判断 (counter == 2)",
                ".默认",
                ".判断结束",
            ],
        )
        assert_contains(
            regenerated_root / "src" / "Features" / "Helper.ecode",
            [
                ".程序集 Helper, , 公开",
                ".子程序 LogMessage, , 公开",
                ".参数 message, 文本型",
                "GlobalCount = GlobalCount + lineCount",
                ".如果真 (FEATURE_ENABLED)",
                ".如果真结束",
            ],
        )

    print(f"Loaded {dll_path.name}")
    print(f"Version: {version}")
    print("Restore failure path and error propagation verified")
    print("Full restore/generate round trip fixture verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
