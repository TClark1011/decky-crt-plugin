# Use gamescope's built-in ReShade instead of ShaderGlass

The original brief named ShaderGlass, with ReShade, as the way to put a CRT shader over the screen. ShaderGlass is a Windows DirectX 11 overlay that runs on Linux only under Wine/Proton, in clone mode, using PipeWire capture. In a gamescope session it would just be another app window, and it cannot sit over the Steam UI and every game. gamescope (since 2023) has a ReShade FX runtime built in, which shades the focused app's layer and can be switched at runtime through root window X properties. That covers the Steam UI and games on any gamescope session with nothing to install, so we use it and drop ShaderGlass.

## Considered Options

- **gamescope's ReShade runtime (chosen)**: works on every gamescope session (Deck, CachyOS, Bazzite) and needs no installs. It supports only a subset of ReShade FX, cannot change uniforms at runtime, and leaves overlay layers (the Quick Access Menu, notifications) unfiltered.
- **ShaderGlass under Wine/Proton**: matches the brief literally, but cannot overlay Game Mode, and it needs a Wine prefix plus a PipeWire ScreenCast portal that gamescope sessions do not reliably provide.
- **vkBasalt or ReShade injected per game**: shades games only, never the Steam UI, and needs per-game launch options.

## Consequences

- Shaders must be ported to self-contained ReShade FX, so RetroArch slang presets (which ShaderGlass would have used) cannot be used directly.
- Per-user shader settings have to be done by generating `.fx` wrappers with `#define` overrides, not by setting uniforms.
