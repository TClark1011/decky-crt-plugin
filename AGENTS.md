# CRT Filter (Decky plugin)

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin that applies a CRT shader to the whole SteamOS Game Mode screen, covering both the Steam interface and games, with a per-game auto-apply toggle. It targets every machine running a gamescope session (Steam Deck, SteamOS-like desktops such as CachyOS or Bazzite), not just the Deck. First version, built but not yet tested on a device. Domain terms are defined in [GLOSSARY.md](./GLOSSARY.md).

## Tech stack

- _Frontend language:_ TypeScript 5 with React (provided by the Steam client at runtime)
- _Frontend libraries:_ `@decky/ui` (Steam UI components and globals), `@decky/api` (backend calls and events)
- _Frontend bundler:_ Rollup through `@decky/rollup`
- _Backend:_ Python 3 `main.py` run by Decky Loader, package code in `py_modules/crt_filter/`
- _Package manager:_ pnpm 9 (Decky's plugin store CI expects v9)
- _Shader runtime:_ gamescope's built-in ReShade FX runtime, driven through X11 root window properties
- _Bundled shader:_ CRT-Lottes, ported to self-contained ReShade FX
- _Packaging:_ `scripts/package.sh`, which builds a zip in the Decky CLI layout
- _CI/CD:_ GitHub Actions. Every push to `master` publishes a GitHub Release with the zip and `install.sh`
- _Store release:_ Decky plugin store submission (planned)

When you add, remove or replace a technology, or build a planned one, update this list in the same change.

## Layout

- `src/`: frontend. `index.tsx` is the Quick Access panel, `backend.ts` holds the typed backend calls, `runningApp.ts` tracks the focused game.
- `main.py`: the Decky `Plugin` class, a thin layer over `py_modules/crt_filter/`.
- `py_modules/crt_filter/`: backend logic. `controller.py` decides the filter state, `gamescope.py` talks to gamescope, `installer.py` places shader files, `shaders.py` is the Shader Registry, `settings.py` persists settings.
- `defaults/shaders/`: bundled `.fx` shaders. The Decky packager copies `defaults/` into the plugin root, so they ship as `shaders/`.
- `decky.pyi`: type stub for the `decky` module Decky injects at runtime.
- `scripts/`: `package.sh` builds `out/decky-crt-filter.zip`, `out/install.sh` and `out/decky-crt-filter-installer.tar.gz` (both files, with `install.sh` still executable, since release asset downloads drop file modes). `install.sh` is the end-user installer; its `__GITHUB_REPOSITORY__` placeholder is filled in by `package.sh` from `GITHUB_REPOSITORY`.
- `.github/workflows/release.yml`: on every push to `master`, typechecks, builds, packages and creates a release tagged `v<package.json version>-build.<run number>`, marked latest.
- `docs/adr/`: architecture decisions.

## Platform facts

These come from gamescope's source (`src/steamcompmgr.cpp`, `src/reshade_effect_manager.cpp`, `src/rendervulkan.cpp`) and nothing in this repository shows them. Check them again before you change `gamescope.py` or a shader.

- gamescope reads `GAMESCOPE_RESHADE_EFFECT` (a UTF8 string path relative to `~/.local/share/gamescope/reshade/Shaders/`, falling back to `/usr/share/gamescope/reshade/Shaders/`) and `GAMESCOPE_RESHADE_TECHNIQUE_IDX` (32-bit cardinal) from the root window of its Xwayland server. Deleting the effect property turns the effect off.
- The effect runs on composite layer 0, the focused app: the Steam UI when no game is focused, otherwise the game. Overlay layers (the Quick Access Menu, notifications, performance overlay) are drawn on top unfiltered. `BUFFER_WIDTH`/`BUFFER_HEIGHT` are the focused app's buffer size, not the display's.
- gamescope compiles only a subset of ReShade FX. Keep shaders self-contained: no `#include "ReShade.fxh"` (it is not guaranteed to be installed), no runtime-changing uniforms, and no textures with mip levels (gamescope asserts `levels == 1`). Read the input with `texture X : COLOR;`.
- The plugin runs as the session user (no `_root` flag), so it can reach the user's Xwayland and `~/.local/share` directly. Decky sets `LD_LIBRARY_PATH` to its bundled libraries, so clear it before running system binaries such as `xprop`.

## Features

### CRT filter toggle

- The Quick Access panel shows a **CRT filter** toggle. It reflects whether the filter is currently on and applies changes immediately.
- Turning it on installs the bundled shaders (see Setup), then sets the selected Shader's effect path and technique index on gamescope.
- Turning it off deletes the effect property, but only when the current value is one of ours (it starts with `DeckyCRT/`), so another plugin's shader is never cleared.
- Outside an Auto-apply Session the toggle edits the Default State, which is persisted and restored after a reboot or Decky restart.

### Shaders

- Shaders are listed in the Shader Registry (`SHADERS` in `py_modules/crt_filter/shaders.py`). Each entry has an `id`, display `name`, `description`, `.fx` `file` and `technique_index`.
- The panel shows a **Shader** dropdown only when the registry holds more than one shader. The selection is persisted, and an unknown saved id falls back to the default shader.
- To add a shader: add a self-contained `.fx` file to `defaults/shaders/` that follows the Platform facts, then add a registry entry. No frontend change is needed.
- Shader tunables are preprocessor `#define`s with `#ifndef` guards, so a future feature can generate a wrapper `.fx` that overrides them and then `#include`s the base file. This is how per-user shader settings should be built, because gamescope cannot change uniforms at runtime.

### Auto-apply per game

- While a game is the Running App, the panel shows an **Auto-apply for this game** toggle.
- Turning it on adds the game's app id to the persisted Auto-apply Games list and starts an Auto-apply Session at once, so the filter turns on.
- Turning it off removes the game from the list and ends the session, so the filter returns to the Default State.
- When an Auto-apply Game becomes the Running App, an Auto-apply Session starts and the filter turns on. While the session lasts, the main toggle changes the filter for this session only and leaves the Default State alone.
- When the Running App changes, to another game or to none, the session ends and the filter returns to the Default State.
- App ids are stored as strings, so non-Steam shortcuts work too.
- The frontend detects the Running App from `Router.MainRunningApp`. It re-checks after each `SteamClient.GameSessions.RegisterForAppLifetimeNotifications` event and polls every few seconds as a safety net, and reports each change through `set_running_app`.

### Setup and lifecycle

- There is nothing separate to install. ReShade is built into gamescope, and the plugin copies its bundled shaders into `~/.local/share/gamescope/reshade/Shaders/DeckyCRT/`, replacing a copy only when its content differs. It installs before every apply, so plugin updates ship new shader versions.
- The backend finds gamescope's X display from the `DISPLAY` and `XAUTHORITY` of processes that carry `GAMESCOPE_WAYLAND_DISPLAY`, Steam's first, then every `/tmp/.X11-unix/X*` socket. It confirms a display by checking that the `GAMESCOPE_RESHADE_EFFECT` atom exists. Display numbers differ between machines, so never hardcode `:0`.
- X11 is driven through libX11 via `ctypes`, with `xprop` as the fallback. A custom Xlib error handler stops Xlib from exiting the plugin process.
- At startup the backend waits up to about a minute for gamescope, then applies the saved state. The frontend calls `frontend_ready` every time it loads, which re-applies the state after Steam or gamescope restarts, because gamescope loses the property when it restarts.
- When the plugin unloads it clears our effect and keeps the settings. Uninstalling also deletes the `DeckyCRT/` shader folder.
- When no gamescope session with ReShade support is found (Desktop Mode, or a gamescope too old to have it), the panel shows the error and the toggles stay usable.

### Constraints

- Everything is Game Mode only. Desktop Mode (Plasma) does not run gamescope and is out of scope.
- ShaderGlass is deliberately not used: see [ADR 0001](./docs/adr/0001-gamescope-reshade-instead-of-shaderglass.md).
- Write UI copy with hyphens instead of em dashes.

## Commands

- `pnpm install`, then `pnpm build` (Rollup bundle in `dist/`) and `pnpm typecheck`.
- `bash scripts/package.sh` after a build, to produce the release zip and installer in `out/`. When you add a top-level file the plugin needs at runtime, add it to `package.sh` too.
- There is no test suite yet. To check a shader compiles the way gamescope compiles it, build gamescope's pinned ReShade fork (`src/reshade` submodule of ValveSoftware/gamescope) with a small harness that mirrors `ReshadeEffectPipeline::init`, and run it on the `.fx` file.
