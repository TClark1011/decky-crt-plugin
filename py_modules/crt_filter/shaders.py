"""Registry of the CRT shaders bundled with the plugin.

To add a shader: put its self-contained .fx file in `defaults/shaders/` and add a
`CrtShader` entry to `SHADERS`. The frontend lists every entry automatically.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrtShader:
    id: str
    name: str
    description: str
    file: str
    technique_index: int = 0


SHADERS: tuple[CrtShader, ...] = (
    CrtShader(
        id="crt-lottes",
        name="CRT-Lottes",
        description="Arcade-monitor scanlines, shadow mask, bloom and slight curvature.",
        file="crt-lottes.fx",
    ),
)

DEFAULT_SHADER_ID = SHADERS[0].id


def get_shader(shader_id: str) -> CrtShader:
    """Returns the shader with `shader_id`, or the default shader if it is unknown."""
    for shader in SHADERS:
        if shader.id == shader_id:
            return shader
    return get_shader(DEFAULT_SHADER_ID)
