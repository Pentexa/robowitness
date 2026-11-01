import type { Pose2D } from "./types";

export interface CanvasTransform {
  scale: number;
  offsetX: number;
  offsetY: number;
  canvasWidth: number;
  canvasHeight: number;
}

export function computeCanvasTransform(
  worldWidth_m: number,
  worldHeight_m: number,
  canvasWidth: number,
  canvasHeight: number,
  paddingPx = 30
): CanvasTransform {
  const availableWidth = canvasWidth - 2 * paddingPx;
  const availableHeight = canvasHeight - 2 * paddingPx;

  const scaleX = availableWidth / worldWidth_m;
  const scaleY = availableHeight / worldHeight_m;
  const scale = Math.min(scaleX, scaleY);

  const drawWidth = worldWidth_m * scale;
  const drawHeight = worldHeight_m * scale;

  const offsetX = (canvasWidth - drawWidth) / 2;
  const offsetY = (canvasHeight - drawHeight) / 2;

  return { scale, offsetX, offsetY, canvasWidth, canvasHeight };
}

export function worldToCanvas(
  x_m: number,
  y_m: number,
  worldHeight_m: number,
  transform: CanvasTransform
): { px: number; py: number } {
  const px = transform.offsetX + x_m * transform.scale;
  const py = transform.offsetY + (worldHeight_m - y_m) * transform.scale;
  return { px, py };
}
