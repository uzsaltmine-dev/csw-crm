import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Chip, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import CopyIcon from "@mui/icons-material/ContentCopy";
import VolumeOffIcon from "@mui/icons-material/VolumeOff";
import VolumeUpIcon from "@mui/icons-material/VolumeUp";
import { useI18n } from "@/i18n/I18nContext";
import type { Stage } from "@/types";

export const NORM_HOURS = 72;

/** Uch bosqich ranglari. Qizil karta vaqt o'tgani sari to'qlashadi, 72 soatdan keyin — qora. */
export const STAGE = {
  yellow: { bg: "#fff4d1", border: "#e3b23c", ink: "#5b4300", strong: "#c98a00" },
  green: { bg: "#e6f6ec", border: "#45a86b", ink: "#14532d", strong: "#1f8a4c" },
} as const;

const RED_START = [211, 47, 47];   // #d32f2f
const RED_END = [90, 12, 12];      // #5a0c0c
export function redColor(hours: number): string {
  if (hours >= NORM_HOURS) return "#141414";
  const k = Math.max(0, Math.min(1, hours / NORM_HOURS));
  const c = RED_START.map((a, i) => Math.round(a + (RED_END[i] - a) * k));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

/** Har daqiqada yangilanadigan "hozir" (timerlar uchun). */
export function useNow(stepMs = 30_000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const h = window.setInterval(() => setNow(Date.now()), stepMs); return () => window.clearInterval(h); }, [stepMs]);
  return now;
}

export const hoursSince = (iso: string | null | undefined, now: number) => (iso ? (now - new Date(iso + "Z").getTime()) / 3_600_000 : 0);
const hm = (h: number) => `${Math.floor(h)}:${String(Math.floor((h % 1) * 60)).padStart(2, "0")}`;

/** Qizil karta: 72 soatlik teskari sanoq ("47:12 qoldi"), o'tsa — "+5:03 kechikdi". */
export function RedTimer({ createdAt, now }: { createdAt: string; now: number }) {
  const { t } = useI18n();
  const h = hoursSince(createdAt, now);
  const left = NORM_HOURS - h;
  return (
    <Box data-timer sx={{ textAlign: "right", lineHeight: 1.1 }}>
      <Typography sx={{ fontSize: 22, fontWeight: 700, fontVariantNumeric: "tabular-nums", letterSpacing: 0.5 }}>
        {left >= 0 ? hm(left) : `+${hm(-left)}`}
      </Typography>
      <Typography variant="caption" sx={{ opacity: 0.85 }}>{t(left >= 0 ? "stg_left" : "stg_late")}</Typography>
    </Box>
  );
}

/** Sariq/yashil karta: shu bosqichga tushganiga necha soat bo'ldi. */
export function SinceTimer({ since, now, label }: { since: string | null | undefined; now: number; label?: string }) {
  const { t } = useI18n();
  if (!since) return null;
  return (
    <Box data-timer sx={{ textAlign: "right", lineHeight: 1.1 }}>
      <Typography sx={{ fontSize: 20, fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{hm(hoursSince(since, now))}</Typography>
      <Typography variant="caption" sx={{ opacity: 0.8 }}>{label ?? t("stg_since")}</Typography>
    </Box>
  );
}

export function StageChip({ stage }: { stage?: Stage }) {
  const { t } = useI18n();
  if (!stage) return null;
  const sx = stage === "red" ? { bgcolor: "#d32f2f", color: "#fff" }
    : stage === "yellow" ? { bgcolor: STAGE.yellow.border, color: "#2b1d00" }
      : stage === "green" ? { bgcolor: STAGE.green.strong, color: "#fff" } : {};
  return <Chip size="small" data-stage={stage} label={t(`stage_${stage}`)} sx={{ fontWeight: 600, ...sx }} />;
}

/** Katta, ko'zga tashlanadigan qiymat + nusxalash tugmasi (maxsus raqam, STIR). */
export function CopyValue({ value, label, big = false, id }: { value: string | null | undefined; label: string; big?: boolean; id?: string }) {
  const { t } = useI18n();
  const [done, setDone] = useState(false);
  if (!value) return null;
  const copy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try { await navigator.clipboard.writeText(value); } catch {
      const ta = document.createElement("textarea"); ta.value = value; document.body.appendChild(ta); ta.select();
      document.execCommand("copy"); ta.remove();
    }
    setDone(true);
    window.setTimeout(() => setDone(false), 1500);
  };
  return (
    <Stack direction="row" alignItems="center" spacing={0.5} id={id}>
      <Box>
        <Typography variant="caption" sx={{ opacity: 0.75, display: "block", lineHeight: 1 }}>{label}</Typography>
        <Typography data-copy-value sx={{ fontFamily: "ui-monospace, Menlo, monospace", fontWeight: 700, letterSpacing: big ? 2 : 0.5,
          fontSize: big ? 26 : 15, lineHeight: 1.2 }}>{value}</Typography>
      </Box>
      <Tooltip title={done ? t("copied") : t("copy")}>
        <IconButton size="small" onClick={copy} aria-label={`${t("copy")}: ${label}`} sx={{ color: "inherit" }}>
          {done ? <CheckIcon fontSize="small" /> : <CopyIcon fontSize="small" />}
        </IconButton>
      </Tooltip>
    </Stack>
  );
}

// --- ovozli alert ---
const SOUND_KEY = "csw:sound";
let ctx: AudioContext | null = null;

function beep(kind: "red" | "yellow") {
  try {
    ctx ??= new AudioContext();
    if (ctx.state === "suspended") void ctx.resume();
    const notes = kind === "red" ? [880, 660, 880] : [660, 880];
    notes.forEach((f, i) => {
      const o = ctx!.createOscillator(), g = ctx!.createGain();
      const t0 = ctx!.currentTime + i * 0.18;
      o.type = "sine"; o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(0.35, t0 + 0.02); g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.16);
      o.connect(g).connect(ctx!.destination); o.start(t0); o.stop(t0 + 0.17);
    });
  } catch { /* brauzer ovozni bloklagan */ }
}

/** Ovozli alert: yoqilgan bo'lsa yangi qizil/sariq karta tushganda signal. Holat shu brauzerda eslab qolinadi. */
export function useAlertSound() {
  const [on, setOn] = useState(() => { try { return localStorage.getItem(SOUND_KEY) !== "off"; } catch { return true; } });
  const onRef = useRef(on);
  onRef.current = on;
  const toggle = useCallback(() => setOn((v) => {
    const n = !v;
    try { localStorage.setItem(SOUND_KEY, n ? "on" : "off"); } catch { /* ignore */ }
    if (n) beep("yellow"); // foydalanuvchi bosishi audio'ni ochadi (brauzer qoidasi)
    return n;
  }), []);
  const play = useCallback((kind: "red" | "yellow") => { if (onRef.current) beep(kind); }, []);
  return { on, toggle, play };
}

export function SoundToggle({ on, toggle }: { on: boolean; toggle: () => void }) {
  const { t } = useI18n();
  return (
    <Tooltip title={t(on ? "sound_on_hint" : "sound_off_hint")}>
      <Chip id="sound-toggle" clickable onClick={toggle} variant={on ? "filled" : "outlined"} color={on ? "primary" : "default"}
        icon={on ? <VolumeUpIcon /> : <VolumeOffIcon />} label={t(on ? "sound_on" : "sound_off")} />
    </Tooltip>
  );
}

/** Ro'yxatga yangi id'lar qo'shilsa signal (birinchi yuklanishda emas). */
export function useNewItemsSignal(ids: number[], loaded: boolean, onNew: () => void) {
  const prev = useRef<Set<number> | null>(null);
  useEffect(() => {
    if (!loaded) return;
    const cur = new Set(ids);
    if (prev.current && ids.some((id) => !prev.current!.has(id))) onNew();
    prev.current = cur;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids.join(","), loaded]);
}
