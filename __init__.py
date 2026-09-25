"""GPU speech-to-text for Hermes' local Whisper: CUDA DLL restore on Windows, local MLX server on macOS."""
import sys


def register(ctx):
    if sys.platform == "win32":
        from . import windows as platform
    elif sys.platform == "darwin":
        from . import macos as platform
    else:
        return
    platform.register(ctx)
