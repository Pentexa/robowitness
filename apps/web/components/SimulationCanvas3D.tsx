"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { ScenarioSpec, TelemetryFrame } from "../lib/types";

interface SimulationCanvas3DProps {
  scenario: ScenarioSpec | null;
  frames: TelemetryFrame[];
  currentFrameIndex: number;
}

const VIEW_W = 800;
const VIEW_H = 500;

/** 3D viewer of the SAME 2D-planar simulation truth: x->X, y->Z, fixed heights.
 *  Pure visualization — physics, oracle and evidence still come from the
 *  authoritative 2D telemetry. Heights mirror the PyBullet collider setup
 *  (robot body 0.3 m, obstacles 0.5 m, walls 0.6 m). */
export const SimulationCanvas3D: React.FC<SimulationCanvas3DProps> = ({
  scenario,
  frames,
  currentFrameIndex,
}) => {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const sceneRef = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    camera: THREE.PerspectiveCamera;
    robot: THREE.Group;
    obstacles: Map<string, THREE.Mesh>;
    trail: THREE.Line | null;
    collisionMark: THREE.Mesh | null;
  } | null>(null);
  const [failed, setFailed] = React.useState<boolean>(false);

  // Build static scene once per scenario
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !scenario) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true });
    } catch {
      setFailed(true);
      return;
    }
    renderer.setSize(VIEW_W, VIEW_H);
    mount.innerHTML = "";
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d16);

    const W = scenario.world.width_m;
    const H = scenario.world.height_m;
    const camera = new THREE.PerspectiveCamera(50, VIEW_W / VIEW_H, 0.1, 200);
    camera.position.set(W / 2, Math.max(W, H) * 1.05, H / 2 + Math.max(W, H) * 0.75);
    camera.lookAt(W / 2, 0, H / 2);

    scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4);
    sun.position.set(W / 2 + 6, 12, H / 2 - 4);
    scene.add(sun);

    // Floor
    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(W, H),
      new THREE.MeshStandardMaterial({ color: 0x0d131f })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(W / 2, 0, H / 2);
    scene.add(floor);
    const grid = new THREE.GridHelper(Math.max(W, H), Math.max(W, H), 0x2a3a52, 0x161f30);
    grid.position.set(W / 2, 0.01, H / 2);
    grid.scale.z = H / Math.max(W, H);
    grid.scale.x = W / Math.max(W, H);
    scene.add(grid);

    // Walls
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x1a2436 });
    const mkWall = (w: number, d: number, x: number, z: number) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(w, 0.6, d), wallMat);
      m.position.set(x, 0.3, z);
      scene.add(m);
    };
    mkWall(W + 0.4, 0.2, W / 2, -0.1);
    mkWall(W + 0.4, 0.2, W / 2, H + 0.1);
    mkWall(0.2, H + 0.4, -0.1, H / 2);
    mkWall(0.2, H + 0.4, W + 0.1, H / 2);

    // Goal ring
    const goal = new THREE.Mesh(
      new THREE.RingGeometry(
        Math.max(0.05, scenario.robot.goal_radius_m - 0.06),
        scenario.robot.goal_radius_m,
        48
      ),
      new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide })
    );
    goal.rotation.x = -Math.PI / 2;
    goal.position.set(scenario.robot.goal.x_m, 0.02, scenario.robot.goal.y_m);
    scene.add(goal);

    // Robot group: body cylinder + heading arrow
    const robot = new THREE.Group();
    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(scenario.robot.body_radius_m, scenario.robot.body_radius_m, 0.3, 32),
      new THREE.MeshStandardMaterial({ color: 0x00e5ff })
    );
    body.position.y = 0.15;
    robot.add(body);
    const arrow = new THREE.Mesh(
      new THREE.ConeGeometry(0.09, 0.28, 16),
      new THREE.MeshStandardMaterial({ color: 0xffffff })
    );
    arrow.rotation.z = -Math.PI / 2;
    arrow.position.set(scenario.robot.body_radius_m + 0.12, 0.15, 0);
    robot.add(arrow);
    const axle = new THREE.Mesh(
      new THREE.BoxGeometry(0.08, 0.06, scenario.robot.body_radius_m * 1.7),
      new THREE.MeshStandardMaterial({ color: 0x090d16 })
    );
    axle.position.y = 0.15;
    robot.add(axle);
    scene.add(robot);

    sceneRef.current = {
      renderer,
      scene,
      camera,
      robot,
      obstacles: new Map(),
      trail: null,
      collisionMark: null,
    };
    return () => {
      renderer.dispose();
      mount.innerHTML = "";
      sceneRef.current = null;
    };
  }, [scenario]);

  // Update dynamic objects per frame
  useEffect(() => {
    const s = sceneRef.current;
    if (!s || !scenario || frames.length === 0) return;
    const frame = frames[Math.min(currentFrameIndex, frames.length - 1)];

    s.robot.position.set(frame.robot.x_m, 0, frame.robot.y_m);
    s.robot.rotation.y = -frame.robot.yaw_rad;

    // Obstacles: create/update, drop vanished
    const seen = new Set<string>();
    for (const o of frame.obstacles) {
      seen.add(o.id);
      let mesh = s.obstacles.get(o.id);
      if (!mesh) {
        mesh = new THREE.Mesh(
          new THREE.CylinderGeometry(o.radius_m, o.radius_m, 0.5, 28),
          new THREE.MeshStandardMaterial({ color: 0xcbd5e1 })
        );
        s.obstacles.set(o.id, mesh);
        s.scene.add(mesh);
      }
      mesh.position.set(o.x_m, 0.25, o.y_m);
    }
    const stale: Array<[string, THREE.Mesh]> = [];
    s.obstacles.forEach((mesh, id) => {
      if (!seen.has(id)) stale.push([id, mesh]);
    });
    for (const [id, mesh] of stale) {
      s.scene.remove(mesh);
      s.obstacles.delete(id);
    }

    // Trail of robot path up to current frame
    if (s.trail) {
      s.scene.remove(s.trail);
      (s.trail.geometry as THREE.BufferGeometry).dispose();
      s.trail = null;
    }
    if (currentFrameIndex > 0) {
      const pts: THREE.Vector3[] = [];
      const step = Math.max(1, Math.floor(currentFrameIndex / 400));
      for (let i = 0; i <= currentFrameIndex; i += step) {
        const f = frames[i];
        pts.push(new THREE.Vector3(f.robot.x_m, 0.03, f.robot.y_m));
      }
      const geo = new THREE.BufferGeometry().setFromPoints(pts);
      s.trail = new THREE.Line(
        geo,
        new THREE.LineBasicMaterial({ color: 0x00e5ff })
      );
      s.scene.add(s.trail);
    }

    // Collision marker at first recorded contact at/before current frame
    if (s.collisionMark) {
      s.scene.remove(s.collisionMark);
      s.collisionMark = null;
    }
    for (let i = 0; i <= currentFrameIndex; i++) {
      const hit = frames[i].events.find((e) => e.type === "COLLISION");
      if (hit) {
        const mark = new THREE.Mesh(
          new THREE.SphereGeometry(0.16, 16, 16),
          new THREE.MeshBasicMaterial({ color: 0xff3366 })
        );
        mark.position.set(frames[i].robot.x_m, 0.35, frames[i].robot.y_m);
        s.scene.add(mark);
        s.collisionMark = mark;
        break;
      }
    }

    s.renderer.render(s.scene, s.camera);
  }, [scenario, frames, currentFrameIndex]);

  if (failed) {
    return <p className="rw-err">3D unavailable (no WebGL) — use 2D view.</p>;
  }
  return (
    <div
      ref={mountRef}
      style={{ width: "100%", aspectRatio: `${VIEW_W} / ${VIEW_H}` }}
    />
  );
};
