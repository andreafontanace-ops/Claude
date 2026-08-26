import React from "react";
import { interpolate } from "remotion";
import { Camera, project } from "./useCamera";
import { Waypoint } from "./geoData";

export const ArrivalPulse: React.FC<{
  waypoint: Waypoint;
  camera: Camera;
  frame: number;
  triggerFrame: number;
}> = ({ waypoint, camera, frame, triggerFrame }) => {
  const { left, top } = project(camera, waypoint.x, waypoint.y);
  const t = frame - triggerFrame;
  if (t < 0 || t > 40) return null;

  return (
    <>
      {[0, 12, 24].map((delay) => {
        const local = t - delay;
        if (local < 0) return null;
        const scale = interpolate(local, [0, 34], [0.2, 2.6], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const opacity = interpolate(local, [0, 34], [0.6, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={delay}
            style={{
              position: "absolute",
              left,
              top,
              width: 30,
              height: 30,
              borderRadius: "50%",
              border: "2.5px solid #c0392b",
              transform: `translate(-50%, -50%) scale(${scale})`,
              opacity,
            }}
          />
        );
      })}
    </>
  );
};
