"use client";

import React, { useEffect, useRef } from "react";
import { computeCanvasTransform, worldToCanvas } from "../lib/geometry";
import { ScenarioSpec, TelemetryFrame } from "../lib/types";

interface SimulationCanvasProps {
  scenario: ScenarioSpec | null;
  frames: TelemetryFrame[];
  currentFrameIndex: number;
}

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

    // Clear background
    ctx.fillStyle = "#0c1017";
    ctx.fillRect(0, 0, width, height);

    // Draw Warehouse Bounds
    const origin = worldToCanvas(0, scenario.world.height_m, scenario.world.height_m, transform);
    const wallWidth = scenario.world.width_m * transform.scale;
    const wallHeight = scenario.world.height_m * transform.scale;

    ctx.strokeStyle = "#30363d";
    ctx.lineWidth = 3;
    ctx.strokeRect(origin.px, origin.py, wallWidth, wallHeight);

    // Grid lines inside warehouse
    ctx.strokeStyle = "rgba(48, 54, 61, 0.4)";
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

    // Draw Goal
    const goalPos = worldToCanvas(scenario.robot.goal.x_m, scenario.robot.goal.y_m, scenario.world.height_m, transform);
    const goalRadiusPx = scenario.robot.goal_radius_m * transform.scale;

    ctx.fillStyle = "rgba(46, 160, 67, 0.25)";
    ctx.beginPath();
    ctx.arc(goalPos.px, goalPos.py, goalRadiusPx, 0, 2 * Math.PI);
    ctx.fill();
    ctx.strokeStyle = "#2ea043";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "#3fb950";
    ctx.font = "12px sans-serif";
    ctx.fillText("GOAL", goalPos.px - 16, goalPos.py + 4);

    // Draw Obstacle Trajectories
    scenario.obstacles.forEach((obs) => {
      const s = worldToCanvas(obs.start.x_m, obs.start.y_m, scenario.world.height_m, transform);
      const e = worldToCanvas(obs.end.x_m, obs.end.y_m, scenario.world.height_m, transform);
      ctx.strokeStyle = "rgba(248, 81, 73, 0.3)";
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(s.px, s.py);
      ctx.lineTo(e.px, e.py);
      ctx.stroke();
      ctx.setLineDash([]);
    });

    const activeFrame = frames[currentFrameIndex];

    // Draw Robot Path History
    if (frames.length > 0) {
      ctx.strokeStyle = "rgba(88, 166, 255, 0.5)";
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
      // Draw Current Obstacles
      activeFrame.obstacles.forEach((obs) => {
        const pos = worldToCanvas(obs.x_m, obs.y_m, scenario.world.height_m, transform);
        const radiusPx = obs.radius_m * transform.scale;

        ctx.fillStyle = "rgba(248, 81, 73, 0.4)";
        ctx.beginPath();
        ctx.arc(pos.px, pos.py, radiusPx, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = "#f85149";
        ctx.lineWidth = 2;
        ctx.stroke();
      });

      // Draw Robot Body
      const robotPos = worldToCanvas(activeFrame.robot.x_m, activeFrame.robot.y_m, scenario.world.height_m, transform);
      const robotRadiusPx = scenario.robot.body_radius_m * transform.scale;

      ctx.fillStyle = "#58a6ff";
      ctx.beginPath();
      ctx.arc(robotPos.px, robotPos.py, robotRadiusPx, 0, 2 * Math.PI);
      ctx.fill();
      ctx.strokeStyle = "#79c0ff";
      ctx.lineWidth = 2;
      ctx.stroke();

      // Heading indicator
      const yaw = activeFrame.robot.yaw_rad;
      const headPx = robotPos.px + robotRadiusPx * 1.5 * Math.cos(yaw);
      const headPy = robotPos.py - robotRadiusPx * 1.5 * Math.sin(yaw);

      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(robotPos.px, robotPos.py);
      ctx.lineTo(headPx, headPy);
      ctx.stroke();

      // Check if collision on this frame
      const isCollision = activeFrame.events.some((e) => e.type === "COLLISION");
      if (isCollision) {
        ctx.strokeStyle = "#f85149";
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(robotPos.px, robotPos.py, robotRadiusPx * 2.0, 0, 2 * Math.PI);
        ctx.stroke();

        ctx.fillStyle = "#ff7b72";
        ctx.font = "bold 14px sans-serif";
        ctx.fillText("COLLISION!", robotPos.px - 38, robotPos.py - robotRadiusPx - 8);
      }
    }
  }, [scenario, frames, currentFrameIndex]);

  return (
    <div className="canvas-container">
      <canvas
        id="simulation-canvas"
        ref={canvasRef}
        width={760}
        height={460}
        className="simulation-canvas"
      />
    </div>
  );
};
