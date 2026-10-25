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


# --- boshqa formatlar: xuddi shu ma'lumot (natija .xlsx bilan bir xil chiqishi kerak) ---
def _matrix(rows=ROWS, header=HEADER) -> list[list]:
    out = [["Буюртмаларни қайд этиш ЖАДВАЛИ"], [], header]
    for i, (reg, dist, name, act, addr, phone, person, info) in enumerate(rows, start=1):
        out.append([i, reg, dist, name, act, addr, phone, person, "02.09.2026", info, ""])
    return out


def build_xls(rows=ROWS) -> bytes:
    import xlwt
    wb = xlwt.Workbook(encoding="utf-8")
    ws = wb.add_sheet("Рес бўйича")
    for r, row in enumerate(_matrix(rows)):
        for c, v in enumerate(row):
            # Bitta telefon raqam sifatida (Excel'da shunday bo'ladi): xlrd uni 991234567.0 deb o'qiydi
            ws.write(r, c, int(v) if c == 6 and str(v).isdigit() else v)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_csv(rows=ROWS, encoding="cp1251", delimiter=";") -> bytes:
    import csv
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter)
    for row in _matrix(rows):
        w.writerow(row)
    # Windows-1251'da o'zbek harflari (ҳ, қ, ў, ғ) yo'q — Excel ularni "?" bilan almashtiradi
    return buf.getvalue().encode(encoding, errors="replace")


def build_docx(rows=ROWS) -> bytes:
    """Sarlavha matni + jadval ikki qismga bo'lingan (sahifadan sahifaga o'tgan jadval kabi)."""
    from docx import Document
    doc = Document()
    doc.add_paragraph("Буюртмаларни қайд этиш ЖАДВАЛИ")
    m = _matrix(rows)[2:]
    for part in (m[:4], m[4:]):
        t = doc.add_table(rows=0, cols=len(HEADER))
        for row in part:
            cells = t.add_row().cells
            for c, v in enumerate(row):
                cells[c].text = str(v)
        doc.add_paragraph("")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_pdf(rows=ROWS) -> bytes:
    """Matnli PDF: jadval ikki sahifada, sarlavha har sahifada takrorlanadi. Lotin yozuvida (standart shrift)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from app.services.normalize import to_latin

    def lat(v):
        return to_latin(str(v)).replace("«", '"').replace("»", '"')
    m = [[lat(v) for v in row] for row in _matrix(rows)[2:]]
    header, data = m[0], m[1:]
    style = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("FONTSIZE", (0, 0), (-1, -1), 6)])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
    story = [Paragraph("Buyurtmalarni qayd etish jadvali", getSampleStyleSheet()["Title"]),
             Table([header] + data[:3], style=style), PageBreak(), Table([header] + data[3:], style=style)]
    doc.build(story)
    return buf.getvalue()


def build_scanned_pdf() -> bytes:
    """Matnsiz PDF (skanerlangan hujjat kabi: faqat chizma)."""
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.rect(50, 50, 400, 300, fill=1)
    c.showPage()
    c.save()
    return buf.getvalue()
