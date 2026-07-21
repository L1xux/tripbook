import { describe, it, expect, vi, beforeEach } from "vitest";
import { createProject } from "./api";

describe("api client", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, status: 201, json: async () => ({ id: "p1" }),
    })));
  });
  it("createProject posts and returns id", async () => {
    const res = await createProject({ title: "제주", mood: "comedy" });
    expect(res.id).toBe("p1");
    const [url, init] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/projects");
    expect(init.method).toBe("POST");
  });
});
