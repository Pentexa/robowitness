"use client";

import React, { useEffect, useRef } from "react";
import { computeCanvasTransform, worldToCanvas } from "../lib/geometry";
import { ScenarioSpec, TelemetryFrame } from "../lib/types";

interface SimulationCanvasProps {
  scenario: ScenarioSpec | null;
  frames: TelemetryFrame[];
  currentFrameIndex: number;
}

const C_BG = "#090D16";
const C_GRID = "rgba(255,255,255,0.05)";
const C_WALL = "rgba(255,255,255,0.22)";
const C_GOAL = "rgba(255,255,255,0.75)";
const C_OBS = "#CBD5E1";
const C_ROBOT = "#00E5FF";
const C_ROBOT_EDGE = "#0891B2";
const C_HIT = "#FF3366";

export const SimulationCanvas: React.FC<SimulationCanvasProps> = ({
  scenario,
  frames,
  currentFrameIndex,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !scenario) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const transform = computeCanvasTransform(
      scenario.world.width_m,
      scenario.world.height_m,
      width,
      height
    );

    ctx.fillStyle = C_BG;
    ctx.fillRect(0, 0, width, height);

    const origin = worldToCanvas(0, scenario.world.height_m, scenario.world.height_m, transform);
    const wallW = scenario.world.width_m * transform.scale;
    const wallH = scenario.world.height_m * transform.scale;

    ctx.strokeStyle = C_WALL;
    ctx.lineWidth = 1.5;
    ctx.strokeRect(origin.px, origin.py, wallW, wallH);

    ctx.strokeStyle = C_GRID;
    ctx.lineWidth = 1;
    for (let x = 1; x < scenario.world.width_m; x++) {
      const p1 = worldToCanvas(x, 0, scenario.world.height_m, transform);
      const p2 = worldToCanvas(x, scenario.world.height_m, scenario.world.height_m, transform);
      ctx.beginPath();
      ctx.moveTo(p1.px, p1.py);
      ctx.lineTo(p2.px, p2.py);
      ctx.stroke();
    }
    for (let y = 1; y < scenario.world.height_m; y++) {
      const p1 = worldToCanvas(0, y, scenario.world.height_m, transform);
      const p2 = worldToCanvas(scenario.world.width_m, y, scenario.world.height_m, transform);
      ctx.beginPath();
      ctx.moveTo(p1.px, p1.py);
      ctx.lineTo(p2.px, p2.py);
      ctx.stroke();
    }

    const goalPos = worldToCanvas(scenario.robot.goal.x_m, scenario.robot.goal.y_m, scenario.world.height_m, transform);
    const goalRadiusPx = scenario.robot.goal_radius_m * transform.scale;
    ctx.strokeStyle = C_GOAL;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 5]);
    ctx.beginPath();
    ctx.arc(goalPos.px, goalPos.py, goalRadiusPx, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(148,163,184,0.9)";
    ctx.font = "600 11px 'JetBrains Mono', monospace";
    ctx.fillText("GOAL", goalPos.px - 15, goalPos.py + 4);

    scenario.obstacles.forEach((obs) => {
      const s = worldToCanvas(obs.start.x_m, obs.start.y_m, scenario.world.height_m, transform);
      const e = worldToCanvas(obs.end.x_m, obs.end.y_m, scenario.world.height_m, transform);
      ctx.strokeStyle = "rgba(148,163,184,0.4)";
      ctx.setLineDash([3, 5]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(s.px, s.py);
      ctx.lineTo(e.px, e.py);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    const activeFrame = frames[currentFrameIndex];

    if (frames.length > 0) {
      ctx.strokeStyle = "rgba(0,229,255,0.55)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i <= currentFrameIndex && i < frames.length; i++) {
        const pt = worldToCanvas(frames[i].robot.x_m, frames[i].robot.y_m, scenario.world.height_m, transform);
        if (i === 0) ctx.moveTo(pt.px, pt.py);
        else ctx.lineTo(pt.px, pt.py);
      }
      ctx.stroke();
    }

    if (activeFrame) {
      activeFrame.obstacles.forEach((obs) => {
        const pos = worldToCanvas(obs.x_m, obs.y_m, scenario.world.height_m, transform);
        const radiusPx = obs.radius_m * transform.scale;
        ctx.fillStyle = C_OBS;
        ctx.beginPath();
        ctx.arc(pos.px, pos.py, radiusPx, 0, 2 * Math.PI);
        ctx.fill();
      });

      const robotPos = worldToCanvas(activeFrame.robot.x_m, activeFrame.robot.y_m, scenario.world.height_m, transform);
      const robotRadiusPx = scenario.robot.body_radius_m * transform.scale;

      ctx.fillStyle = C_ROBOT;
      ctx.beginPath();
      ctx.arc(robotPos.px, robotPos.py, robotRadiusPx, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = C_ROBOT_EDGE;
      ctx.lineWidth = 2;
      ctx.stroke();

      const yaw = activeFrame.robot.yaw_rad;
      ctx.strokeStyle = "#FFFFFF";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(robotPos.px, robotPos.py);
      ctx.lineTo(
        robotPos.px + robotRadiusPx * 1.4 * Math.cos(yaw),
        robotPos.py - robotRadiusPx * 1.4 * Math.sin(yaw)
      );
      ctx.stroke();

      const isCollision = activeFrame.events.some((e) => e.type === "COLLISION");
      if (isCollision) {
        ctx.strokeStyle = C_HIT;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(robotPos.px, robotPos.py, robotRadiusPx * 1.9, 0, 2 * Math.PI);
        ctx.stroke();
        ctx.fillStyle = C_HIT;
        ctx.font = "700 13px 'JetBrains Mono', monospace";
        ctx.fillText("COLLISION", robotPos.px - 36, robotPos.py - robotRadiusPx - 10);
      }
    }
  }, [scenario, frames, currentFrameIndex]);

  return (
    <div className="rw-canvas-wrap">
      <canvas
        id="simulation-canvas"
        ref={canvasRef}
        width={760}
        height={460}
      />
    </div>
  );
};
