# textecode

`textecode` is a Python wrapper around the `TextECode.NativeBridge.dll` NativeAOT bridge.

It currently supports Windows `win-x64` only.

It provides:

- `generate()` to convert `*.e` into a text project
- `restore()` to convert a text project back into `*.e`
- `version()` to query the loaded native bridge
- a small CLI exposed as `textecode`

The package expects a Windows `win-x64` native bridge DLL. The recommended build flow is:

1. Download the current release asset `TextECode.NativeBridge-win-x64-v*.zip`
2. Copy the native files into `src/textecode/bin/win-x64/`
3. Build the wheel

You can override the bundled DLL at runtime with the `TEXTECODE_NATIVE_DLL` environment variable.

Local wheel builds intentionally fail if `src/textecode/bin/win-x64/TextECode.NativeBridge.dll` has not been vendored first.

The repository workflow `build-python-package.yml` automates that process.

Example:

```python
from textecode import generate, restore, version

print(version())
restore("demo/full.eproject", "demo/full.e")
generate("demo/full.e", "demo/out/full.eproject")
```
