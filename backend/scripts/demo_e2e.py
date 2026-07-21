"""E2E 데모(v2): 프로젝트 생성→사진 업로드→음성 업로드(캡션)→수령인→주문.
실행: cd backend; python scripts/demo_e2e.py [--order]
사전조건: uvicorn 실행, .env에 실키."""
import io, sys, time
import httpx
from PIL import Image

BASE = "http://localhost:8000/api/v1"


def jpg(color):
    buf = io.BytesIO(); Image.new("RGB", (1200, 900), color).save(buf, "JPEG"); return buf.getvalue()


def main(order: bool):
    c = httpx.Client(timeout=300)
    pid = c.post(f"{BASE}/projects", json={"title": "제주, 봄", "companions": "엄마"}).json()["id"]
    print("project:", pid)
    photos = c.post(f"{BASE}/projects/{pid}/photos", files=[
        ("files", ("a.jpg", jpg("navy"), "image/jpeg")),
        ("files", ("b.jpg", jpg("orange"), "image/jpeg")),
    ]).json()["photos"]
    for m in photos:
        # 실제 음성 파일이 있으면 그것을 사용. 데모는 짧은 더미 바이트.
        c.post(f"{BASE}/moments/{m['id']}/audio", files=[("file", ("v.m4a", b"DUMMYAUDIO", "audio/m4a"))])
    print("캡션 생성 대기…")
    for _ in range(30):
        st = c.get(f"{BASE}/projects/{pid}/photos/analysis").json()["photos"]
        if all(x["analysis_status"] in ("done", "failed") for x in st):
            break
        time.sleep(2)
    for x in c.get(f"{BASE}/projects/{pid}/photos/analysis").json()["photos"]:
        print("  캡션:", x["caption"])
    if order:
        c.post(f"{BASE}/projects/{pid}/recipients", json={"name": "엄마", "address": "서울"})
        res = c.post(f"{BASE}/projects/{pid}/order", json={
            "spec": {"bookSpecUid": "REPLACE_ME"},
            "shipping": {"name": "나", "phone": "010-0000-0000", "address": "부산"}})
        print("order:", res.json())
    print("완료:", f"http://localhost:5173/ (프로젝트 {pid})")


if __name__ == "__main__":
    main("--order" in sys.argv)
