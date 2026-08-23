import { describe, expect, it } from "vitest";
import { applyCameraPreset } from "../previs/cameraPresets";

function distance(a: [number, number, number], b: [number, number, number]): number {
  return Math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2);
}

describe("cameraPresets", () => {
  const position: [number, number, number] = [5, 3, 5];
  const target: [number, number, number] = [0, 0, 0];

  it("dolly_in 应缩短相机与目标距离", () => {
    const next = applyCameraPreset("dolly_in", position, target);
    expect(distance(next.position, next.target)).toBeLessThan(distance(position, target));
  });

  it("dolly_out 应增大相机与目标距离", () => {
    const next = applyCameraPreset("dolly_out", position, target);
    expect(distance(next.position, next.target)).toBeGreaterThan(distance(position, target));
  });

  it("orbit 应保持距离并改变相机位置", () => {
    const next = applyCameraPreset("orbit", position, target);
    expect(distance(next.position, next.target)).toBeCloseTo(distance(position, target), 5);
    expect(next.position).not.toEqual(position);
  });

  it("truck_left 应同时平移相机与目标", () => {
    const next = applyCameraPreset("truck_left", position, target);
    expect(next.position[0]).not.toBe(position[0]);
    expect(next.target[0]).not.toBe(target[0]);
  });
});
