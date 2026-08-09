import { describe, expect, it } from "vitest";
import { classifyVaultError } from "@/lib/document-vault-api";
import { errorCopy } from "@/components/document-vault/DocumentVaultExplorer";

describe("document vault error classification", () => {
  it("classifies offline, quota, conflict, conversion, and forbidden", () => {
    expect(classifyVaultError(Object.assign(new Error("failed to fetch"), { status: 0 }))).toBe(
      "offline",
    );
    expect(classifyVaultError(Object.assign(new Error("quota"), { code: "quota_exceeded" }))).toBe(
      "quota",
    );
    expect(classifyVaultError(Object.assign(new Error("stale"), { status: 409 }))).toBe("conflict");
    expect(
      classifyVaultError(Object.assign(new Error("bad format"), { code: "unsupported_kind" })),
    ).toBe("conversion");
    expect(
      classifyVaultError(Object.assign(new Error("blocked"), { code: "host_fs_forbidden", status: 403 })),
    ).toBe("forbidden");
  });

  it("exposes UI copy for each failure state", () => {
    for (const state of ["offline", "empty", "loading", "quota", "conflict", "conversion"] as const) {
      const copy = errorCopy(state);
      expect(copy.title.length).toBeGreaterThan(0);
      expect(copy.body.length).toBeGreaterThan(0);
    }
  });
});
