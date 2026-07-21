"""E2E 데모: 샘플 사진으로 업로드→집필→(선택)주문까지 로컬 API를 순서대로 호출.
실행: cd backend; python scripts/demo_e2e.py [--order]
사전조건: uvicorn 실행 중, .env에 실키."""
import io, sys, time
import httpx
from PIL import Image

BASE = "http://localhost:8000/api/v1"


def jpg(color):
    buf = io.BytesIO(); Image.new("RGB", (1200, 900), color).save(buf, "JPEG")
    return buf.getvalue()


def main(order: bool):
    c = httpx.Client(timeout=300)
    pid = c.post(f"{BASE}/projects", json={"title": "데모 여행", "mood": "comedy",
                                           "companions": "친구들"}).json()["id"]
    print("project:", pid)
    photos = c.post(f"{BASE}/projects/{pid}/photos", files=[
        ("files", ("a.jpg", jpg("red"), "image/jpeg")),
        ("files", ("b.jpg", jpg("blue"), "image/jpeg")),
    ]).json()["photos"]
    for i, p in enumerate(photos):
        c.patch(f"{BASE}/photos/{p['id']}", json={"emotion": "신남", "note": f"{i+1}번째 장소, 정말 재밌었다"})
    print("사진 분석 대기...")
    while any(x["analysis_status"] == "pending"
              for x in c.get(f"{BASE}/projects/{pid}/photos/analysis").json()["photos"]):
        time.sleep(2)
    c.post(f"{BASE}/projects/{pid}/write")
    print("집필 스트림 수신:")
    with c.stream("GET", f"{BASE}/projects/{pid}/write/stream") as res:
        for line in res.iter_lines():
            if line.startswith("data:"):
                print(" ", line[:110])
                if '"done"' in line or '"error"' in line:
                    break
    if order:
        res = c.post(f"{BASE}/projects/{pid}/order", json={
            "spec": {"bookSpecUid": "REPLACE_ME"},
            "shipping": {"name": "데모", "phone": "010-0000-0000", "address": "서울"}})
        print("order:", res.json())
    print("완료. 프로젝트:", f"http://localhost:5173/p/{pid}/review")


if __name__ == "__main__":
    main("--order" in sys.argv)
