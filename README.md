# CSW Chiqindi CRM

Yuridik shaxslardan chiqindi olib ketish arizalarini boshqarish tizimi: call-center, yuridik bo'lim, GPS xodimi, haydovchi plansheti va statistika.

Monorepo:

| Papka | Stek |
| --- | --- |
| `backend/` | Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, MySQL 8, JWT (httpOnly cookie), python-socketio, MinIO |
| `frontend/` | React 18 + TypeScript (Vite), Material UI, Redux Toolkit, React-Router, Axios, Socket.IO-client, SweetAlert2 |

## Hozirgi holat — 1-bosqich: haydovchi moduli

- Login + parol (bcrypt, 5 xato urinishdan keyin 15 daqiqaga bloklanadi), access 15 daqiqa / refresh 7 kun.
- **Smena:** GPS xodimi haydovchini o'z tumanidagi bo'sh mashina bilan juftlab smena ochadi; haydovchi mashina rasmi, spidometr va yoqilg'i bilan boshlaydi va yopadi.
- **Avtonaryad:** `BTE-2026-00001` — xizmat ko'rsatuvchi kodi, yil, tartib raqami (har kompaniya alohida).
- **Dalolatnoma (14 maydon):** oldin/keyin rasm (GPS bilan), sana, davlat raqami, haydovchi, avtonaryad, shartnoma, INN — avtomatik; konteyner, hajm, izoh, imzo, yuz rasmi — haydovchi kiritadi. Hammasi serverda tekshiriladi.
- **GPS radiusi** (100–300 m, standart 300): tashqarida yopilgan ariza `suspect` bo'ladi.
- **Bajarib bo'lmadi:** ariza `failed` holatida ochiq qoladi (Manager nazorati).
- **Jonli yangilanish:** `request:updated`, `driver:location` (Socket.IO).
- Internet yo'q bo'lsa yuborish bloklanadi (to'liq oflayn rejim — keyingi bosqich).

## 2-bosqich: korxonalar bazasi va Excel import

- **Korxonalar** (`/admin#customers`): qidiruv (nom kirill/lotin, STIR, telefon), filtrlar, karta, aloqa raqamlari, shartnomalar.
  Ko'rish — admin, manager, yurist, GPS (o'z tumani); tahrirlash va shartnoma — admin, yurist; koordinata tasdig'i — admin, manager.
- **Fayldan import** (`customers.import` ruxsati): call-center jadvali — .xlsx, .xls, .csv (UTF-8 yoki Windows-1251), .docx (jadval), matnli .pdf.
  Skanerlangan PDF uchun OCR keyingi bosqichda. Avval tahlil (bazaga yozilmaydi), keyin import. Viloyat/tuman yozuvlari
  normallashtiriladi, bir korxonaning takror qatorlari birlashadi, barcha telefonlar saqlanadi; qayta import xavfsiz.
  Buyurtmalar tarixi import qilinmaydi. Namunalar (sun'iy ma'lumot): `docs/samples/call-center-namuna.{xlsx,csv,docx,pdf}`.
- **Biriktirish sharti:** korxonada STIR va amaldagi shartnoma bo'lmasa haydovchi biriktirilmaydi (`customer_incomplete`).
- **Koordinata:** importdagi korxonada yo'q → birinchi tashrifda haydovchi dalolatnoma yopgan nuqta olinadi (radius tekshirilmaydi) →
  Manager tasdiqlaydi → keyingi tashriflar shu nuqta bo'yicha tekshiriladi.
- Yangi xizmat turi: **assenizator** (`septic`).

## Vaziyat paneli (admin va manager)

- `/admin#situation` va navbardagi qo'ng'iroqcha: o'qilmagan hodisalar soni, yangi hodisa kelganda popup (Socket.IO `situation:new`).
- Serverda saqlanadigan hodisalar (90 kun): akkaunt bloklandi, shubhali dalolatnoma, bajarib bo'lmadi, koordinata tasdig'i,
  Excel import, xodim/tuman/mashina faolsizlantirildi yoki faollashtirildi, parol tiklandi, GPS radiusi o'zgardi.
- "Shu sessiyadagi xabarlar": ekranda chiqqan barcha popuplar (forma xatolari ham), sahifa yangilanguncha.
- O'qilganlik har bir xodim uchun alohida.

## Jonli demo (Render, bepul)

`render.yaml` + `Dockerfile.demo`: bitta konteynerda frontend va backend, SQLite, fayllar xotirada.
Har push'da avtomatik qayta deploy bo'ladi; har qayta ishga tushishda baza boshlang'ich holatga qaytadi.

1. https://render.com → **GitHub bilan kirish** (karta shart emas)
2. **New → Blueprint** → `uzsaltmine-dev/csw-crm` → **Apply**
3. Havola: `https://csw-crm-demo.onrender.com` (yoki Render bergan nom)

Demo loginlar (parol `demo1234`): GPS xodimi `gps4`, haydovchi `driver41` (ikkalasi Asaka tumani), `admin`, `manager`, yurist `legal`.
Tavsiya: GPS xodimini kompyuterda, haydovchini telefon/planshetda oching.
Demo serverda (`TAB_SESSIONS=true`) bitta brauzerning har tabida boshqa rolda kirish mumkin; tab sarlavhasida rol va ism turadi.
Yangi tab ochib manzilni qo'lda kiriting (tabni "Dublikat" qilsangiz, sessiya ham nusxalanadi). Prod'da bu rejim o'chiq — httpOnly cookie.

Bepul reja cheklovlari: 15 daqiqa kirilmasa uxlaydi, keyingi ochilish ~1 daqiqa.
Namuna korxonalar Asakada joylashgan — boshqa joydan yakunlangan ariza haqli ravishda `Shubhali` (radiusdan tashqarida) bo'ladi.

## Lokal ishga tushirish (Docker)

```bash
cp .env.example .env          # parollarni almashtiring
docker compose up -d --build
docker compose exec api python -m app.seed   # boshlang'ich ma'lumotlar, parol: SEED_PASSWORD yoki ChangeMe123!
```

- Frontend: http://localhost:8080 — haydovchi `driver41` (Asaka tumani), GPS xodimi `gps4`
- API hujjati (Swagger): http://localhost:8000/docs
- MinIO konsoli: http://localhost:9001
- MySQL (DBeaver): `localhost:3306`, `.env` dagi foydalanuvchi

## Docker'siz ishlab chiqish

```bash
# backend
cd backend
pipenv install --dev
export DATABASE_URL=sqlite+aiosqlite:///./dev.db STORAGE_BACKEND=memory   # MySQL/MinIO'siz tezkor variant
pipenv run alembic upgrade head && pipenv run python -m app.seed
pipenv run uvicorn app.main:asgi_app --reload

# frontend (boshqa terminalda) — /api va /socket.io avtomatik :8000 ga proksi qilinadi
cd frontend
yarn && yarn dev              # http://localhost:5173
```

## Testlar

```bash
cd backend && pipenv run pytest      # 19 test: auth, smena qoidalari, avtonaryad, to'liq haydovchi oqimi
cd frontend && yarn build            # tsc typecheck + build
```

## Arxitektura (backend)

```
app/api/v1/*        router (controller) — HTTP, validatsiya, Depends orqali DI
app/services/*      biznes qoidalari (smena, biriktirish, dalolatnoma, avtonaryad)
app/repositories/*  baza so'rovlari
app/models          SQLAlchemy modellari; app/schemas.py — Pydantic sxemalar
app/middleware.py   X-Request-ID + vaqt logi, CSRF sarlavha tekshiruvi
app/realtime.py     Socket.IO xonalari: managers, gps:{tuman}, driver:{id}
```

API'ni Postman bilan sinash: `Authorization: Bearer <token>` sarlavhasi bilan CSRF tekshiruvi talab qilinmaydi; brauzer cookie bilan ishlaganda `X-Requested-With: csw` sarlavhasi shart.

## Prod (VPS) uchun eslatma

- Tashqi Nginx: SSL (Let's Encrypt) va `proxy_pass http://127.0.0.1:8080`; `.env` da `COOKIE_SECURE=true`.
- UFW: faqat 22, 80, 443 ochiq; MySQL, MinIO va API portlari `127.0.0.1` ga bog'langan.
- Planshetda GPS va kamera faqat **HTTPS** orqali ishlaydi.

## Huquqlar (PR #7)

- Ruxsat kodi `<bo'lim>.<amal>`: `customers.*`, `staff.*`, `vehicles.*`, `settings.*` (katalog: `backend/app/core/permissions.py`).
  Admin hammasiga ega; boshqa xodimga yaratilganda rol andozasi yoziladi, keyin "Xodimlar → Huquqlar" oynasida ochiladi/yopiladi.
- Doira: GPS/haydovchi — bitta tuman; manager/yurist/operator — bir nechta tuman. Manager faqat o'z tumanlaridagi
  GPS/yurist/operator/haydovchilarni ko'radi va boshqaradi; faqat o'zida bor ruxsatlarni bera oladi.
- Manager qo'shgan xodim admin tasdiqlamaguncha kira olmaydi ("Vaziyat" yoki "Xodimlar"da "Tasdiqlash").
- GPS radiusi tuman bo'yicha (bo'sh bo'lsa umumiy). Vaziyat paneli — faqat admin; managerning har o'zgarishi u yerga yoziladi.

## Call-center va statistika (PR #9)

- **Operator** (`/operator`): korxonani telefon/nom/STIR bo'yicha topadi → ariza ochadi (xizmat turi, hajm, vaqt, qo'ng'iroq qiluvchi, manba).
  Korxonada ochiq ariza bo'lsa — "Qayta ariza sifatida belgilaymi?" tasdig'i; ariza "qayta" belgisi bilan avvalgisiga bog'lanadi.
  Korxona topilmasa — **birinchi murojaat** yuridik bo'limga; yurist karta (+ shartnoma) ochadi, ariza avtomatik GPS xodimiga o'tadi.
- **72 soat**: har arizada muddat (`due_at`); muddati o'tganlari qizil belgilanadi va admin Vaziyat paneliga bir marta ogohlantirish tushadi.
- **Statistika** (`stats.view`): bugun / oxirgi 5 kun / oxirgi 10 kun / shu oy — tushgan, qayta, kutilmoqda, muddatdan oshgan,
  bajarilgan va bajarilmagan (soni va ulushi). Kartochka bosilsa — tumanlar kesimida diagramma va jadval. Manager — o'z tumanlari.
- Yangi ruxsatlar: `requests.view/create/cancel`, `appeals.view/create/review`, `stats.view`. Demo login: `operator`.
- Ovozli AI assistent bo'yicha kelishuvlar: `docs/plans/voice-ai-assistant.md`.

## Statistika, Arizalar va GPS "Yangilar" (PR #10)

- **Statistika** admin panelida birinchi yorliq. Kartochka (ko'rsatkich) tanlansa to'rtta diagramma faqat shu ko'rsatkich bo'yicha:
  Area (dinamika: bugun — soatlar, boshqa davrlar — kunlar), Pie (tarkib), Histogramma (ochilgandan bajarilguncha soatlar: 0–24, 24–48,
  48–72, 72+), Bar (tumanlar). Har biri "Jadval" ko'rinishiga o'tadi. **Excel / PDF** — tanlangan davr va ko'rsatkich bo'yicha
  (`GET /api/v1/stats/export?period=&metric=&format=xlsx|pdf`; PDF shriftlari: `backend/app/assets/fonts`, DejaVu litsenziyasi).
- **Arizalar** yorlig'i (`requests.view`; manager — o'z tumanlari): holat, tuman, xizmat turi, sana, qayta, muddati o'tgan, qidiruv;
  karta + holatlar tarixi; `requests.cancel` bo'lsa yangi arizani sabab bilan bekor qilish.
- **"Yangi"** — har xodim uchun alohida (`request_seen` jadvali, migratsiya 0008): arizani ochguncha/bosguncha belgilanadi.
  GPS ro'yxati eng yangisi tepada; filtrlar: Yangilar (standart), Bugun, Qayta, Muddati o'tgan, Assenizator, Barchasi.

## Yozishma (PR #11)

- Har ariza va murojaat ichida bitta umumiy yozishma: **matn** va **ovozli xabar** (60 soniyagacha, audio 90 kun saqlanadi,
  keyin "saqlash muddati tugagan" bo'lib qoladi). Ruxsatlar: `chat.view`, `chat.write` (migratsiya 0009 mavjud xodimlarga beradi).
- Kim ko'radi: admin — hammasi; manager, yurist, operator — o'z tumanlari; GPS — o'z tumanidagi arizalar; haydovchi — faqat o'ziga
  biriktirilgan ariza. Murojaat yozishmasini GPS va haydovchi ko'rmaydi; murojaat ariza bo'lib ochilsa, uning yozishmasi ariza
  yozishmasining boshida ko'rinadi.
- Ariza yoki murojaat yopilgach — faqat o'qish (manager va admin yoza oladi).
- Navbarda o'qilmaganlar soni, boshqa xodim yozsa jonli toast ("Ochish"). Socket xabarlari faqat ko'rish huquqi borlarga
  (`user:{id}` xonasi). Mikrofon brauzerda faqat HTTPS (yoki localhost) orqali ishlaydi.

## Uch bosqichli jarayon va buyurtma varaqasi (PR #12)

Batafsil kelishuvlar: `docs/plans/three-stage-flow.md`.

- 🔴 **Qizil** (GPS): 72 soat teskari timer, rang to'qlashadi, 72 soatdan keyin qora; yangi karta tushganda ovozli alert.
  Mashina dropdowni: bugungi ish jadvalidan, yuridik bo'lim mashinalari yuqorida, korxonagacha masofa bilan.
- 🟡 **Sariq** (GPS, legal, haydovchi): biriktirilganiga N soat; legal va haydovchi uchun ham ovozli alert.
- 🟢 **Yashil**: legal varaqani yopganda yoki haydovchi planshetda dalolatnomani yakunlaganda.
- **Korxona maxsus raqami** (`KTR47`): STIR o'rniga, avtomatik va doimiy. STIR endi takrorlanishi mumkin.
- **Buyurtma varaqasi**: GPS chop etadi (PDF, ikki qism). Maxfiy tasdiq kodi faqat qog'ozda bo'ladi, bazada HMAC xeshi.
  Qayta chop etish manager ruxsati bilan. Kod 3 marta noto'g'ri kiritilsa blok. Yopish uchun skan, kod, kub va tur kerak.
- **Kunlik ish jadvali** smenalar o'rnida. Haydovchi smenasiz ishlaydi.
- **GPS-monitoring uchun API** (`X-Api-Key`, `INTEGRATION_API_KEY`): `POST /api/v1/integrations/vehicle-positions`,
  `GET/PUT /api/v1/integrations/schedule`. Ixtiyoriy sozlama: `ORDER_CODE_SECRET` (bo'sh bo'lsa `JWT_SECRET`'dan olinadi).
- **Yangi ruxsatlar** (migratsiya 0010 mavjud xodimlarga beradi): `orders.view`, `orders.print` (GPS), `orders.close` (legal),
  `orders.unlock` (manager); legal uchun `requests.view`.

## Murojaatlar va operator (PR #13)

- «Ariza» tushunchasi olib tashlandi: hamma joyda **murojaat**, raqamlar `M-000123` (migratsiya 0011 eski `AR-` raqamlarni o'zgartiradi).
- **Admin/manager → Murojaatlar**: barcha murojaatlar o'z rangida (qizil, qora — 72 soatdan o'tgan, sariq, yashil),
  12 / 72 / 144 soatlik 4 ta rangli panel, rang filtri, qidiruv. Manager sariq kartadan qayta chop etishga ruxsat beradi
  va blokni ochadi.
- **Operator**: «Yangi korxona» (telefon, STIR, mashinani kutib oluvchi) — korxona «shartnoma kutilmoqda» holatida ochiladi,
  maxsus raqam SMS bilan yuboriladi (Eskiz.uz: `ESKIZ_EMAIL`, `ESKIZ_PASSWORD`, `SMS_SENDER`; sozlanmasa faqat jurnal).
  Mavjud korxona: telefon, chiqindi turi, kutib oluvchi → «Murojaat yaratish».
- **STIR yana unikal**: band bo'lsa «Siz STIRni xato kiritdingiz — bu STIR «X» korxonasiga tegishli» va shu korxonaga o'tish.
- Shartnomasiz korxonalar murojaatlari GPS'ga ko'rinmaydi. GPS socket xonasi tuman bo'yicha (yangi qizil karta jonli tushadi).
- Sariq kartalarda buyurtma varaqasi raqami ko'rsatilmaydi (faqat qidiruv uchun).
