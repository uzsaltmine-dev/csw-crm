"""Buyurtma varaqasining PDF'i: A4 albom, ikki qism (1-nusxa — buyurtmachiga, 2-nusxa — xizmat ko'rsatuvchiga),
o'rtada qirqish chizig'i. Qog'ozdagi namunaga o'xshash; STIR o'rniga korxona maxsus raqami.
Kub, chiqindi turi, vaqt va imzolar ruchkada to'ldiriladi. Maxfiy tasdiq kodi ikkala qismda."""
import io
from datetime import timedelta
from pathlib import Path

from reportlab.lib.colors import Color, black
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
RED = Color(0.78, 0.07, 0.2)
GREY = Color(0.45, 0.45, 0.45)
_registered = False


def _fonts() -> None:
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("DejaVu", str(FONTS / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(FONTS / "DejaVuSans-Bold.ttf")))
        _registered = True


def _line(c, x, y, w, label=None, value=None, size=9):
    """Chiziq (ruchkada yoziladigan joy); qiymat bo'lsa ustiga yoziladi."""
    if label:
        c.setFont("DejaVu", size)
        c.drawString(x, y, label)
        lw = pdfmetrics.stringWidth(label, "DejaVu", size) + 4
    else:
        lw = 0
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(x + lw, y - 2, x + w, y - 2)
    if value:
        c.setFont("DejaVu-Bold", size)
        c.drawString(x + lw + 3, y + 1, str(value)[:60])


def _box(c, x, y, label, checked=False):
    c.setLineWidth(0.7)
    c.rect(x, y - 1, 8, 8)
    if checked:
        c.line(x + 1, y + 3, x + 3.5, y), c.line(x + 3.5, y, x + 7.5, y + 7)
    c.setFont("DejaVu", 9)
    c.drawString(x + 13, y, label)


def _code(c, x, y, code):
    c.setFont("DejaVu", 7.5)
    c.setFillColor(GREY)
    c.drawString(x, y + 13, "Tasdiq kodi (yuridik bo'limga topshiriladi)")
    c.setFillColor(black)
    c.setLineWidth(0.8)
    c.rect(x, y - 4, 118, 15)
    c.setFont("DejaVu-Bold", 11)
    c.drawString(x + 6, y, " ".join(code))


def _half(c, x0, top, width, d, code, copy_label):
    x, y = x0, top
    c.setFillColor(black)
    c.setFont("DejaVu-Bold", 11)
    c.drawCentredString(x + width / 2, y, "Ko'rsatilgan xizmat bo'yicha")
    c.drawCentredString(x + width / 2, y - 14, "BUYURTMA CHEKI")
    c.setFont("DejaVu", 7.5)
    c.drawCentredString(x + width / 2, y - 25, copy_label)
    # raqam (qizil, chop etilgan)
    c.setFillColor(RED)
    c.setFont("DejaVu-Bold", 20)
    c.drawRightString(x + width, y - 52, f"№ {d['form']['number']}")
    c.setFillColor(black)
    y -= 50
    _line(c, x, y, width * 0.52, "20__ yil «__» ")
    y -= 20
    _line(c, x, y, width * 0.45, "soat ____:____ dan")
    _line(c, x + width * 0.5, y, width * 0.5, "____:____ gacha")
    y -= 26
    c.setFont("DejaVu-Bold", 10)
    c.drawString(x, y, f"«{d['provider'] or 'BIO TEXNO KLASTER'}» MChJ")
    c.setFont("DejaVu", 7)
    c.drawString(x, y - 10, "(Xizmat ko'rsatuvchi tashkilot nomi)")
    y -= 30
    cust = d["customer"]
    _line(c, x, y, width, "Tashkilot nomi:", cust["name"])
    y -= 18
    _line(c, x, y, width * 0.48, "Maxsus raqami:", cust["code"])
    _line(c, x + width * 0.52, y, width * 0.48, "Murojaat:", d["request_number"])
    y -= 18
    _line(c, x, y, width, "Manzili:", cust["address"])
    y -= 26
    c.setFont("DejaVu-Bold", 9.5)
    c.drawString(x, y, "Olib chiqilgan chiqindi miqdori:")
    _line(c, x + width * 0.55, y, width * 0.3)
    c.setFont("DejaVu", 9)
    c.drawString(x + width * 0.87, y, "metr kub")
    c.setFont("DejaVu", 7)
    c.drawString(x + width * 0.55, y - 10, "(Miqdor raqam va so'z bilan yozilsin)")
    y -= 22
    _line(c, x, y, width * 0.85)
    c.setFont("DejaVu", 9)
    c.drawString(x + width * 0.87, y, "metr kub")
    y -= 22
    c.setFont("DejaVu-Bold", 9.5)
    c.drawString(x, y, "Olib chiqilgan chiqindi turini belgilang:")
    y -= 16
    _box(c, x + 6, y, "Qattiq maishiy chiqindi")
    _box(c, x + width * 0.5, y, "Suyuq maishiy chiqindi")
    y -= 22
    c.setFont("DejaVu-Bold", 9.5)
    c.drawString(x, y, "Xizmat ko'rsatuvchi maxsus texnika haqida ma'lumot")
    y -= 18
    v = d.get("vehicle") or {}
    _line(c, x, y, width * 0.48, "Davlat raqami:", v.get("plate"))
    _line(c, x + width * 0.52, y, width * 0.48, "Rusumi:", v.get("model"))
    y -= 18
    _line(c, x, y, width, "Haydovchi F.I.Sh.:", d.get("driver_name"))
    y -= 24
    _line(c, x, y, width * 0.36, "Buyurtmachi:")
    _line(c, x + width * 0.38, y, width * 0.24)
    _line(c, x + width * 0.64, y, width * 0.36)
    c.setFont("DejaVu", 7)
    c.drawString(x + width * 0.18, y - 10, "(lavozimi)")
    c.drawString(x + width * 0.46, y - 10, "(imzo)")
    c.drawString(x + width * 0.78, y - 10, "(F.I.O.)")
    y -= 24
    _line(c, x, y, width * 0.6, "Haydovchi imzosi:")
    c.setFont("DejaVu-Bold", 10)
    c.drawString(x + width * 0.78, y, "M.O'.")
    _code(c, x, y - 40, code)


def render(d: dict, code: str) -> bytes:
    _fonts()
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))
    c.setTitle(f"Buyurtma varaqasi {d['form']['number']}")
    margin, gap = 28, 36
    half = (w - 2 * margin - gap) / 2
    top = h - 40
    _half(c, margin, top, half, d, code, "(buyurtmachi tashkilotga beriladigan 1-nusxa)")
    _half(c, margin + half + gap, top, half, d, code, "(xizmat ko'rsatuvchi tashkilotga beriladigan 2-nusxa)")
    # qirqish chizig'i
    cx = w / 2
    c.setDash(4, 3)
    c.setLineWidth(0.8)
    c.setStrokeColor(GREY)
    c.line(cx, 24, cx, h - 24)
    c.setDash()
    c.saveState()
    c.translate(cx - 4, h / 2)
    c.rotate(90)
    c.setFont("DejaVu", 8)
    c.setFillColor(GREY)
    c.drawCentredString(0, 0, "✂  Qirqish chizig'i")
    c.restoreState()
    assigned = d.get("assigned_at")
    if assigned:
        c.setFont("DejaVu", 6.5)
        c.setFillColor(GREY)
        c.drawString(margin, 14, f"Tizim: biriktirilgan {(assigned + timedelta(hours=5)).strftime('%d.%m.%Y %H:%M')} · "
                                 f"varaqa {d['form']['number']} · {d['form']['print_count']}-chop etish")
    c.showPage()
    c.save()
    return buf.getvalue()
