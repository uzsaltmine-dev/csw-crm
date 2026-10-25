import Swal from "sweetalert2";

const base = { confirmButtonColor: "#1d6b4f", heightAuto: false } as const;
type Icon = "success" | "error" | "warning" | "info";

// SweetAlert standart z-index (1060) MUI navbar (1100) va dialoglar (1300) ostida qoladi — hammasidan yuqoriga chiqaramiz.
// Toast navbar ostida (64 px) o'ng tomonda chiqadi, shunda navbar uni yopmaydi.
const STYLE = `
.swal2-container { z-index: 2000 !important; }
.swal2-container.swal2-top-end, .swal2-container.swal2-top { top: 72px !important; }
@media (max-width: 600px) { .swal2-container.swal2-top-end, .swal2-container.swal2-top { top: 104px !important; } }
`;
if (typeof document !== "undefined" && !document.getElementById("csw-swal-style")) {
  const el = document.createElement("style");
  el.id = "csw-swal-style";
  el.textContent = STYLE;
  document.head.appendChild(el);
}

/** Shu sessiyada ekranda chiqqan barcha xabarlar — Vaziyat panelida "shu sessiya" bo'limida ko'rinadi. */
export interface SessionAlert { id: number; at: Date; icon: Icon; title: string }
const sessionLog: SessionAlert[] = [];
const listeners = new Set<() => void>();
let seq = 0;

export function sessionAlerts(): readonly SessionAlert[] { return sessionLog; }
export function onSessionAlert(fn: () => void): () => void { listeners.add(fn); return () => { listeners.delete(fn); }; }
export function clearSessionAlerts(): void { sessionLog.length = 0; listeners.forEach((l) => l()); }

function remember(icon: Icon, title: string) {
  sessionLog.unshift({ id: ++seq, at: new Date(), icon, title });
  if (sessionLog.length > 200) sessionLog.length = 200;
  listeners.forEach((l) => l());
}

/** Muvaffaqiyat — 4 soniya; ogohlantirish/ma'lumot — 7 soniya; xato — yopilmaguncha turadi. */
export const toast = (title: string, icon: Icon = "success", opts: { log?: boolean } = {}) => {
  if (opts.log !== false) remember(icon, title);
  const sticky = icon === "error";
  return Swal.fire({
    ...base, toast: true, position: "top-end", icon, title,
    timer: sticky ? undefined : icon === "success" ? 4000 : 7000, timerProgressBar: !sticky,
    showConfirmButton: false, showCloseButton: true,
  });
};

export const confirmDialog = (title: string, confirmText: string, cancelText: string, text?: string) =>
  Swal.fire({ ...base, title, text, icon: "question", showCancelButton: true, confirmButtonText: confirmText, cancelButtonText: cancelText })
    .then((r) => r.isConfirmed);
