import type { Vec3 } from "./types";

/** 当前相机状态（由 PrevisCanvas 每帧更新，供工具栏记录相机关键帧使用）。 */
export const cameraRef: { position: Vec3; target: Vec3 } = {
  position: [5, 4, 5],
  target: [0, 0, 0],
};
