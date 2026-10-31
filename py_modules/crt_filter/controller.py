"""Decides whether the CRT filter is on and keeps gamescope in sync with that decision.

See the "Features" section of AGENTS.md for the behaviour this implements.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from .gamescope import GamescopeError
from .installer import effect_path, is_own_effect
from .settings import Settings, SettingsStore
from .shaders import SHADERS, get_shader


class GamescopeControl(Protocol):
    def set_effect(self, effect_path: str, technique_index: int) -> None: ...
    def get_effect(self) -> str: ...
    def clear_effect(self) -> None: ...


@dataclass
class RunningApp:
    id: str
    name: str


@dataclass
class AutoApplySession:
    app_id: str
    active: bool = True


class Controller:
    def __init__(
        self,
        store: SettingsStore,
        gamescope: GamescopeControl,
        install_shaders: Callable[[], None],
        on_state_change: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self._store = store
        self._settings: Settings = store.load()
        self._gamescope = gamescope
        self._install_shaders = install_shaders
        self._on_state_change = on_state_change
        self._running_app: RunningApp | None = None
        self._session: AutoApplySession | None = None
        self._error: str | None = None
        self._lock = asyncio.Lock()

    @property
    def active(self) -> bool:
        return self._session.active if self._session else self._settings.enabled

    def state(self) -> dict[str, Any]:
        app = self._running_app
        return {
            "active": self.active,
            "shaderId": get_shader(self._settings.shader_id).id,
            "shaders": [{"id": s.id, "name": s.name, "description": s.description} for s in SHADERS],
            "runningApp": {"id": app.id, "name": app.name} if app else None,
            "autoApply": bool(app and app.id in self._settings.auto_apply_app_ids),
            "error": self._error,
        }

    async def set_active(self, active: bool) -> dict[str, Any]:
        if self._session:
            self._session.active = active
        else:
            self._settings.enabled = active
            self._store.save(self._settings)
        return await self._apply()

    async def set_shader(self, shader_id: str) -> dict[str, Any]:
        self._settings.shader_id = get_shader(shader_id).id
        self._store.save(self._settings)
        return await self._apply()

    async def set_running_app(self, app_id: str | None, app_name: str | None) -> dict[str, Any]:
        app = RunningApp(str(app_id), app_name or "") if app_id else None
        if (app and self._running_app and app.id == self._running_app.id) or (app is None and self._running_app is None):
            self._running_app = app
            return self.state()
        self._running_app = app
        in_list = app is not None and app.id in self._settings.auto_apply_app_ids
        self._session = AutoApplySession(app.id) if app and in_list else None
        return await self._apply()

    async def set_auto_apply(self, enabled: bool) -> dict[str, Any]:
        app = self._running_app
        if app is None:
            return self.state()
        app_ids = self._settings.auto_apply_app_ids
        if enabled:
            if app.id not in app_ids:
                app_ids.append(app.id)
            self._session = AutoApplySession(app.id)
        else:
            if app.id in app_ids:
                app_ids.remove(app.id)
            if self._session and self._session.app_id == app.id:
                self._session = None
        self._store.save(self._settings)
        return await self._apply()

    async def sync(self) -> dict[str, Any]:
        """Re-asserts the current state, e.g. after gamescope restarted and lost its properties."""
        return await self._apply()

    async def clear(self) -> None:
        """Turns our effect off without changing settings, for when the plugin stops."""
        async with self._lock:
            try:
                await self._clear_own_effect()
            except (GamescopeError, OSError):
                pass

    async def _clear_own_effect(self) -> None:
        current = await asyncio.to_thread(self._gamescope.get_effect)
        if is_own_effect(current):
            await asyncio.to_thread(self._gamescope.clear_effect)

    async def _apply(self) -> dict[str, Any]:
        async with self._lock:
            try:
                if self.active:
                    await asyncio.to_thread(self._install_shaders)
                    shader = get_shader(self._settings.shader_id)
                    await asyncio.to_thread(self._gamescope.set_effect, effect_path(shader), shader.technique_index)
                else:
                    await self._clear_own_effect()
                self._error = None
            except GamescopeError as error:
                self._error = str(error)
            except OSError as error:
                self._error = f"Could not install shaders: {error}"
        state = self.state()
        await self._on_state_change(state)
        return state
