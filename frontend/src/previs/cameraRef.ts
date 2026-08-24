import type { Vec3 } from "./types";

export interface CameraView {
  position: Vec3;
  target: Vec3;
}

/** 当前相机状态（由 PrevisCanvas 每帧更新，供工具栏记录相机关键帧使用）。 */
export const cameraRef: { position: Vec3; target: Vec3 } = {
  position: [5, 4, 5],
  target: [0, 0, 0],
};

type CameraViewListener = (view: CameraView) => void;

const cameraViewListeners = new Set<CameraViewListener>();

/** 外部（工具栏）设置相机视角，并通知 PrevisCanvas 立即应用。 */
export function setCameraView(view: CameraView): void {
  cameraRef.position = [...view.position];
  cameraRef.target = [...view.target];
  cameraViewListeners.forEach((listener) => listener({ position: [...view.position], target: [...view.target] }));
}

/** 订阅相机视角变化，返回取消订阅函数。 */
export function onCameraView(listener: CameraViewListener): () => void {
  cameraViewListeners.add(listener);
  return () => {
    cameraViewListeners.delete(listener);
  };
}
