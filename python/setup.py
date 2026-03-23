from setuptools import Distribution, setup
from setuptools.command.build_py import build_py as _build_py
from pathlib import Path

try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except ImportError:  # pragma: no cover
    _bdist_wheel = None


class BinaryDistribution(Distribution):
    def has_ext_modules(self) -> bool:
        return True


class build_py(_build_py):
    def run(self) -> None:
        dll_path = Path(__file__).resolve().parent / "src" / "textecode" / "bin" / "win-x64" / "TextECode.NativeBridge.dll"
        if not dll_path.is_file():
            raise FileNotFoundError(
                "Missing vendored native bridge DLL. Run python/tools/vendor_native.py before building the wheel."
            )
        super().run()


if _bdist_wheel is not None:
    class bdist_wheel(_bdist_wheel):
        def finalize_options(self) -> None:
            super().finalize_options()
            self.root_is_pure = False

        def get_tag(self):
            _, _, plat = super().get_tag()
            return "py3", "none", plat


    setup(
        distclass=BinaryDistribution,
        cmdclass={"bdist_wheel": bdist_wheel, "build_py": build_py},
    )
else:  # pragma: no cover
    setup(distclass=BinaryDistribution, cmdclass={"build_py": build_py})
