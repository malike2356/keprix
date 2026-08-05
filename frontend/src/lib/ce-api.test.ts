import { describe, expect, it } from "vitest";
import { normalizePublicApiBase } from "./ce-api";

describe("ce api base", () => {
  it("ignores baked localhost API URLs on deployed hostnames", async () => {
    expect(
      normalizePublicApiBase("http://localhost:3333", {
        hostname: "hermes.verlox.uk",
        origin: "https://hermes.verlox.uk",
      }),
    ).toBe("");
  });

  it("keeps baked localhost API URLs for local development", async () => {
    expect(
      normalizePublicApiBase("http://localhost:3333", {
        hostname: "localhost",
        origin: "http://localhost:3000",
      }),
    ).toBe("http://localhost:3333");
  });
});
