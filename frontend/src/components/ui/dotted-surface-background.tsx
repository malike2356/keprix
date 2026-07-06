"use client";

import * as React from "react";
import * as THREE from "three";

const DEFAULT_TINT = { r: 108 / 255, g: 92 / 255, b: 231 / 255 };
const DEFAULT_FOG = 0x08080f;

type DottedSurfaceBackgroundProps = {
  className?: string;
  /** Pin to the viewport (full-page background). */
  fixed?: boolean;
  /** Particle tint (0-1 RGB). Defaults to Keprix primary purple. */
  tint?: { r: number; g: number; b: number };
  /** Fog and clear color. */
  fogColor?: number;
  particleOpacity?: number;
};

export function DottedSurfaceBackground({
  className,
  fixed = false,
  tint = DEFAULT_TINT,
  fogColor = DEFAULT_FOG,
  particleOpacity = 0.6,
}: DottedSurfaceBackgroundProps) {
  const mountRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const mobile = window.innerWidth <= 768;
    const SEPARATION = mobile ? 120 : 150;
    const AMOUNTX = mobile ? 28 : 40;
    const AMOUNTY = mobile ? 42 : 60;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(fogColor, 2000, 10000);

    const camera = new THREE.PerspectiveCamera(60, 1, 1, 10000);
    camera.position.set(0, 355, 1220);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(fogColor, 0);
    mount.appendChild(renderer.domElement);

    const positions: number[] = [];
    const colors: number[] = [];

    for (let ix = 0; ix < AMOUNTX; ix++) {
      for (let iy = 0; iy < AMOUNTY; iy++) {
        const x = ix * SEPARATION - (AMOUNTX * SEPARATION) / 2;
        const z = iy * SEPARATION - (AMOUNTY * SEPARATION) / 2;
        positions.push(x, 0, z);
        const mix = 0.55 + Math.random() * 0.45;
        colors.push(tint.r * mix, tint.g * mix, tint.b * mix);
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: mobile ? 6 : 8,
      vertexColors: true,
      transparent: true,
      opacity: particleOpacity,
      sizeAttenuation: true,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    let count = 0;
    let animationId = 0;
    let running = true;

    const resize = () => {
      const width = fixed ? window.innerWidth : mount.clientWidth || window.innerWidth;
      const height = fixed ? window.innerHeight : mount.clientHeight || window.innerHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    const animate = () => {
      if (!running) return;
      animationId = window.requestAnimationFrame(animate);

      const positionAttribute = geometry.attributes.position;
      const posArr = positionAttribute.array as Float32Array;
      let i = 0;

      for (let ix = 0; ix < AMOUNTX; ix++) {
        for (let iy = 0; iy < AMOUNTY; iy++) {
          const index = i * 3;
          posArr[index + 1] =
            Math.sin((ix + count) * 0.3) * 50 + Math.sin((iy + count) * 0.5) * 50;
          i++;
        }
      }

      positionAttribute.needsUpdate = true;
      renderer.render(scene, camera);
      count += 0.1;
    };

    const handleVisibility = () => {
      if (document.hidden) {
        running = false;
        window.cancelAnimationFrame(animationId);
      } else {
        running = true;
        animate();
      }
    };

    resize();
    animate();
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", handleVisibility);

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(mount);

    return () => {
      running = false;
      window.cancelAnimationFrame(animationId);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", handleVisibility);
      resizeObserver.disconnect();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [fixed, tint.r, tint.g, tint.b, fogColor, particleOpacity]);

  return (
    <div
      ref={mountRef}
      aria-hidden
      className={className}
      style={{
        position: fixed ? "fixed" : "absolute",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
        overflow: "hidden",
      }}
    />
  );
}
