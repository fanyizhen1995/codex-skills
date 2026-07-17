import { describe, expect, it } from "vitest";

describe("Vite remote access configuration", () => {
  it("allows the trusted project Tailnet hostname", async () => {
    const configModulePath = "../vite.config";
    const { default: viteConfig } = await import(configModulePath);
    const config = viteConfig as {
      server?: { allowedHosts?: string[] | true };
    };

    expect(config.server?.allowedHosts).toContain(
      "spark-8c85.tail04bc15.ts.net"
    );
  });
});
