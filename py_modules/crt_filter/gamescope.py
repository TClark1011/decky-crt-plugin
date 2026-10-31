"""Controls gamescope's built-in ReShade effect through X11 root window properties.

gamescope watches two properties on the root window of its Xwayland server:
`GAMESCOPE_RESHADE_EFFECT` (a path relative to `~/.local/share/gamescope/reshade/Shaders`)
and `GAMESCOPE_RESHADE_TECHNIQUE_IDX`. Setting the effect compiles and applies it;
deleting it turns the effect off.

libX11 is used through ctypes so no extra package is needed. `xprop` is the fallback
when libX11 cannot be loaded.
"""

import ctypes
import ctypes.util
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

EFFECT_ATOM = "GAMESCOPE_RESHADE_EFFECT"
TECHNIQUE_ATOM = "GAMESCOPE_RESHADE_TECHNIQUE_IDX"

_X11_SOCKET_DIR = Path("/tmp/.X11-unix")
_STEAM_PROCESS_NAMES = ("steam", "steamwebhelper")


class GamescopeError(Exception):
    pass


@dataclass(frozen=True)
class XTarget:
    display: str
    xauthority: str | None = None


def _read_environ(pid_dir: Path) -> dict[str, str]:
    try:
        raw = (pid_dir / "environ").read_bytes()
    except OSError:
        return {}
    env: dict[str, str] = {}
    for entry in raw.split(b"\0"):
        key, sep, value = entry.partition(b"=")
        if sep:
            env[key.decode(errors="replace")] = value.decode(errors="replace")
    return env


def _read_comm(pid_dir: Path) -> str:
    try:
        return (pid_dir / "comm").read_text().strip()
    except OSError:
        return ""


def candidate_targets() -> list[XTarget]:
    """Lists X displays that may belong to gamescope, most likely first.

    Processes started by gamescope (Steam included) carry `GAMESCOPE_WAYLAND_DISPLAY`
    and the matching `DISPLAY`. Every local X socket is appended as a fallback.
    """
    steam: list[XTarget] = []
    others: list[XTarget] = []
    try:
        pid_dirs = [p for p in Path("/proc").iterdir() if p.name.isdigit()]
    except OSError:
        pid_dirs = []
    for pid_dir in pid_dirs:
        env = _read_environ(pid_dir)
        display = env.get("DISPLAY")
        if not display or "GAMESCOPE_WAYLAND_DISPLAY" not in env:
            continue
        target = XTarget(display, env.get("XAUTHORITY"))
        (steam if _read_comm(pid_dir) in _STEAM_PROCESS_NAMES else others).append(target)

    sockets: list[XTarget] = []
    try:
        for socket in sorted(_X11_SOCKET_DIR.iterdir()):
            if socket.name.startswith("X") and socket.name[1:].isdigit():
                sockets.append(XTarget(f":{socket.name[1:]}"))
    except OSError:
        pass

    ordered: list[XTarget] = []
    seen: set[str] = set()
    for target in steam + others + sockets:
        if target.display not in seen:
            seen.add(target.display)
            ordered.append(target)
    return ordered


class _XlibBackend:
    _PROP_MODE_REPLACE = 0
    _XA_CARDINAL = 6
    _ANY_PROPERTY_TYPE = 0

    def __init__(self) -> None:
        path = ctypes.util.find_library("X11") or "libX11.so.6"
        lib = ctypes.CDLL(path)
        c_void_p, c_ulong, c_int, c_long = ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long

        lib.XOpenDisplay.argtypes = [ctypes.c_char_p]
        lib.XOpenDisplay.restype = c_void_p
        lib.XCloseDisplay.argtypes = [c_void_p]
        lib.XDefaultRootWindow.argtypes = [c_void_p]
        lib.XDefaultRootWindow.restype = c_ulong
        lib.XInternAtom.argtypes = [c_void_p, ctypes.c_char_p, c_int]
        lib.XInternAtom.restype = c_ulong
        lib.XChangeProperty.argtypes = [c_void_p, c_ulong, c_ulong, c_ulong, c_int, c_int, c_void_p, c_int]
        lib.XDeleteProperty.argtypes = [c_void_p, c_ulong, c_ulong]
        lib.XGetWindowProperty.argtypes = [
            c_void_p, c_ulong, c_ulong, c_long, c_long, c_int, c_ulong,
            ctypes.POINTER(c_ulong), ctypes.POINTER(c_int), ctypes.POINTER(c_ulong),
            ctypes.POINTER(c_ulong), ctypes.POINTER(ctypes.POINTER(ctypes.c_ubyte)),
        ]
        lib.XFree.argtypes = [c_void_p]
        lib.XSync.argtypes = [c_void_p, c_int]

        # Xlib's default error handler exits the process, which would kill the plugin.
        handler_type = ctypes.CFUNCTYPE(c_int, c_void_p, c_void_p)
        self._error_handler = handler_type(lambda _display, _event: 0)
        lib.XSetErrorHandler.argtypes = [handler_type]
        lib.XSetErrorHandler(self._error_handler)

        self._lib = lib

    def _open(self, target: XTarget) -> int:
        previous = os.environ.get("XAUTHORITY")
        if target.xauthority:
            os.environ["XAUTHORITY"] = target.xauthority
        try:
            display = self._lib.XOpenDisplay(target.display.encode())
        finally:
            if previous is None:
                os.environ.pop("XAUTHORITY", None)
            else:
                os.environ["XAUTHORITY"] = previous
        if not display:
            raise GamescopeError(f"Cannot open X display {target.display}")
        return display

    def probe(self, target: XTarget) -> bool:
        try:
            display = self._open(target)
        except GamescopeError:
            return False
        try:
            return self._lib.XInternAtom(display, EFFECT_ATOM.encode(), 1) != 0
        finally:
            self._lib.XCloseDisplay(display)

    def set_effect(self, target: XTarget, effect_path: str, technique_index: int) -> None:
        display = self._open(target)
        try:
            lib = self._lib
            root = lib.XDefaultRootWindow(display)
            technique = (ctypes.c_long * 1)(technique_index)
            lib.XChangeProperty(
                display, root, lib.XInternAtom(display, TECHNIQUE_ATOM.encode(), 0),
                self._XA_CARDINAL, 32, self._PROP_MODE_REPLACE, technique, 1,
            )
            data = effect_path.encode()
            lib.XChangeProperty(
                display, root, lib.XInternAtom(display, EFFECT_ATOM.encode(), 0),
                lib.XInternAtom(display, b"UTF8_STRING", 0), 8, self._PROP_MODE_REPLACE, data, len(data),
            )
            lib.XSync(display, 0)
        finally:
            self._lib.XCloseDisplay(display)

    def get_effect(self, target: XTarget) -> str:
        display = self._open(target)
        try:
            lib = self._lib
            actual_type = ctypes.c_ulong()
            actual_format = ctypes.c_int()
            item_count = ctypes.c_ulong()
            bytes_after = ctypes.c_ulong()
            value = ctypes.POINTER(ctypes.c_ubyte)()
            status = lib.XGetWindowProperty(
                display, lib.XDefaultRootWindow(display), lib.XInternAtom(display, EFFECT_ATOM.encode(), 0),
                0, 4096, 0, self._ANY_PROPERTY_TYPE, ctypes.byref(actual_type), ctypes.byref(actual_format),
                ctypes.byref(item_count), ctypes.byref(bytes_after), ctypes.byref(value),
            )
            if status != 0 or not value:
                return ""
            try:
                if actual_format.value != 8:
                    return ""
                return ctypes.string_at(value, item_count.value).decode(errors="replace")
            finally:
                lib.XFree(value)
        finally:
            self._lib.XCloseDisplay(display)

    def clear_effect(self, target: XTarget) -> None:
        display = self._open(target)
        try:
            lib = self._lib
            lib.XDeleteProperty(display, lib.XDefaultRootWindow(display), lib.XInternAtom(display, EFFECT_ATOM.encode(), 0))
            lib.XSync(display, 0)
        finally:
            self._lib.XCloseDisplay(display)


class _XpropBackend:
    def _run(self, target: XTarget, *args: str) -> str:
        env = dict(os.environ)
        env["DISPLAY"] = target.display
        if target.xauthority:
            env["XAUTHORITY"] = target.xauthority
        # Decky's bundled libraries break system binaries.
        env["LD_LIBRARY_PATH"] = ""
        try:
            result = subprocess.run(["xprop", "-root", *args], capture_output=True, text=True, env=env, timeout=5)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise GamescopeError(f"xprop failed: {error}") from error
        if result.returncode != 0:
            raise GamescopeError(f"xprop failed: {result.stderr.strip()}")
        return result.stdout

    def probe(self, target: XTarget) -> bool:
        try:
            return "GAMESCOPE_" in self._run(target)
        except GamescopeError:
            return False

    def set_effect(self, target: XTarget, effect_path: str, technique_index: int) -> None:
        self._run(target, "-f", TECHNIQUE_ATOM, "32c", "-set", TECHNIQUE_ATOM, str(technique_index))
        self._run(target, "-f", EFFECT_ATOM, "8u", "-set", EFFECT_ATOM, effect_path)

    def get_effect(self, target: XTarget) -> str:
        match = re.search(r'=\s*"(.*)"', self._run(target, EFFECT_ATOM))
        return match.group(1) if match else ""

    def clear_effect(self, target: XTarget) -> None:
        self._run(target, "-remove", EFFECT_ATOM)


class Gamescope:
    """Finds gamescope's X display and sets or clears its ReShade effect.

    Every method blocks; call them from a worker thread.
    """

    def __init__(self) -> None:
        try:
            self._backend: _XlibBackend | _XpropBackend = _XlibBackend()
        except (OSError, AttributeError):
            self._backend = _XpropBackend()
        self._target: XTarget | None = None

    def _find_target(self) -> XTarget:
        if self._target and self._backend.probe(self._target):
            return self._target
        self._target = None
        for target in candidate_targets():
            if self._backend.probe(target):
                self._target = target
                return target
        raise GamescopeError("No gamescope session with ReShade support was found")

    def is_available(self) -> bool:
        try:
            self._find_target()
            return True
        except GamescopeError:
            return False

    def set_effect(self, effect_path: str, technique_index: int) -> None:
        self._backend.set_effect(self._find_target(), effect_path, technique_index)

    def get_effect(self) -> str:
        return self._backend.get_effect(self._find_target())

    def clear_effect(self) -> None:
        self._backend.clear_effect(self._find_target())
