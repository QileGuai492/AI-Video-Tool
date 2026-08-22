import { beforeEach, describe, expect, it } from "vitest";
import { usePrevisStore } from "../previs/store";

describe("previsStore", () => {
  beforeEach(() => {
    usePrevisStore.setState({
      objects: [],
      keyframes: {},
      cameraKeyframes: [],
      shotMarkers: [],
      shotDescriptions: {},
      duration: 5,
      selectedObjectId: null,
      currentTime: 0,
      isPlaying: false,
    });
  });

  it("addObject 会新增对象并选中", () => {
    usePrevisStore.getState().addObject("box");
    const state = usePrevisStore.getState();
    expect(state.objects).toHaveLength(1);
    expect(state.selectedObjectId).toBe(state.objects[0].id);
  });

  it("updateObject 会更新对象变换", () => {
    usePrevisStore.getState().addObject("sphere");
    const id = usePrevisStore.getState().objects[0].id;
    usePrevisStore.getState().updateObject(id, { position: [1, 2, 3] });
    expect(usePrevisStore.getState().objects[0].position).toEqual([1, 2, 3]);
  });

  it("addKeyframe 会记录当前变换", () => {
    usePrevisStore.getState().addObject("box");
    const id = usePrevisStore.getState().objects[0].id;
    usePrevisStore.getState().updateObject(id, { position: [2, 0, 0] });
    usePrevisStore.getState().addKeyframe(id, 0);
    const frames = usePrevisStore.getState().keyframes[id];
    expect(frames).toHaveLength(1);
    expect(frames[0].position).toEqual([2, 0, 0]);
  });

  it("duplicateObject 会复制对象", () => {
    usePrevisStore.getState().addObject("humanoid");
    const id = usePrevisStore.getState().objects[0].id;
    usePrevisStore.getState().duplicateObject(id);
    expect(usePrevisStore.getState().objects).toHaveLength(2);
  });

  it("removeObject 会删除对象及其关键帧", () => {
    usePrevisStore.getState().addObject("box");
    const id = usePrevisStore.getState().objects[0].id;
    usePrevisStore.getState().addKeyframe(id, 0);
    usePrevisStore.getState().removeObject(id);
    const state = usePrevisStore.getState();
    expect(state.objects).toHaveLength(0);
    expect(state.keyframes[id]).toBeUndefined();
  });

  it("addShotMarker 与 removeShotMarker 应维护镜头切点", () => {
    usePrevisStore.getState().addShotMarker(1);
    usePrevisStore.getState().addShotMarker(3);
    usePrevisStore.getState().addShotMarker(1);
    expect(usePrevisStore.getState().shotMarkers).toEqual([1, 3]);
    usePrevisStore.getState().removeShotMarker(1);
    expect(usePrevisStore.getState().shotMarkers).toEqual([3]);
  });

  it("setShotDescription 应保存镜头描述", () => {
    usePrevisStore.getState().addShotMarker(2);
    usePrevisStore.getState().setShotDescription(2, { action: "人物向前走", camera: "跟拍" });
    expect(usePrevisStore.getState().shotDescriptions[2]).toEqual({
      action: "人物向前走",
      camera: "跟拍",
    });
  });
});
