"use client";
import * as React from "react";

const GRADIENT_ANGLES = { top: 0, right: 90, bottom: 180, left: 270 } as const;

type ProgressiveBlurProps = {
  direction?: keyof typeof GRADIENT_ANGLES;
  blurLayers?: number;
  blurIntensity?: number;
  style?: React.CSSProperties;
};

export function ProgressiveBlur({
  direction = "bottom",
  blurLayers = 8,
  blurIntensity = 0.25,
  style,
}: ProgressiveBlurProps) {
  const layers = Math.max(blurLayers, 2);
  const segmentSize = 1 / (layers + 1);

  return (
    <div style={{ position: "relative", pointerEvents: "none", ...style }}>
      {Array.from({ length: layers }).map((_, index) => {
        const angle = GRADIENT_ANGLES[direction];
        const stops = [
          index * segmentSize,
          (index + 1) * segmentSize,
          (index + 2) * segmentSize,
          (index + 3) * segmentSize,
        ]
          .map(
            (pos, pi) =>
              `rgba(255,255,255,${pi === 1 || pi === 2 ? 1 : 0}) ${(pos * 100).toFixed(1)}%`
          )
          .join(", ");
        const gradient = `linear-gradient(${angle}deg, ${stops})`;

        return (
          <div
            key={index}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              maskImage: gradient,
              WebkitMaskImage: gradient,
              backdropFilter: `blur(${index * blurIntensity}px)`,
            }}
          />
        );
      })}
    </div>
  );
}
