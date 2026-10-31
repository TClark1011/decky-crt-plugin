# CRT Filter

A [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader) plugin that applies a CRT shader to the whole SteamOS Game Mode screen, covering both the Steam interface and games. You can set it to turn on automatically for specific games.

It works on any machine running a gamescope session (Game Mode), including the Steam Deck and desktops running SteamOS-like distributions such as CachyOS or Bazzite. It uses gamescope's built-in ReShade support, so there is nothing else to install.

## Install

On a machine with [Decky Loader](https://decky.xyz) installed, run:

```sh
curl -fsSL https://github.com/<owner>/<repo>/releases/latest/download/install.sh | bash
```

If the repository is private, download `decky-crt-filter.zip` and `install.sh` from the latest release into one folder and run `bash install.sh`. The zip also works with Decky's "Install plugin from ZIP" option in developer mode.

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

To package the plugin, run `bash scripts/package.sh` after building. It writes `out/decky-crt-filter.zip` and `out/install.sh`. Every push to `master` does this in GitHub Actions and publishes the result as the latest release.

## Credits

The bundled shader is adapted from Timothy Lottes' public domain CRT shader.
