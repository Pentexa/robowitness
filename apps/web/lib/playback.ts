import { TelemetryFrame } from "./types";

export interface PlaybackState {
  isPlaying: boolean;
  currentFrameIndex: number;
  speed: number; // 0.5, 1.0, 2.0
}

export function getFrameAtTime(frames: TelemetryFrame[], targetSimTime_s: number): number {
  if (frames.length === 0) return 0;
  for (let i = 0; i < frames.length; i++) {
    if (frames[i].sim_time_s >= targetSimTime_s) {
      return i;
    }
  }
  return frames.length - 1;
}
