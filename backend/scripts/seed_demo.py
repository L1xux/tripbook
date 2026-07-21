"""로컬 테스트용 데모 여행 시드. / 개발자가 직접 실행. / 실행 중인 uvicorn(:8000)의 DB에 채운다.
사진·글귀·감정·재생 가능한 음성·감정 아크·주문 현황까지 넣어 브라우저에서 전 화면을 눌러볼 수 있게 한다.
실행: (uvicorn 켜둔 상태) cd backend; python scripts/seed_demo.py   (AI/실키 불필요 — 값은 직접 세팅)"""
import io, os, sys, wave, struct, math, httpx
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from PIL import Image

BASE = "http://localhost:8000/api/v1"

SCENES = [
    ((244, 162, 79), (46, 63, 102), "평온", "바다가 생각보다 훨씬 파랬다.\n한참을 그냥 서 있었어."),
    ((227, 192, 146), (79, 61, 48), "설렘", "골목 끝에서 길을 잃었는데,\n그게 제일 좋았어."),
    ((199, 219, 151), (66, 99, 44), "신남", "돌담 사이로 유채가 끝없이.\n소리 지를 뻔했어."),
    ((239, 166, 192), (51, 37, 69), "뭉클", "노을 보다가 엄마가 조용해졌다.\n나도 조용해졌다."),
]


def _grad(top, bot, w=1000, h=1250):
    img = Image.new("RGB", (w, h)); px = img.load()
    for y in range(h):
        t = y / h
        col = tuple(int(top[i] * (1 - t) + bot[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = col
    b = io.BytesIO(); img.save(b, "JPEG", quality=88); return b.getvalue()


def _make_wav(path, secs=3.2, rate=16000):
    n = int(secs * rate)
    with wave.open(path, "w") as wv:
        wv.setnchannels(1); wv.setsampwidth(2); wv.setframerate(rate)
        fr = bytearray()
        for i in range(n):
            t = i / rate
            env = abs(math.sin(t * 3.0)) * (0.35 + 0.65 * abs(math.sin(t * 13)))  # 말하는 듯한 진폭
            fr += struct.pack("<h", int(env * math.sin(2 * math.pi * 185 * t) * 0.7 * 32767))
        wv.writeframes(fr)


def main():
    c = httpx.Client(timeout=60)
    pid = c.post(f"{BASE}/projects", json={
        "title": "제주, 봄", "companions": "엄마",
        "start_date": "2025.04.12", "end_date": "2025.04.14", "cover_line": "우리의 첫 봄"}).json()["id"]
    photos = c.post(f"{BASE}/projects/{pid}/photos",
                    files=[("files", (f"s{i}.jpg", _grad(t, b), "image/jpeg")) for i, (t, b, _, _) in enumerate(SCENES)]).json()["photos"]
    for m, (_, _, emo, cap) in zip(photos, SCENES):
        c.patch(f"{BASE}/moments/{m['id']}", json={"caption": cap, "emotion": emo})

    # 재생 가능한 음성(첫 순간) + 감정 아크 + 주문 현황은 API에 없으니 DB에 직접 세팅
    import app.db as db_module
    from app.models import Photo, Project, Recipient
    adir = f"data/audio/{pid}"; os.makedirs(adir, exist_ok=True)
    wav = os.path.abspath(f"{adir}/{photos[0]['id']}.wav"); _make_wav(wav)
    with db_module.SessionLocal() as db:
        for m in photos:  # 캡션이 캡처 화면에서도 보이도록 분석 완료 상태로
            db.get(Photo, m["id"]).analysis_status = "done"
        ph = db.get(Photo, photos[0]["id"])
        ph.audio_path = wav; ph.transcript = SCENES[0][3].replace("\n", " ")
        pr = db.get(Project, pid)
        pr.emotion_arc = "잔잔한 바다에서 시작해, 골목과 유채밭을 지나 노을 앞에서 뭉클했던 여행. 그때의 마음이 아직 선명하다."
        pr.order_status = "PRINTING"; pr.status = "ordered"
        db.add(Recipient(project_id=pid, name="엄마", address="서울시 강남구", phone="010-1111-2222",
                         postal_code="06000", order_status="SHIPPING"))
        db.commit()

    print("\n데모 여행 준비 완료! 브라우저에서 열어보세요:")
    print(f"  앨범(덱·글귀·파형·그리드·책·주문현황): http://localhost:5173/p/{pid}")
    print(f"  여행 중 순간 담기:                    http://localhost:5173/p/{pid}/add")
    print(f"  공개 재생 페이지(QR 목적지):          http://localhost:5173/v/{photos[0]['id']}")


if __name__ == "__main__":
    main()
