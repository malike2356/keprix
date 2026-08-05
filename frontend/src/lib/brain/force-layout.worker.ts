import { runForceSimulation, type ForceLayoutPayload } from "@/lib/brain/layout-force-core";
import type { LayoutPositions } from "@/lib/brain/layout-types";

self.onmessage = (event: MessageEvent<ForceLayoutPayload>) => {
  const positions: LayoutPositions = runForceSimulation(event.data);
  self.postMessage(positions);
};
