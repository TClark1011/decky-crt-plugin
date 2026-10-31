# CRT Filter

A Decky plugin that makes the whole SteamOS Game Mode screen look like a CRT, with per-game automation.

## Language

**CRT Filter**:
The plugin's whole-screen effect: the selected Shader applied by gamescope to the focused app.
_Avoid_: Overlay, CRT mode

**Shader**:
A self-contained ReShade FX file bundled with the plugin and listed in the Shader Registry.
_Avoid_: Effect, preset

**Shader Registry**:
The list of bundled Shaders the plugin offers, defined in `py_modules/crt_filter/shaders.py`.
_Avoid_: Shader list, catalogue

**Default State**:
The persisted on or off state of the CRT Filter, used whenever no Auto-apply Session is running.
_Avoid_: Global setting, manual state

**Running App**:
The game Steam reports as the main running app, or none when the Steam interface is in front.
_Avoid_: Current game, active app

**Auto-apply Game**:
A game whose app id is in the persisted auto-apply list, so the CRT Filter turns on while it is the Running App.
_Avoid_: Whitelisted game, favourite

**Auto-apply Session**:
The period during which an Auto-apply Game is the Running App. Within it, the CRT Filter state is temporary and the Default State is untouched.
_Avoid_: Override, game session

**Gamescope Session**:
Game Mode: Steam running inside the gamescope compositor, which provides the ReShade runtime the plugin needs.
_Avoid_: Big Picture, Steam session
