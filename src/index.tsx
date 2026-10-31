import { DropdownItem, PanelSection, PanelSectionRow, ToggleField, staticClasses } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { useEffect, useState } from "react";
import { FaTv } from "react-icons/fa";
import {
  type PluginState,
  frontendReady,
  getState,
  onStateChanged,
  setActive,
  setAutoApply,
  setShader,
} from "~/backend";
import { trackRunningApp } from "~/runningApp";

function Content() {
  const [state, setState] = useState<PluginState | null>(null);

  useEffect(() => {
    void getState().then(setState);
    return onStateChanged(setState);
  }, []);

  if (!state) return null;

  return (
    <PanelSection>
      <PanelSectionRow>
        <ToggleField
          label="CRT filter"
          description="Applies to the Steam interface and games."
          checked={state.active}
          onChange={(checked) => void setActive(checked).then(setState)}
        />
      </PanelSectionRow>
      {state.shaders.length > 1 && (
        <PanelSectionRow>
          <DropdownItem
            label="Shader"
            description={state.shaders.find((shader) => shader.id === state.shaderId)?.description}
            rgOptions={state.shaders.map((shader) => ({ data: shader.id, label: shader.name }))}
            selectedOption={state.shaderId}
            onChange={(option) => void setShader(option.data).then(setState)}
          />
        </PanelSectionRow>
      )}
      {state.runningApp && (
        <PanelSectionRow>
          <ToggleField
            label="Auto-apply for this game"
            description={`Turns the filter on whenever ${state.runningApp.name || "this game"} is running.`}
            checked={state.autoApply}
            onChange={(checked) => void setAutoApply(checked).then(setState)}
          />
        </PanelSectionRow>
      )}
      {state.error && (
        <PanelSectionRow>
          <div style={{ fontSize: "12px", color: "#ff9b9b" }}>{state.error}</div>
        </PanelSectionRow>
      )}
    </PanelSection>
  );
}

export default definePlugin(() => {
  void frontendReady();
  const stopTracking = trackRunningApp();

  return {
    name: "CRT Filter",
    titleView: <div className={staticClasses.Title}>CRT Filter</div>,
    content: <Content />,
    icon: <FaTv />,
    onDismount() {
      stopTracking();
    },
  };
});
