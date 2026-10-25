"""Sun'iy call-center fayli: haqiqiy fayl tuzilishi (1-qator sarlavha matni, 3-qator ustunlar, kirill), shaxsiy ma'lumotsiz."""
import io

from openpyxl import Workbook

HEADER = ["Т/Р", "Ҳудуд номи", "Туман (шаҳар) номи", "Ташкилот номи", "Фаолият тури", "Манзили", "Телефон\nрақами",
          "Буюртма берган ходим\nФ.И.Ш.", "Буюртма келиб тушган сана", "Буюртма ҳақида қисқа\nмаълумот", "Ташкилот ИНН рақами"]

ROWS = [
    # viloyat, tuman, nom, faoliyat, manzil, telefon, xodim, info
    ("Андижон вилоят ", "Асака тумани", "«Янги Бозор» МЧЖ", "Савдо", "Мустақиллик к. 1", "94-512-11-16", "Тест Бир", "чиқинди олиб кетиш"),
    ("Андижон вилояти", "Асака туман", "\"Янги бозор\"  МЧЖ", "Савдо", "", "+998 90 555 11 22", "Тест Икки", "контейнер тўлган"),
    ("Сурхандарё вилоят", "Термиз шахри", "Сув Таъминот", "Коммунал", "Ал-Термизий 5", "93 111 22 33", "Тест Уч", "Ассенизатор керак"),
    ("Андижон вилоят", "Ангор туман", "Нотўғри Туман МЧЖ", "Савдо", "", "991234567", "", ""),
    ("Андижон вилоят", "Асака тумани", "Боғ МЧЖ", "Қишлоқ хўжалиги", "", "12345", "", ""),
    ("Андижон вилоят", "Асака тумани", "\"Асака Авто\" МЧЖ", "", "", "97 777 11 00", "Тест Тўрт", ""),
]


def build(rows=ROWS, header=HEADER) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Рес бўйича"
    ws.append(["Буюртмаларни қайд этиш ЖАДВАЛИ"])
    ws.append([])
    ws.append(header)
    for i, (reg, dist, name, act, addr, phone, person, info) in enumerate(rows, start=1):
        ws.append([i, reg, dist, name, act, addr, phone, person, "02.09.2026", info, None])
    ws.append([])  # bo'sh qator — hisobga olinmaydi
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
