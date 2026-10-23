"""Nomlarni solishtirish uchun normallashtirish: Excel'dagi kirill va qo'lda kiritilgan lotin yozuvlar bir xil kalitga keladi."""
import re

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "ғ": "g'", "д": "d", "е": "e", "ё": "yo", "ж": "j", "з": "z", "и": "i",
    "й": "y", "к": "k", "қ": "q", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ў": "o'", "ф": "f", "х": "x", "ҳ": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "i",
    "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def to_latin(text: str) -> str:
    return "".join(_CYR.get(ch, ch) for ch in text.lower())


def key(text: str | None) -> str:
    """'«Яшил Дуне»  савдо мажмуаси' → 'yashil dune savdo majmuasi'."""
    s = to_latin(text or "")
    s = s.replace("ʻ", "'").replace("‘", "'").replace("’", "'").replace("`", "'")
    s = re.sub(r"[\"«»“”„()\[\],.;:!?№#]", " ", s)
    s = re.sub(r"[^0-9a-z' -]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Viloyat/tuman nomidan "viloyat", "tuman", "shahar" so'zlarini olib tashlab asosini topish
_SUFFIX = re.compile(r"\b(viloyati|viloyat|vil|tumani|tuman|t|shahri|shahar|shaxar|shaxri|sh)\b\.?")
# Excel'da uchragan imlo variantlari → bazadagi yozuv
_ALIASES = {"surxandaryo": "surxondaryo", "kashkadaryo": "qashqadaryo", "kashkadare": "qashqadaryo",
            "surxondare": "surxondaryo", "surxandare": "surxondaryo", "oltinkul": "oltinko'l", "sariosie": "sariosiyo",
            "sarosie": "sariosiyo", "shaxrisabz": "shahrisabz", "termez": "termiz"}


def place_key(name: str | None) -> str:
    """'Сурхандарё вилоят ' va 'Surxondaryo viloyati' → 'surxondaryo'. Shahar/tuman farqi alohida saqlanadi."""
    s = key(name).replace("'", "")
    s = _SUFFIX.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for wrong, right in _ALIASES.items():
        s = re.sub(rf"\b{wrong}\b", right.replace("'", ""), s)
    return s


def is_city(name: str | None) -> bool:
    k = key(name)
    return bool(re.search(r"\b(shahar|shaxar|shahri|shaxri)\b", k))


def phone_digits(phone: str | None) -> str:
    """'94-512-11-16 ' → '945121116' (9 xonali mahalliy raqam), '+998 94 …' → ham shunday."""
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 12 and d.startswith("998"):
        d = d[3:]
    return d


def format_phone(phone: str | None) -> str | None:
    d = phone_digits(phone)
    if len(d) == 9:
        return f"+998 {d[:2]} {d[2:5]}-{d[5:7]}-{d[7:]}"
    return (phone or "").strip() or None
