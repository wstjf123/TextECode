class TextECodeError(RuntimeError):
    pass


class NativeBridgeLoadError(TextECodeError):
    pass


class NativeBridgeCallError(TextECodeError):
    pass
