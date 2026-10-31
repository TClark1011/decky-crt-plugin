"""Installs the bundled shaders where gamescope's ReShade runtime looks for them."""

import shutil
from pathlib import Path

from .shaders import SHADERS, CrtShader

# Our own folder inside gamescope's Shaders directory, so other plugins' files are never touched.
SHADER_SUBDIR = "DeckyCRT"


def gamescope_shaders_dir(user_home: str) -> Path:
    return Path(user_home) / ".local" / "share" / "gamescope" / "reshade" / "Shaders"


def bundled_shaders_dir(plugin_dir: str) -> Path:
    """Decky's packager copies `defaults/` into the plugin root; a raw checkout keeps it under `defaults/`."""
    packaged = Path(plugin_dir) / "shaders"
    return packaged if packaged.is_dir() else Path(plugin_dir) / "defaults" / "shaders"


def effect_path(shader: CrtShader) -> str:
    """The value gamescope expects: a path relative to its Shaders directory."""
    return f"{SHADER_SUBDIR}/{shader.file}"


def is_own_effect(effect: str) -> bool:
    return effect.startswith(f"{SHADER_SUBDIR}/")


def install_shaders(source_dir: Path, shaders_dir: Path) -> None:
    """Copies every registered shader, replacing any copy whose content differs."""
    target_dir = shaders_dir / SHADER_SUBDIR
    target_dir.mkdir(parents=True, exist_ok=True)
    for shader in SHADERS:
        source = source_dir / shader.file
        target = target_dir / shader.file
        if not target.exists() or target.read_bytes() != source.read_bytes():
            shutil.copyfile(source, target)


def uninstall_shaders(shaders_dir: Path) -> None:
    shutil.rmtree(shaders_dir / SHADER_SUBDIR, ignore_errors=True)
