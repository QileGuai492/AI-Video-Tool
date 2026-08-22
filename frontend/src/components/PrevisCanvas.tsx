import { useEffect, useMemo, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { TransformControls } from "three/examples/jsm/controls/TransformControls.js";
import { cameraRef } from "../previs/cameraRef";
import { usePrevisStore } from "../previs/store";
import type { ObjectType, Vec3 } from "../previs/types";

function createMesh(type: ObjectType): THREE.Object3D {
  if (type === "humanoid") {
    const group = new THREE.Group();
    const material = new THREE.MeshStandardMaterial({ color: 0xdddddd });
    const body = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.8, 0.3), material);
    body.position.y = 0.9;
    const head = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.35, 0.35), material);
    head.position.y = 1.55;
    const leftLeg = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.6, 0.2), material);
    leftLeg.position.set(-0.15, 0.3, 0);
    const rightLeg = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.6, 0.2), material);
    rightLeg.position.set(0.15, 0.3, 0);
    const leftArm = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.55, 0.18), material);
    leftArm.position.set(-0.42, 1.0, 0);
    const rightArm = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.55, 0.18), material);
    rightArm.position.set(0.42, 1.0, 0);
    group.add(body, head, leftLeg, rightLeg, leftArm, rightArm);
    return group;
  }

  let geometry: THREE.BufferGeometry;
  switch (type) {
    case "box":
      geometry = new THREE.BoxGeometry(1, 1, 1);
      break;
    case "cylinder":
      geometry = new THREE.CylinderGeometry(0.5, 0.5, 1, 16);
      break;
    case "sphere":
      geometry = new THREE.SphereGeometry(0.5, 16, 16);
      break;
    case "plane":
      geometry = new THREE.PlaneGeometry(1, 1);
      break;
    default:
      geometry = new THREE.BoxGeometry(1, 1, 1);
  }
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xcccccc }));
  return mesh;
}

function lerpVec3(a: Vec3, b: Vec3, t: number): Vec3 {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

function interpolateTransform(
  keyframes: { time: number; position: Vec3; rotation: Vec3; scale: Vec3 }[],
  time: number
): { position: Vec3; rotation: Vec3; scale: Vec3 } | null {
  if (keyframes.length === 0) return null;
  if (time <= keyframes[0].time) return keyframes[0];
  if (time >= keyframes[keyframes.length - 1].time) return keyframes[keyframes.length - 1];
  for (let i = 0; i < keyframes.length - 1; i += 1) {
    const a = keyframes[i];
    const b = keyframes[i + 1];
    if (time >= a.time && time <= b.time) {
      const t = b.time === a.time ? 0 : (time - a.time) / (b.time - a.time);
      return {
        position: lerpVec3(a.position, b.position, t),
        rotation: lerpVec3(a.rotation, b.rotation, t),
        scale: lerpVec3(a.scale, b.scale, t),
      };
    }
  }
  return null;
}

export default function PrevisCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const transformRef = useRef<TransformControls | null>(null);
  const meshMapRef = useRef<Map<string, THREE.Object3D>>(new Map());
  const clockRef = useRef<THREE.Clock>(new THREE.Clock());

  const objects = usePrevisStore((state) => state.objects);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const currentTime = usePrevisStore((state) => state.currentTime);
  const isPlaying = usePrevisStore((state) => state.isPlaying);
  const keyframes = usePrevisStore((state) => state.keyframes);
  const cameraKeyframes = usePrevisStore((state) => state.cameraKeyframes);
  const duration = usePrevisStore((state) => state.duration);
  const setCurrentTime = usePrevisStore((state) => state.setCurrentTime);
  const setIsPlaying = usePrevisStore((state) => state.setIsPlaying);
  const updateObject = usePrevisStore((state) => state.updateObject);

  const objectSignature = useMemo(
    () => objects.map((obj) => `${obj.id}:${obj.type}`).join("|"),
    [objects]
  );

  // 初始化 Three.js 场景
  useEffect(() => {
    if (!containerRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x222222);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.set(5, 4, 5);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controlsRef.current = controls;

    const transform = new TransformControls(camera, renderer.domElement);
    transform.addEventListener("change", () => renderer.render(scene, camera));
    transform.addEventListener("dragging-changed", (event) => {
      controls.enabled = !event.value;
    });
    transform.addEventListener("objectChange", () => {
      const obj = transform.object as THREE.Object3D | undefined;
      if (!obj) return;
      const id = obj.userData.objectId as string | undefined;
      if (!id) return;
      updateObject(id, {
        position: [obj.position.x, obj.position.y, obj.position.z],
        rotation: [obj.rotation.x, obj.rotation.y, obj.rotation.z],
        scale: [obj.scale.x, obj.scale.y, obj.scale.z],
      });
    });
    transformRef.current = transform;
    scene.add(transform);

    const grid = new THREE.GridHelper(10, 10, 0x888888, 0x444444);
    scene.add(grid);
    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5, 10, 5);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0xffffff, 0.3));

    let animationId = 0;
    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const delta = clockRef.current.getDelta();
      if (usePrevisStore.getState().isPlaying) {
        const next = usePrevisStore.getState().currentTime + delta;
        if (next >= usePrevisStore.getState().duration) {
          usePrevisStore.getState().setIsPlaying(false);
          usePrevisStore.getState().setCurrentTime(usePrevisStore.getState().duration);
        } else {
          usePrevisStore.getState().setCurrentTime(next);
        }
      }
      controls.update();
      cameraRef.position = [camera.position.x, camera.position.y, camera.position.z];
      cameraRef.target = [controls.target.x, controls.target.y, controls.target.z];
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", handleResize);
      transform.dispose();
      controls.dispose();
      renderer.dispose();
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement);
      }
      meshMapRef.current.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 根据对象列表增删网格
  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    const existing = meshMapRef.current;
    const nextIds = new Set(objects.map((obj) => obj.id));
    for (const [id, mesh] of existing.entries()) {
      if (!nextIds.has(id)) {
        scene.remove(mesh);
        existing.delete(id);
      }
    }

    for (const obj of objects) {
      let mesh = existing.get(obj.id);
      if (!mesh) {
        mesh = createMesh(obj.type);
        mesh.userData.objectId = obj.id;
        existing.set(obj.id, mesh);
        scene.add(mesh);
      }
      mesh.position.set(...obj.position);
      mesh.rotation.set(...obj.rotation);
      mesh.scale.set(...obj.scale);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [objectSignature]);

  // 选择对象时绑定 TransformControls
  useEffect(() => {
    const transform = transformRef.current;
    const scene = sceneRef.current;
    if (!transform || !scene) return;

    transform.detach();

    if (selectedObjectId) {
      const mesh = meshMapRef.current.get(selectedObjectId);
      if (mesh) {
        transform.attach(mesh);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedObjectId, objectSignature]);

  // 按时间轴插值对象变换
  useEffect(() => {
    for (const obj of objects) {
      const mesh = meshMapRef.current.get(obj.id);
      if (!mesh) continue;
      const frames = keyframes[obj.id] ?? [];
      const interpolated = interpolateTransform(frames, currentTime);
      if (interpolated) {
        mesh.position.set(...interpolated.position);
        mesh.rotation.set(...interpolated.rotation);
        mesh.scale.set(...interpolated.scale);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTime, keyframes, objectSignature]);

  // 按时间轴插值相机
  useEffect(() => {
    const camera = cameraRef.current;
    const controls = controlsRef.current;
    if (!camera || !controls || cameraKeyframes.length === 0) return;

    if (currentTime <= cameraKeyframes[0].time) {
      camera.position.set(...cameraKeyframes[0].position);
      controls.target.set(...cameraKeyframes[0].target);
    } else if (currentTime >= cameraKeyframes[cameraKeyframes.length - 1].time) {
      const last = cameraKeyframes[cameraKeyframes.length - 1];
      camera.position.set(...last.position);
      controls.target.set(...last.target);
    } else {
      for (let i = 0; i < cameraKeyframes.length - 1; i += 1) {
        const a = cameraKeyframes[i];
        const b = cameraKeyframes[i + 1];
        if (currentTime >= a.time && currentTime <= b.time) {
          const t = b.time === a.time ? 0 : (currentTime - a.time) / (b.time - a.time);
          camera.position.set(...lerpVec3(a.position, b.position, t));
          controls.target.set(...lerpVec3(a.target, b.target, t));
          break;
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTime, cameraKeyframes]);

  return <div ref={containerRef} style={{ width: "100%", height: 480 }} />;
}
