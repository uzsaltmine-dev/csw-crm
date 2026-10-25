# Ovozli AI assistent (call-center) — reja uchun kelishuvlar

Holat: **rejalashtirilgan, hali boshlanmagan.** Batafsil reja va PR'lar alohida tasdiqlanadi.
Manba: 2026-10-25 dagi grill-me savol-javoblari (PR #9 tasdig'i bilan birga).

## Maqsad
Call-center operatori o'rnida qo'ng'iroqlarga ovozli AI javob beradi (inson omilini kamaytirish).

## Qarorlar

| Mavzu | Qaror |
|---|---|
| Telefoniya | **Hali aniq emas.** Avval 1348 qisqa raqami qanday kelishini o'rganish kerak (mobil operator SIP-trunk yoki call-center'lardagi mavjud ATS). |
| Tillar | **O'zbek tili shevalari + rus + tojik shevalari.** |
| Joylashuv | **O'z serverimizda**: nutqni tanish (STT), til modeli (LLM) va ovoz sintezi (TTS) bizning serverda; ovoz va matn tashqariga chiqmaydi (shaxsiy ma'lumotlar qonuni). |
| Zaxira yo'l | AI tushunmasa yoki muammo bo'lsa — **navbatchi xodimga ulash.** |
| AI vazifalari | **Ariza ochish**, **ariza holatini aytish**, **birinchi murojaatni yuridik bo'limga yuborish**, **shikoyat qabul qilish** (Manager'ga). |
| Yozuvlar | Ovoz va transkript **90 kun** saqlanadi. |
| Yuklama | **Kuniga 100 tagacha**, bir vaqtda **3–5** qo'ng'iroq. |
| Ishga tushirish | **Ish vaqtidan tashqari** (tun, dam olish kunlari) — avval faqat shu vaqtda AI javob beradi. |

## Rejada hisobga olinadigan xavflar
- **Shevalar va tojik tili**: tayyor ochiq STT modellari o'zbek adabiy tilida o'rtacha, shevalar va tojik tilida zaif. Haqiqiy
  qo'ng'iroq yozuvlarida (rozilik bilan) sinov va moslashtirish (fine-tuning) bosqichi kerak.
- **O'z serverida GPU**: STT + LLM + TTS uchun kamida bitta GPU server (3–5 parallel qo'ng'iroq uchun). Narx va xarid alohida.
- **Navbatchi xodim**: "ish vaqtidan tashqari" ishga tushirish bilan ziddiyat — tunda ulanadigan navbatchi kim bo'lishi
  aniqlanishi kerak (yoki tunda zaxira = qayta qo'ng'iroq so'rovi).
- **Telefoniya** aniqlanmaguncha arxitektura (SIP/ATS integratsiyasi) yakunlanmaydi.

## Keyingi qadam (reja tuziladi)
1. Telefoniyani o'rganish: 1348 raqami provayderi, SIP imkoniyati, mavjud ATS.
2. STT/TTS modellarini o'zbek/rus/tojik namunalarida sinov (sifat o'lchovi).
3. Arxitektura va PR'lar rejasi → tasdiq.
