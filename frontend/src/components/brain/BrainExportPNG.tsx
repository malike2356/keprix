"use client";

import { toPng } from "html-to-image";
import type { Viewport } from "@xyflow/react";

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function triggerDownload(dataUrl: string, filename: string): void {
  const link = document.createElement("a");
  link.download = filename;
  link.href = dataUrl;
  link.click();
}

export async function exportBrainAsPNG(
  canvasElement: HTMLElement,
  filename = "brain-graph.png",
  options?: {
    fullGraph?: boolean;
    fitView?: () => void | Promise<void>;
    getViewport?: () => Viewport;
    setViewport?: (viewport: Viewport) => void;
  },
): Promise<void> {
  const previousViewport = options?.getViewport?.();
  if (options?.fullGraph && options.fitView) {
    await options.fitView();
    await sleep(100);
  }

  const dataUrl = await toPng(canvasElement, {
    backgroundColor: "var(--color-base, #0f172a)",
    pixelRatio: 2,
  });

  if (options?.fullGraph && previousViewport && options.setViewport) {
    options.setViewport(previousViewport);
  }

  triggerDownload(dataUrl, filename);
}
