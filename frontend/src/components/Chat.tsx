import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Alert, Badge, Box, Button, Chip, CircularProgress, Divider, Drawer, IconButton, List, ListItemButton, ListItemText, Popover,
  Stack, TextField, Tooltip, Typography } from "@mui/material";
import ChatIcon from "@mui/icons-material/ChatBubbleOutline";
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/DeleteOutline";
import LockIcon from "@mui/icons-material/LockOutlined";
import MicIcon from "@mui/icons-material/Mic";
import PlayIcon from "@mui/icons-material/PlayArrow";
import SendIcon from "@mui/icons-material/Send";
import StopIcon from "@mui/icons-material/Stop";
import { toast as sonner } from "sonner";
import { chatApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useCan } from "@/hooks/useCan";
import { useI18n } from "@/i18n/I18nContext";
import type { MessageKey } from "@/i18n/messages";
import { toast } from "@/lib/alerts";
import { formatDateTime } from "@/lib/format";
import { getSocket } from "@/lib/socket";
import { useAppSelector } from "@/store";
import type { ChatEvent, ChatMessage, ChatThread, ChatThreadType, ChatUnread } from "@/types";

const MAX_VOICE_S = 60;
const CHAT_EVENT = "csw:chat-message";

type Open = { type: ChatThreadType; id: number } | null;
interface ChatCtx {
  unread: ChatUnread;
  refresh: () => void;
  openChat: (type: ChatThreadType, id: number) => void;
  countFor: (type: ChatThreadType, id: number) => number;
}
const Ctx = createContext<ChatCtx | null>(null);
export const useChat = () => useContext(Ctx);

/** Yozishma xabari shu ochiq yozishmaga tegishlimi (ariza yozishmasida murojaat xabarlari ham ko'rinadi). */
const belongs = (m: ChatEvent, open: Open) => !!open && (
  (m.thread.type === open.type && m.thread.id === open.id) || (open.type === "request" && m.thread.request_id === open.id));

/**
 * Yozishma: o'qilmaganlar soni, jonli toast va har qanday ekrandan ochiladigan yon panel.
 * Toast — faqat boshqa xodim yozganda va shu yozishma hozir ochiq bo'lmaganda.
 */
export function ChatProvider({ children }: { children: ReactNode }) {
  const { t } = useI18n();
  const can = useCan();
  const me = useAppSelector((s) => s.auth.user);
  const enabled = can("chat.view");
  const [unread, setUnread] = useState<ChatUnread>({ total: 0, threads: [] });
  const [open, setOpen] = useState<Open>(null);
  const openRef = useRef<Open>(null);
  openRef.current = open;

  const refresh = useCallback(() => { if (enabled) chatApi.unread().then(setUnread).catch(() => undefined); }, [enabled]);
  const openChat = useCallback((type: ChatThreadType, id: number) => setOpen({ type, id }), []);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    const s = getSocket();
    const on = (m: ChatEvent) => {
      window.dispatchEvent(new CustomEvent<ChatEvent>(CHAT_EVENT, { detail: m }));
      if (m.author_id === me?.id) return;
      if (belongs(m, openRef.current)) return; // panel o'zi "o'qildi" qiladi
      refresh();
      const target = m.thread.request_id && m.thread.type === "appeal" ? { type: "request" as const, id: m.thread.request_id } : m.thread;
      const body = m.kind === "voice" ? t("chat_voice_msg") : (m.text ?? "");
      sonner.info(`${m.thread.number ?? ""} · ${m.author_name}`, {
        description: body.length > 120 ? `${body.slice(0, 120)}…` : body, duration: 8000,
        action: { label: t("chat_open"), onClick: () => setOpen({ type: target.type, id: target.id }) },
      });
    };
    s.on("chat:message", on);
    const poll = window.setInterval(refresh, 60_000);
    return () => { s.off("chat:message", on); window.clearInterval(poll); };
  }, [enabled, me?.id, refresh, t]);

  const countFor = useCallback((type: ChatThreadType, id: number) =>
    unread.threads.find((x) => x.thread_type === type && x.thread_id === id)?.count ?? 0, [unread]);
  const value = useMemo(() => ({ unread, refresh, openChat, countFor }), [unread, refresh, openChat, countFor]);

  return (
    <Ctx.Provider value={value}>
      {children}
      {/* Ariza kartasi (Dialog) ustidan ochiladi: drawer'ning odatdagi z-index'i dialogdan past */}
      <Drawer anchor="right" open={!!open} onClose={() => setOpen(null)} sx={{ zIndex: (th) => th.zIndex.modal + 1 }}
        PaperProps={{ sx: { width: { xs: "100%", sm: 460 }, display: "flex", flexDirection: "column" } }}>
        {open && <ChatPanel key={`${open.type}-${open.id}`} type={open.type} id={open.id} onClose={() => setOpen(null)} />}
      </Drawer>
    </Ctx.Provider>
  );
}

/** Navbar: o'qilmagan yozishmalar soni va ro'yxati. */
export function ChatBell() {
  const { t } = useI18n();
  const ctx = useChat();
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  if (!ctx) return null;
  const { unread, openChat } = ctx;
  return (
    <>
      <Tooltip title={t("chat_title")}>
        <IconButton id="chat-bell" aria-label={t("chat_title")} onClick={(e) => setAnchor(e.currentTarget)}>
          <Badge color="error" badgeContent={unread.total} max={99}><ChatIcon /></Badge>
        </IconButton>
      </Tooltip>
      <Popover open={!!anchor} anchorEl={anchor} onClose={() => setAnchor(null)} anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }} PaperProps={{ sx: { width: 340, maxHeight: 420 } }}>
        <Typography variant="subtitle2" sx={{ px: 2, pt: 1.5, pb: 1 }}>{t("chat_unread_title")}</Typography>
        <Divider />
        {!unread.threads.length
          ? <Typography color="text.secondary" variant="body2" sx={{ p: 2 }}>{t("chat_no_unread")}</Typography>
          : <List dense disablePadding id="chat-unread-list">
            {unread.threads.map((x) => (
              <ListItemButton key={`${x.thread_type}-${x.thread_id}`} onClick={() => { setAnchor(null); openChat(x.thread_type, x.thread_id); }}>
                <ListItemText primary={`${x.number ?? ""} · ${x.title}`} primaryTypographyProps={{ noWrap: true, fontWeight: 600 }}
                  secondary={t(x.thread_type === "appeal" ? "chat_appeal" : "chat_request")} />
                <Chip size="small" color="error" label={x.count} sx={{ ml: 1 }} />
              </ListItemButton>
            ))}
          </List>}
      </Popover>
    </>
  );
}

/** Ariza/murojaat kartasidagi "Yozishma (n)" tugmasi. */
export function ChatButton({ type, id, size = "small", variant = "outlined" }: { type: ChatThreadType; id: number; size?: "small" | "medium" | "large";
  variant?: "outlined" | "text" | "contained" }) {
  const { t } = useI18n();
  const ctx = useChat();
  const can = useCan();
  if (!ctx || !can("chat.view")) return null;
  const n = ctx.countFor(type, id);
  return (
    <Button size={size} variant={variant} data-chat={`${type}-${id}`} onClick={(e) => { e.stopPropagation(); ctx.openChat(type, id); }}
      startIcon={<Badge color="error" variant="dot" invisible={!n}><ChatIcon fontSize="small" /></Badge>}>
      {t("chat_title")}{n ? ` (${n})` : ""}
    </Button>
  );
}

const fmtDur = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function VoiceBubble({ m }: { m: ChatMessage }) {
  const { t, tErr } = useI18n();
  const [src, setSrc] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => () => { if (src) URL.revokeObjectURL(src); }, [src]);
  if (!m.has_audio) return <Typography variant="body2" color="text.secondary" fontStyle="italic">🎤 {t("chat_voice_expired")}</Typography>;
  if (src) return <audio src={src} controls autoPlay style={{ width: 240, maxWidth: "100%", height: 36 }} data-voice={m.id} />;
  const load = async () => {
    setBusy(true);
    try { setSrc(URL.createObjectURL(await chatApi.audio(m.id))); } catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); }
    finally { setBusy(false); }
  };
  return (
    <Button size="small" variant="outlined" color="inherit" onClick={load} disabled={busy} data-voice-play={m.id}
      startIcon={busy ? <CircularProgress size={14} /> : <PlayIcon />} sx={{ borderColor: "divider" }}>
      {t("chat_voice_msg")} · {fmtDur(m.duration_s ?? 0)}
    </Button>
  );
}

function pickMime(): string {
  const opts = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "audio/webm"];
  return opts.find((o) => typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported?.(o)) ?? "";
}

/** Ovoz yozish: 60 soniyada o'zi to'xtaydi; yuborishdan oldin eshitib ko'rish mumkin. */
function useRecorder() {
  const [state, setState] = useState<"idle" | "rec" | "ready">("idle");
  const [secs, setSecs] = useState(0);
  const [blob, setBlob] = useState<Blob | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const timer = useRef<number>();
  const started = useRef(0);
  const dur = useRef(0);

  const stop = useCallback(() => { if (rec.current?.state === "recording") rec.current.stop(); }, []);
  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mime = pickMime();
    const r = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    const chunks: BlobPart[] = [];
    r.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    r.onstop = () => {
      window.clearInterval(timer.current);
      stream.getTracks().forEach((tr) => tr.stop());
      dur.current = Math.min(MAX_VOICE_S, (performance.now() - started.current) / 1000);
      setBlob(new Blob(chunks, { type: (r.mimeType || mime || "audio/webm").split(";")[0] }));
      setState("ready");
    };
    rec.current = r;
    started.current = performance.now();
    setSecs(0); setBlob(null); setState("rec");
    r.start(250);
    timer.current = window.setInterval(() => {
      const s = (performance.now() - started.current) / 1000;
      setSecs(s);
      if (s >= MAX_VOICE_S) r.stop();
    }, 200);
  }, []);
  const reset = useCallback(() => { setBlob(null); setState("idle"); setSecs(0); }, []);
  useEffect(() => () => { window.clearInterval(timer.current); if (rec.current?.state === "recording") rec.current.stop(); }, []);
  return { state, secs, blob, duration: () => dur.current, start, stop, reset };
}

export function ChatPanel({ type, id, onClose }: { type: ChatThreadType; id: number; onClose?: () => void }) {
  const { t, tErr } = useI18n();
  const ctx = useChat();
  const me = useAppSelector((s) => s.auth.user);
  const [th, setTh] = useState<ChatThread | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const recorder = useRecorder();
  const scroller = useRef<HTMLDivElement>(null);
  const fail = useCallback((e: unknown) => toast(tErr(errorCode(e), errorMessage(e)), "error"), [tErr]);
  const stick = useRef(true);

  const markRead = useCallback(() => { chatApi.read(type, id).then(() => ctx?.refresh()).catch(() => undefined); }, [type, id, ctx]);

  useEffect(() => {
    chatApi.thread(type, id).then((x) => { setTh(x); markRead(); }).catch((e) => { fail(e); onClose?.(); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [type, id]);

  // Jonli: shu yozishmaga yangi xabar
  useEffect(() => {
    const on = (e: Event) => {
      const m = (e as CustomEvent<ChatEvent>).detail;
      if (!belongs(m, { type, id })) return;
      setTh((cur) => cur && !cur.items.some((x) => x.id === m.id) ? { ...cur, items: [...cur.items, m] } : cur);
      if (m.author_id !== me?.id) markRead();
    };
    window.addEventListener(CHAT_EVENT, on);
    return () => window.removeEventListener(CHAT_EVENT, on);
  }, [type, id, me?.id, markRead]);

  useEffect(() => {
    const el = scroller.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [th?.items.length]);

  useEffect(() => {
    if (!recorder.blob) { setPreview(null); return; }
    const u = URL.createObjectURL(recorder.blob);
    setPreview(u);
    return () => URL.revokeObjectURL(u);
  }, [recorder.blob]);

  const add = (m: ChatMessage) => setTh((cur) => cur && !cur.items.some((x) => x.id === m.id) ? { ...cur, items: [...cur.items, m] } : cur);
  const sendText = async () => {
    const v = text.trim();
    if (!v || sending) return;
    setSending(true);
    try { stick.current = true; add(await chatApi.sendText(type, id, v)); setText(""); } catch (e) { fail(e); } finally { setSending(false); }
  };
  const sendVoice = async () => {
    if (!recorder.blob) return;
    setSending(true);
    try { stick.current = true; add(await chatApi.sendVoice(type, id, recorder.blob, recorder.duration())); recorder.reset(); }
    catch (e) { fail(e); } finally { setSending(false); }
  };
  const startRec = async () => {
    try { await recorder.start(); } catch { toast(t("chat_mic_denied"), "error"); }
  };
  const older = async () => {
    if (!th?.items.length) return;
    stick.current = false;
    try {
      const x = await chatApi.thread(type, id, th.items[0].id);
      setTh({ ...th, has_more: x.has_more, items: [...x.items, ...th.items] });
    } catch (e) { fail(e); }
  };

  return (
    <Stack sx={{ height: "100%" }} id="chat-panel" data-thread={`${type}-${id}`}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ px: 2, py: 1.25, borderBottom: 1, borderColor: "divider" }}>
        <ChatIcon color="primary" />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography fontWeight={600} noWrap>{th ? `${th.number ?? ""} · ${th.title}` : t("chat_title")}</Typography>
          <Typography variant="caption" color="text.secondary">{t(type === "appeal" ? "chat_appeal" : "chat_request")}</Typography>
        </Box>
        {onClose && <IconButton aria-label={t("close")} onClick={onClose}><CloseIcon /></IconButton>}
      </Stack>

      <Box ref={scroller} sx={{ flex: 1, overflowY: "auto", px: 2, py: 1.5, bgcolor: "background.default" }} id="chat-messages"
        onScroll={(e) => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40; }}>
        {!th && <Stack alignItems="center" sx={{ py: 6 }}><CircularProgress size={28} /></Stack>}
        {th?.has_more && <Box sx={{ textAlign: "center", mb: 1 }}><Button size="small" onClick={older}>{t("chat_older")}</Button></Box>}
        {th && !th.items.length && <Typography color="text.secondary" sx={{ textAlign: "center", py: 6 }}>{t("chat_empty")}</Typography>}
        <Stack spacing={1}>
          {th?.items.map((m, i) => {
            const mine = m.author_id === me?.id;
            const fromAppeal = th.thread_type === "request" && m.thread_type === "appeal";
            const prev = th.items[i - 1];
            const divider = fromAppeal && (!prev || prev.thread_type !== "appeal")
              ? t("chat_from_appeal") : !fromAppeal && prev?.thread_type === "appeal" && th.thread_type === "request" ? t("chat_request") : null;
            return (
              <Box key={m.id}>
                {divider && <Divider sx={{ my: 1 }}><Typography variant="caption" color="text.secondary">{divider}</Typography></Divider>}
                <Box data-msg={m.id} sx={{ display: "flex", justifyContent: mine ? "flex-end" : "flex-start" }}>
                  <Box sx={{ maxWidth: "85%", px: 1.5, py: 1, borderRadius: 2, border: 1, borderColor: mine ? "transparent" : "divider",
                    bgcolor: mine ? "primary.main" : "background.paper", color: mine ? "primary.contrastText" : "text.primary",
                    borderTopRightRadius: mine ? 4 : undefined, borderTopLeftRadius: mine ? undefined : 4 }}>
                    {!mine && <Typography variant="caption" fontWeight={700} display="block" color="primary">
                      {m.author_name}{m.author_role && !m.author_name.startsWith(t(`r_${m.author_role}` as MessageKey)) &&
                        <Typography component="span" variant="caption" color="text.secondary">{" · "}{t(`r_${m.author_role}` as MessageKey)}</Typography>}
                    </Typography>}
                    {m.kind === "voice" ? <Box sx={{ mt: 0.5, "& .MuiButton-root": mine ? { color: "inherit", borderColor: "rgba(255,255,255,.5)" } : {} }}>
                      <VoiceBubble m={m} /></Box>
                      : <Typography variant="body2" sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{m.text}</Typography>}
                    <Typography variant="caption" sx={{ display: "block", textAlign: "right", opacity: 0.7, mt: 0.25, fontVariantNumeric: "tabular-nums" }}>
                      {formatDateTime(new Date(m.created_at + "Z"))}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            );
          })}
        </Stack>
      </Box>

      {th && !th.can_write && <Alert icon={<LockIcon fontSize="small" />} severity="info" square id="chat-readonly">
        {t(th.closed ? "chat_closed" : "chat_no_write")}</Alert>}
      {th?.can_write && <Box sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}>
        {recorder.state === "rec" && <Stack direction="row" alignItems="center" spacing={1.5} id="chat-recording">
          <Box sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "error.main", animation: "csw-pulse 1s infinite",
            "@keyframes csw-pulse": { "50%": { opacity: 0.3 } } }} />
          <Typography sx={{ flex: 1, fontVariantNumeric: "tabular-nums" }}>{fmtDur(recorder.secs)} / {fmtDur(MAX_VOICE_S)}</Typography>
          <Button id="chat-rec-stop" variant="contained" color="error" disableElevation startIcon={<StopIcon />} onClick={recorder.stop}>{t("chat_stop")}</Button>
        </Stack>}
        {recorder.state === "ready" && <Stack direction="row" alignItems="center" spacing={1} id="chat-voice-preview">
          {preview && <audio src={preview} controls style={{ flex: 1, minWidth: 0, height: 36 }} />}
          <IconButton aria-label={t("cancel")} onClick={recorder.reset}><DeleteIcon /></IconButton>
          <Button id="chat-voice-send" variant="contained" disableElevation disabled={sending} endIcon={<SendIcon />} onClick={sendVoice}>{t("chat_send")}</Button>
        </Stack>}
        {recorder.state === "idle" && <Stack direction="row" alignItems="flex-end" spacing={1}>
          <TextField id="chat-input" fullWidth multiline maxRows={5} size="small" placeholder={t("chat_placeholder")} value={text}
            onChange={(e) => setText(e.target.value)} inputProps={{ maxLength: 2000 }}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendText(); } }} />
          {text.trim()
            ? <IconButton id="chat-send" color="primary" disabled={sending} onClick={sendText} aria-label={t("chat_send")}><SendIcon /></IconButton>
            : <Tooltip title={t("chat_record")}><IconButton id="chat-mic" color="primary" onClick={startRec} aria-label={t("chat_record")}
                sx={{ bgcolor: "action.hover", width: 44, height: 44 }}><MicIcon /></IconButton></Tooltip>}
        </Stack>}
      </Box>}
    </Stack>
  );
}
