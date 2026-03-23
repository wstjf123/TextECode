from __future__ import annotations

import json
from pathlib import Path

import pytest

from textecode import TextECode, generate, restore, version
from textecode.errors import NativeBridgeCallError


FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "tests" / "assets" / "full_project"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def list_relative_files(root: Path) -> list[str]:
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")


def assert_contains(path: Path, markers: list[str]) -> None:
    content = read_text(path)
    missing = [marker for marker in markers if marker not in content]
    assert not missing, f"{path.name} is missing markers: {missing}"


def test_version_is_not_empty() -> None:
    assert version()


def test_missing_project_raises_error(tmp_path: Path) -> None:
    with pytest.raises(NativeBridgeCallError):
        restore(tmp_path / "missing.eproject", tmp_path / "out.e")


def test_round_trip_fixture(tmp_path: Path) -> None:
    input_project = FIXTURE_ROOT / "full.eproject"
    restored_e = tmp_path / "full.e"
    regenerated_root = tmp_path / "roundtrip"
    regenerated_project = regenerated_root / "full.eproject"

    with TextECode() as client:
        restored_path = client.restore(input_project, restored_e)
        assert restored_path == restored_e
        assert restored_e.is_file()
        assert restored_e.stat().st_size > 0

        generated_path = generate(restored_e, regenerated_project)
        assert generated_path == regenerated_project
        assert regenerated_project.is_file()

    expected_project = load_json(FIXTURE_ROOT / "full.eproject")
    actual_project = load_json(regenerated_project)
    for key in ("Name", "Version", "ProjectType", "SourceSet"):
        assert actual_project[key] == expected_project[key]
    assert any(
        item.get("Kind") == "ELib" and item.get("FileName") == "krnln"
        for item in actual_project["Dependencies"]
        if isinstance(item, dict)
    )

    assert load_json(regenerated_root / "full.eproject.order") == load_json(
        FIXTURE_ROOT / "full.eproject.order"
    )
    assert list_relative_files(regenerated_root) == list_relative_files(FIXTURE_ROOT)
    assert read_text(regenerated_root / "src" / "@Resource" / "HelpDoc.txt") == read_text(
        FIXTURE_ROOT / "src" / "@Resource" / "HelpDoc.txt"
    )
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
        [".常量 APP_NAME", "NativeBridgeFixture", ".常量 FEATURE_ENABLED", ".常量 RETRY_LIMIT", ".长文本 HelpDoc, 公开"],
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
