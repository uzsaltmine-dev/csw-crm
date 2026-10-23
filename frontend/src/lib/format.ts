const pad = (n: number) => String(n).padStart(2, "0");

/** 23.10.2026 21:03 — barcha tillarda bir xil, O'zbekistonda qabul qilingan ko'rinish. */
export function formatDateTime(d: Date): string {
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
