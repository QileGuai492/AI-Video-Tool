export type ObjectType = "box" | "cylinder" | "sphere" | "plane" | "humanoid";

export type Vec3 = [number, number, number];

export interface SceneObject {
  id: string;
  name: string;
  type: ObjectType;
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
}

export interface Keyframe {
  time: number;
  position: Vec3;
  rotation: Vec3;
  scale: Vec3;
}

export interface CameraKeyframe {
  time: number;
  position: Vec3;
  target: Vec3;
}

export interface ShotDescription {
  action: string;
  camera: string;
}

export interface SceneState {
  objects: SceneObject[];
  keyframes: Record<string, Keyframe[]>;
  cameraKeyframes: CameraKeyframe[];
  shotMarkers: number[];
  shotDescriptions: Record<number, ShotDescription>;
  duration: number;
}
