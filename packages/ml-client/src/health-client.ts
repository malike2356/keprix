import { MLServiceClientBase } from "./base-client";
import type { MLServiceHealth } from "./types";

export class HealthClient extends MLServiceClientBase {
  async health(): Promise<MLServiceHealth> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) {
      throw new Error(`ML service health error ${response.status}`);
    }
    return response.json() as Promise<MLServiceHealth>;
  }
}
