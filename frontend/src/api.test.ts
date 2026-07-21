import { describe, it, expect, vi, beforeEach } from "vitest";
import { createProject, uploadAudio } from "./api";

describe("api v2", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 201, json: async () => ({ id: "p1" }) })));
  });
  it("createProject posts title without mood", async () => {
    const res = await createProject({ title: "제주" });
    expect(res.id).toBe("p1");
    const [url, init] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/projects");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).not.toHaveProperty("mood");
  });
  it("uploadAudio posts multipart to moments/{id}/audio", async () => {
    const blob = new Blob(["x"], { type: "audio/m4a" });
    await uploadAudio("m1", blob);
    const [url, init] = (fetch as any).mock.calls[0];
    expect(url).toContain("/api/v1/moments/m1/audio");
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
  });
});
