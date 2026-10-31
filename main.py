import asyncio
from pathlib import Path
from typing import Any

import decky

from crt_filter.controller import Controller
from crt_filter.gamescope import Gamescope
from crt_filter.installer import bundled_shaders_dir, gamescope_shaders_dir, install_shaders, uninstall_shaders
from crt_filter.settings import SettingsStore

STATE_CHANGED_EVENT = "state_changed"
# gamescope may still be starting when Decky loads the plugin at boot.
STARTUP_RETRY_SECONDS = 2
STARTUP_RETRY_ATTEMPTS = 30


async def _emit_state(state: dict[str, Any]) -> None:
    await decky.emit(STATE_CHANGED_EVENT, state)


class Plugin:
    # Built here rather than in _main because the frontend can call methods before _main runs.
    def __init__(self) -> None:
        shaders_dir = gamescope_shaders_dir(decky.DECKY_USER_HOME)
        source_dir = bundled_shaders_dir(decky.DECKY_PLUGIN_DIR)
        self.gamescope = Gamescope()
        self.controller = Controller(
            store=SettingsStore(Path(decky.DECKY_PLUGIN_SETTINGS_DIR) / "settings.json"),
            gamescope=self.gamescope,
            install_shaders=lambda: install_shaders(source_dir, shaders_dir),
            on_state_change=_emit_state,
        )

    async def get_state(self) -> dict[str, Any]:
        return self.controller.state()

    async def frontend_ready(self) -> dict[str, Any]:
        """Called by the frontend whenever it loads, which includes after Steam or gamescope restarts."""
        return await self.controller.sync()

    async def set_active(self, active: bool) -> dict[str, Any]:
        return await self.controller.set_active(active)

    async def set_shader(self, shader_id: str) -> dict[str, Any]:
        return await self.controller.set_shader(shader_id)

    async def set_running_app(self, app_id: str | None, app_name: str | None) -> dict[str, Any]:
        return await self.controller.set_running_app(app_id, app_name)

    async def set_auto_apply(self, enabled: bool) -> dict[str, Any]:
        return await self.controller.set_auto_apply(enabled)

    async def _main(self) -> None:
        for _ in range(STARTUP_RETRY_ATTEMPTS):
            if await asyncio.to_thread(self.gamescope.is_available):
                break
            await asyncio.sleep(STARTUP_RETRY_SECONDS)
        state = await self.controller.sync()
        decky.logger.info("CRT Filter started: %s", state)

    async def _unload(self) -> None:
        await self.controller.clear()

    async def _uninstall(self) -> None:
        uninstall_shaders(gamescope_shaders_dir(decky.DECKY_USER_HOME))
