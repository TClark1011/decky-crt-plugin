# CRT Filter

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin that applies a CRT shader to the whole SteamOS Game Mode screen, covering both the Steam interface and games. You can set it to turn on automatically for specific games.

It works on any machine running a gamescope session (Game Mode), including the Steam Deck and desktops running SteamOS-like distributions such as CachyOS or Bazzite. It uses gamescope's built-in ReShade support, so there is nothing else to install.

## Use

1. Open the Quick Access Menu and choose **CRT Filter**.
2. Turn on **CRT filter**.
3. With a game running, turn on **Auto-apply for this game** to have the filter switch on whenever that game runs.

The Quick Access Menu, notifications and other overlays are drawn on top of the filter, so they are not filtered.

## Requirements

- Decky Loader, in Game Mode on a gamescope version with ReShade support (SteamOS 3.5 or later, or an equivalent gamescope)
- For development: [Node.js](https://nodejs.org) 20 or later and [pnpm](https://pnpm.io) 9

## Develop

```sh
pnpm install
pnpm build       # bundles the frontend into dist/
pnpm typecheck
```

To package the plugin, use the [Decky CLI](https://github.com/SteamDeckHomebrew/cli). It zips `dist/`, `main.py`, `py_modules/`, `plugin.json`, `package.json` and the contents of `defaults/`.

## Credits

The bundled shader is adapted from Timothy Lottes' public domain CRT shader.
