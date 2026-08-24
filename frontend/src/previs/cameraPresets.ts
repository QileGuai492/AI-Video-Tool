import type { Vec3 } from "./types";

export type CameraPreset = "dolly_in" | "dolly_out" | "pan_left" | "pan_right" | "truck_left" | "truck_right" | "orbit";
export type CameraViewPreset = "front" | "back" | "left" | "right" | "top" | "perspective";

function add(a: Vec3, b: Vec3): Vec3 {
  return [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
}

function sub(a: Vec3, b: Vec3): Vec3 {
  return [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
}

function scale(v: Vec3, s: number): Vec3 {
  return [v[0] * s, v[1] * s, v[2] * s];
}

function length(v: Vec3): number {
  return Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
}

function normalize(v: Vec3): Vec3 {
  const len = length(v);
  if (len === 0) return v;
  return scale(v, 1 / len);
}

function rotateY(v: Vec3, angle: number): Vec3 {
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  return [v[0] * cos + v[2] * sin, v[1], -v[0] * sin + v[2] * cos];
}

/**
 * 根据当前相机位置与目标点，计算常用运镜预设的新相机参数。
 */
export function applyCameraPreset(
  preset: CameraPreset,
  position: Vec3,
  target: Vec3
): { position: Vec3; target: Vec3 } {
  const offset = sub(position, target);
  const distance = length(offset);
  const direction = normalize(offset);
  const right: Vec3 = normalize([-direction[2], 0, direction[0]]);

  switch (preset) {
    case "dolly_in":
      return { position: add(target, scale(direction, Math.max(0.5, distance * 0.8))), target };
    case "dolly_out":
      return { position: add(target, scale(direction, distance * 1.2)), target };
    case "pan_left":
      return { position: add(target, rotateY(offset, 0.3)), target };
    case "pan_right":
      return { position: add(target, rotateY(offset, -0.3)), target };
    case "truck_left":
      return { position: add(position, scale(right, -0.5)), target: add(target, scale(right, -0.5)) };
    case "truck_right":
      return { position: add(position, scale(right, 0.5)), target: add(target, scale(right, 0.5)) };
    case "orbit":
      return { position: add(target, rotateY(offset, 0.6)), target };
    default:
      return { position, target };
  }
}

export const CAMERA_PRESET_LABELS: { value: CameraPreset; label: string }[] = [
  { value: "dolly_in", label: "推近" },
  { value: "dolly_out", label: "拉远" },
  { value: "pan_left", label: "左摇" },
  { value: "pan_right", label: "右摇" },
  { value: "truck_left", label: "左移" },
  { value: "truck_right", label: "右移" },
  { value: "orbit", label: "环绕" },
];

const VIEW_DISTANCE = 8;

/** 根据视角预设计算相机位置，保持当前目标点不变。 */
export function applyCameraView(preset: CameraViewPreset, target: Vec3): { position: Vec3; target: Vec3 } {
  const [tx, ty, tz] = target;
  switch (preset) {
    case "front":
      return { position: [tx, ty + 1, tz + VIEW_DISTANCE], target: [tx, ty, tz] };
    case "back":
      return { position: [tx, ty + 1, tz - VIEW_DISTANCE], target: [tx, ty, tz] };
    case "left":
      return { position: [tx - VIEW_DISTANCE, ty + 1, tz], target: [tx, ty, tz] };
    case "right":
      return { position: [tx + VIEW_DISTANCE, ty + 1, tz], target: [tx, ty, tz] };
    case "top":
      return { position: [tx, ty + VIEW_DISTANCE, tz + 0.01], target: [tx, ty, tz] };
    case "perspective":
    default:
      return { position: [tx + 5, ty + 4, tz + 5], target: [tx, ty, tz] };
  }
}

export const CAMERA_VIEW_LABELS: { value: CameraViewPreset; label: string }[] = [
  { value: "front", label: "前视图" },
  { value: "back", label: "后视图" },
  { value: "left", label: "左视图" },
  { value: "right", label: "右视图" },
  { value: "top", label: "顶视图" },
  { value: "perspective", label: "透视" },
];
