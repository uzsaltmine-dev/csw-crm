import { toast as sonner } from "sonner";
import { openDialog } from "@/lib/dialogs";

type Icon = "success" | "error" | "warning" | "info";

/** Shu tabda ekranda chiqqan barcha xabarlar — Vaziyat panelida "shu sessiya" bo'limida ko'rinadi.
 *  sessionStorage'da: sahifa yangilansa saqlanadi, tab yopilsa o'chadi. */
export interface SessionAlert { id: number; at: Date; icon: Icon; title: string }
const KEY = "csw:session-alerts";
const listeners = new Set<() => void>();

function read(): SessionAlert[] {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as SessionAlert[]).map((a) => ({ ...a, at: new Date(a.at) })) : [];
  } catch { return []; }
}
let sessionLog: SessionAlert[] = read();
function persist() {
  try { sessionStorage.setItem(KEY, JSON.stringify(sessionLog)); } catch { /* xotira to'la yoki yopiq — faqat xotirada qoladi */ }
  listeners.forEach((l) => l());
}

export function sessionAlerts(): readonly SessionAlert[] { return sessionLog; }
export function onSessionAlert(fn: () => void): () => void { listeners.add(fn); return () => { listeners.delete(fn); }; }
export function clearSessionAlerts(): void { sessionLog = []; persist(); }

function remember(icon: Icon, title: string) {
  const id = (sessionLog[0]?.id ?? 0) + 1;
  sessionLog = [{ id, at: new Date(), icon, title }, ...sessionLog].slice(0, 200);
  persist();
}

/** shadcn/ui (Sonner) uslubidagi toast. Muvaffaqiyat — 4 s, ogohlantirish/ma'lumot — 7 s, xato — yopilmaguncha. */
export const toast = (title: string, icon: Icon = "success", opts: { log?: boolean; description?: string } = {}) => {
  if (opts.log !== false) remember(icon, title);
  const duration = icon === "error" ? Infinity : icon === "success" ? 4000 : 7000;
  return sonner[icon](title, { duration, description: opts.description });
};

export const confirmDialog = (title: string, confirmText: string, cancelText: string, text?: string, destructive = true) =>
  openDialog<boolean>({ kind: "confirm", title, description: text, confirmText, cancelText, destructive }).then((r) => r === true);

/** Ro'yxatdan bittasini tanlash (masalan, "bajarib bo'lmadi" sababi). Bekor qilinsa — null. */
export const chooseDialog = (title: string, options: { value: string; label: string }[], confirmText: string, cancelText: string,
  destructive = false) =>
  openDialog<string>({ kind: "choose", title, options, confirmText, cancelText, destructive });
