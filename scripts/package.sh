#!/usr/bin/env bash
# Packages the built plugin into out/decky-crt-filter.zip, writes out/install.sh, and
# bundles both into out/decky-crt-filter-installer.tar.gz.
# Run `pnpm build` first. The zip follows the Decky CLI layout, so Decky's
# "Install plugin from ZIP" accepts it too.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
name="decky-crt-filter"
out="$root/out"
stage="$out/stage/$name"

if [[ ! -f "$root/dist/index.js" ]]; then
  echo "dist/index.js is missing. Run pnpm build first." >&2
  exit 1
fi

rm -rf "$out"
mkdir -p "$stage"

cp -r "$root/dist" "$root/py_modules" "$stage/"
cp "$root/main.py" "$root/plugin.json" "$root/package.json" "$root/LICENSE" "$root/README.md" "$stage/"
# Decky's packager copies the contents of defaults/ into the plugin root.
cp -r "$root/defaults/." "$stage/"
find "$stage" -name __pycache__ -type d -prune -exec rm -rf {} +

(cd "$out/stage" && zip -qr "$out/$name.zip" "$name")
rm -rf "$out/stage"

# Point the installer at this repository's releases when built in GitHub Actions.
sed "s|__GITHUB_REPOSITORY__|${GITHUB_REPOSITORY:-__GITHUB_REPOSITORY__}|" "$root/scripts/install.sh" > "$out/install.sh"
chmod +x "$out/install.sh"

# Release asset downloads lose file modes; tar keeps install.sh executable.
tar -czf "$out/$name-installer.tar.gz" -C "$out" install.sh "$name.zip"

echo "Wrote $out/$name.zip, $out/install.sh and $out/$name-installer.tar.gz"
