/** O'zbek lotin → kirill. Kirill lug'ati alohida yuritilmaydi, lotin matndan hosil qilinadi. */
const PAIRS: [string, string][] = [
  ["O'", "Ў"], ["o'", "ў"], ["Oʻ", "Ў"], ["oʻ", "ў"], ["G'", "Ғ"], ["g'", "ғ"], ["Gʻ", "Ғ"], ["gʻ", "ғ"],
  ["SH", "Ш"], ["Sh", "Ш"], ["sh", "ш"], ["CH", "Ч"], ["Ch", "Ч"], ["ch", "ч"],
  ["Yo", "Ё"], ["yo", "ё"], ["Yu", "Ю"], ["yu", "ю"], ["Ya", "Я"], ["ya", "я"], ["Ye", "Е"], ["ye", "е"],
];
const SINGLE: Record<string, string> = {
  a: "а", b: "б", d: "д", e: "е", f: "ф", g: "г", h: "ҳ", i: "и", j: "ж", k: "к", l: "л", m: "м", n: "н", o: "о",
  p: "п", q: "қ", r: "р", s: "с", t: "т", u: "у", v: "в", x: "х", y: "й", z: "з", c: "ц", w: "в",
};
const LETTER = /[A-Za-zʻ']/;

export function toCyrillic(s: string): string {
  let out = "";
  let i = 0;
  while (i < s.length) {
    const pair = PAIRS.find(([la]) => s.startsWith(la, i));
    if (pair) {
      out += pair[1];
      i += pair[0].length;
      continue;
    }
    const ch = s[i];
    const lo = ch.toLowerCase();
    const wordStart = i === 0 || !LETTER.test(s[i - 1]);
    if (lo === "e" && wordStart) out += ch === lo ? "э" : "Э";
    else if (ch === "'" && i > 0 && /[A-Za-z]/.test(s[i - 1]) && /[A-Za-z]/.test(s[i + 1] ?? "")) out += "ъ";
    else if (SINGLE[lo]) out += ch === lo ? SINGLE[lo] : SINGLE[lo].toUpperCase();
    else out += ch;
    i++;
  }
  return out;
}
