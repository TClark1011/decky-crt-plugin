#!/usr/bin/env bash
# Installs the CRT Filter plugin into Decky Loader and restarts Decky.
#
# Usage:
#   ./install.sh                     uses decky-crt-filter.zip next to this script,
#                                    otherwise downloads the latest release
#   ./install.sh path/to/plugin.zip  installs that zip
#
# Set CRT_FILTER_REPO=owner/repo to download from a different repository.
set -euo pipefail

name="decky-crt-filter"
repo="${CRT_FILTER_REPO:-__GITHUB_REPOSITORY__}"

fail() {
  echo "Error: $*" >&2
  exit 1
}

for command in unzip sudo systemctl getent; do
  command -v "$command" >/dev/null || fail "'$command' is required but not installed."
done

user="${SUDO_USER:-$USER}"
user_home="$(getent passwd "$user" | cut -d: -f6)"
plugins_dir="$user_home/homebrew/plugins"
[[ -d "$user_home/homebrew" ]] || fail "Decky Loader was not found in $user_home/homebrew. Install it first: https://decky.xyz"

work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT

zip_path="${1:-}"
script_path="${BASH_SOURCE[0]:-}"
if [[ -z "$zip_path" && -f "$script_path" && -f "$(dirname "$script_path")/$name.zip" ]]; then
  zip_path="$(dirname "$script_path")/$name.zip"
fi
if [[ -z "$zip_path" ]]; then
  [[ "$repo" != "__GITHUB_REPOSITORY__" ]] || fail "No zip given and no repository set. Pass a zip path or set CRT_FILTER_REPO."
  command -v curl >/dev/null || fail "'curl' is required to download the plugin."
  zip_path="$work_dir/$name.zip"
  echo "Downloading the latest release from $repo..."
  curl -fsSL -o "$zip_path" "https://github.com/$repo/releases/latest/download/$name.zip" \
    || fail "Download failed. For a private repository, download $name.zip yourself and pass its path."
fi
[[ -f "$zip_path" ]] || fail "$zip_path does not exist."

unzip -q "$zip_path" -d "$work_dir/extracted"
[[ -f "$work_dir/extracted/$name/plugin.json" ]] || fail "$zip_path does not contain a $name plugin."

echo "Installing to $plugins_dir/$name (needs sudo)..."
sudo mkdir -p "$plugins_dir"
sudo rm -rf "${plugins_dir:?}/$name"
sudo cp -r "$work_dir/extracted/$name" "$plugins_dir/$name"

echo "Restarting Decky Loader..."
sudo systemctl restart plugin_loader

echo "Done. Open the Quick Access Menu in Game Mode and find CRT Filter in the Decky tab."
