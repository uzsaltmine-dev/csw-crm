# Uch bosqichli jarayon (qizil → sariq → yashil) — kelishuvlar

Foydalanuvchi bilan 2026-10-30 da grill-me savollari orqali kelishildi. PR #12 da qilingan qismlar ✅ bilan, keyingilari ⏳ bilan belgilangan.

## Bosqichlar
| Rang | Holat | Kimda |
|---|---|---|
| 🔴 Qizil | mashina biriktirilmagan | GPS: «Biriktirilmagan arizalar». 72 soat teskari timer, rang to'qlashadi, 72 soatdan keyin qora. Yangi karta tushganda ovozli alert |
| 🟡 Sariq | mashina biriktirilgan, chiqindi olinishi va varaqa qaytishi kutilmoqda | GPS «Biriktirilganlar», legal «Jarayonda», haydovchi «Biriktirilgan murojaatlar». Timer: biriktirilganiga N soat. Legal va haydovchi uchun ham ovozli alert |
| 🟢 Yashil | bajarilgan | legal va haydovchidagi «Bajarilganlar» |

## Qarorlar
- ✅ **Haydovchi paneli** ishlaydi (foto + imzoli dalolatnoma). Planshetda yakunlansa darhol yashil. Planshetsiz haydovchilar uchun buyurtma varaqasi yo'li parallel ishlaydi.
- ✅ **Smena logikasi olib tashlandi.** GPS panelida «Haydovchilar va smenalar» o'rniga «Kunlik ish jadvali» bor: mashina → haydovchi → xizmat turi (yuridik / jismoniy, mahallalar). Haydovchi smenasiz ishlaydi.
- ✅ **Mashina dropdowni.** GPS tumani mashinalari ko'rsatiladi. Bugun yuridik bo'lim uchun ishlayotganlar yuqorida turadi, ichida korxonagacha masofa bo'yicha o'sish va kamayish tartibi bor. Haydovchi jadvaldan olinadi.
- ✅ **Mashina joylashuvi** tashqi GPS-monitoring tizimidan keladi. Hozircha faqat API joyi tayyor: `POST /api/v1/integrations/vehicle-positions`, `GET/PUT /api/v1/integrations/schedule`, `X-Api-Key` = `INTEGRATION_API_KEY`. Haydovchi plansheti ham joylashuv yuboradi.
- ✅ **Korxona maxsus raqami** STIR o'rniga ishlatiladi. Format: 3 ta tasodifiy harf va 2 ta raqam, chiziqchasiz (`KTR47`). O, I va Q harflari yo'q. Raqam doimiy va avtomatik beriladi.
- ✅ **STIR takrorlanishi mumkin**, chunki maktablar kabi tashkilotlarda u bir xil bo'ladi.
- ✅ **Buyurtma varaqasi** GPS mashina biriktirganda yaratiladi.
  - Ochiq 7 xonali raqami bor: hamma ko'radi va u bilan qidiradi.
  - Maxfiy 7 belgili tasdiq kodi faqat chop etilgan PDF'da bo'ladi, ikkala qismda ham. Ekranda va API'da kod yo'q, bazada faqat HMAC xeshi saqlanadi.
  - GPS varaqani bir marta chop etadi. Qayta chop etish uchun manager ruxsati kerak va yangi kod beriladi. Chop etishlar jurnalga yoziladi.
  - Kod 3 marta noto'g'ri kiritilsa varaqa bloklanadi va Vaziyat paneliga xabar tushadi. Blokni manager ochadi.
  - Kod faqat qo'lda kiritiladi, QR ishlatilmaydi.
  - Faqat yangi chop etilgan varaqalar ishlatiladi: raqami oldindan bosilgan eski daftarlar ishlatilmaydi.
  - GPS kodni chop etishda ko'rishi mumkin. Bu nazorat bilan qabul qilingan: murojaatni faqat legal yopadi.
- ✅ **Legal yopishi.** Tartib: skan (majburiy) → maxfiy kod → forma avtomatik to'ladi → kub va chiqindi turi (bularsiz forma yopilmaydi) → «Murojaatni yopish» → yashil.
- ⏳ **GPS-monitoring geozonasi:** mashina korxona yonida bo'lmagan bo'lsa murojaat yopilmaydi. Monitoring API ulangach qo'shiladi.
- ✅ **Buxgalter tasdiqlagan yangi shartnoma** bo'yicha murojaat GPS'ga qizil kartada «Yangi shartnoma» pilli bilan tushadi. Bu qaror qabul qilingan, pilli PR #13 da qo'shiladi.

## Keyingi bosqichlar
- ⏳ **PR #13:**
  - legal «Yangi korxonalar» tabi (sariq, timer bilan);
  - shartnoma formasi → «Tekshirish» → qog'oz ko'rinishi → «Buxgalteriyaga yuborish»;
  - buxgalter roli va tasdiqlash;
  - «Qilingan shartnomalar» bo'limi (yashil);
  - GPS'da «Yangi shartnoma» pilli.
- ⏳ **PR #14:**
  - buxgalteriya tizimi (1C'ga o'xshash, o'zimizniki, API bilan);
  - debitor va kreditor, ikki davrni solishtirish;
  - legal «Mening korxonalarim» tabi: jami korxonalar soni va jadval (nom, maxsus raqam, debitor, kreditor, jami kub — bosilganda tartiblanadi);
  - jadvaldagi har bir raqam bosilsa batafsil oyna ochiladi;
  - sariq kartada debitor va kreditor pillari.
- ⏳ Haydovchilar uchun Telegram bot (planshetdagi jarayon bilan bir xil). PR #14 dan keyin.
- ⏳ O'zimizning GPS-monitoring tizimi (GPS paneli ichida) va jismoniy abonentlar bilan ishlash. Yuridik bo'lim qismi tugagach boshlanadi.
