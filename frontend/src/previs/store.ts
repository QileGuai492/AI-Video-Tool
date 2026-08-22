import { create } from "zustand";
import type { CameraKeyframe, Keyframe, ObjectType, SceneObject, SceneState, Vec3 } from "./types";

let objectSeq = 0;

function createObject(type: ObjectType, name: string): SceneObject {
  objectSeq += 1;
  return {
    id: `obj_${Date.now()}_${objectSeq}`,
    name,
    type,
    position: [0, 0.5, 0],
    rotation: [0, 0, 0],
    scale: [1, 1, 1],
  };
}

interface PrevisStore extends SceneState {
  selectedObjectId: string | null;
  currentTime: number;
  isPlaying: boolean;
  addObject: (type: ObjectType) => void;
  removeObject: (id: string) => void;
  duplicateObject: (id: string) => void;
  updateObject: (id: string, patch: Partial<Pick<SceneObject, "position" | "rotation" | "scale">>) => void;
  selectObject: (id: string | null) => void;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  addKeyframe: (objectId: string, time: number) => void;
  removeKeyframe: (objectId: string, time: number) => void;
  addCameraKeyframe: (time: number, position: Vec3, target: Vec3) => void;
  setDuration: (duration: number) => void;
  exportScene: () => SceneState;
  loadScene: (scene: SceneState) => void;
}

const defaultState: SceneState = {
  objects: [],
  keyframes: {},
  cameraKeyframes: [],
  duration: 5,
};

export const usePrevisStore = create<PrevisStore>((set, get) => ({
  ...defaultState,
  selectedObjectId: null,
  currentTime: 0,
  isPlaying: false,

  addObject: (type) => {
    const names: Record<ObjectType, string> = {
      box: "方块",
      cylinder: "圆柱",
      sphere: "球体",
      plane: "平面",
      humanoid: "灰模人形",
    };
    const obj = createObject(type, names[type]);
    set((state) => ({ objects: [...state.objects, obj], selectedObjectId: obj.id }));
  },

  removeObject: (id) => {
    set((state) => {
      const objects = state.objects.filter((obj) => obj.id !== id);
      const keyframes = { ...state.keyframes };
      delete keyframes[id];
      return {
        objects,
        keyframes,
        selectedObjectId: state.selectedObjectId === id ? null : state.selectedObjectId,
      };
    });
  },

  duplicateObject: (id) => {
    const source = get().objects.find((obj) => obj.id === id);
    if (!source) return;
    const copy = createObject(source.type, `${source.name}（副本）`);
    copy.position = [...source.position];
    copy.rotation = [...source.rotation];
    copy.scale = [...source.scale];
    set((state) => ({ objects: [...state.objects, copy], selectedObjectId: copy.id }));
  },

  updateObject: (id, patch) => {
    set((state) => ({
      objects: state.objects.map((obj) => (obj.id === id ? { ...obj, ...patch } : obj)),
    }));
  },

  selectObject: (id) => set({ selectedObjectId: id }),

  setCurrentTime: (time) => {
    const duration = get().duration;
    set({ currentTime: Math.max(0, Math.min(duration, time)) });
  },

  setIsPlaying: (playing) => set({ isPlaying: playing }),

  addKeyframe: (objectId, time) => {
    const obj = get().objects.find((item) => item.id === objectId);
    if (!obj) return;
    const frame: Keyframe = {
      time,
      position: [...obj.position],
      rotation: [...obj.rotation],
      scale: [...obj.scale],
    };
    set((state) => {
      const list = [...(state.keyframes[objectId] ?? []).filter((item) => Math.abs(item.time - time) > 0.01), frame].sort(
        (a, b) => a.time - b.time
      );
      return { keyframes: { ...state.keyframes, [objectId]: list } };
    });
  },

  removeKeyframe: (objectId, time) => {
    set((state) => ({
      keyframes: {
        ...state.keyframes,
        [objectId]: (state.keyframes[objectId] ?? []).filter((item) => Math.abs(item.time - time) > 0.01),
      },
    }));
  },

  addCameraKeyframe: (time, position, target) => {
    const frame: CameraKeyframe = { time, position: [...position], target: [...target] };
    set((state) => ({
      cameraKeyframes: [...state.cameraKeyframes.filter((item) => Math.abs(item.time - time) > 0.01), frame].sort(
        (a, b) => a.time - b.time
      ),
    }));
  },

  setDuration: (duration) => set({ duration: Math.max(1, duration) }),

  exportScene: () => {
    const { objects, keyframes, cameraKeyframes, duration } = get();
    return { objects, keyframes, cameraKeyframes, duration };
  },

  loadScene: (scene) => {
    set({
      objects: scene.objects ?? [],
      keyframes: scene.keyframes ?? {},
      cameraKeyframes: scene.cameraKeyframes ?? [],
      duration: scene.duration ?? 5,
      selectedObjectId: null,
      currentTime: 0,
      isPlaying: false,
    });
  },
}));
