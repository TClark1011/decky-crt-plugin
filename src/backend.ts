import { addEventListener, callable, removeEventListener } from "@decky/api";

export interface ShaderOption {
  id: string;
  name: string;
  description: string;
}

export interface PluginState {
  active: boolean;
  shaderId: string;
  shaders: ShaderOption[];
  runningApp: { id: string; name: string } | null;
  autoApply: boolean;
  error: string | null;
}

export const getState = callable<[], PluginState>("get_state");
export const frontendReady = callable<[], PluginState>("frontend_ready");
export const setActive = callable<[active: boolean], PluginState>("set_active");
export const setShader = callable<[shaderId: string], PluginState>("set_shader");
export const setRunningApp = callable<[appId: string | null, appName: string | null], PluginState>(
  "set_running_app",
);
export const setAutoApply = callable<[enabled: boolean], PluginState>("set_auto_apply");

const STATE_CHANGED_EVENT = "state_changed";

export function onStateChanged(listener: (state: PluginState) => void): () => void {
  const registered = addEventListener<[state: PluginState]>(STATE_CHANGED_EVENT, listener);
  return () => removeEventListener(STATE_CHANGED_EVENT, registered);
}
