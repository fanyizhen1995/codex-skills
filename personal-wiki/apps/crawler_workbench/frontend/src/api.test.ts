import { describe, expect, it } from "vitest";

import { resolveApiBase } from "./api";

describe("resolveApiBase", () => {
  it("defaults to /api when no environment value is configured", () => {
    expect(resolveApiBase()).toBe("/api");
  });

  it("adds /api to an origin value", () => {
    expect(resolveApiBase("http://localhost:8765")).toBe("http://localhost:8765/api");
  });

  it("does not duplicate /api when already present", () => {
    expect(resolveApiBase("http://localhost:8765/api")).toBe("http://localhost:8765/api");
  });

  it("preserves an explicit /api base path", () => {
    expect(resolveApiBase("/api")).toBe("/api");
  });
});
