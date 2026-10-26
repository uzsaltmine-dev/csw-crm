import { useEffect, useRef, useState, type ReactNode } from "react";
import { Alert, Box, Button, Chip, Divider, LinearProgress, Paper, Stack, TextField, Typography } from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import { useNavigate, useParams } from "react-router-dom";
import { driverApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { CollectedCapture } from "@/components/CollectedCapture";
import { PhotoCapture } from "@/components/PhotoCapture";
import { SignaturePad } from "@/components/SignaturePad";
import { distanceM, useGeolocation } from "@/hooks/useGeolocation";
import { useOnline } from "@/hooks/useOnline";
import { useI18n } from "@/i18n/I18nContext";
import { ChatButton } from "@/components/Chat";
import type { MessageKey } from "@/i18n/messages";
import { chooseDialog, toast } from "@/lib/alerts";
import { formatDateTime } from "@/lib/format";
import { useAppDispatch, useAppSelector } from "@/store";
import { refreshDriver, removeTask, upsertTask } from "@/store/driverSlice";
import type { Coords, FailReason, FileKind } from "@/types";

const LOCATION_EVERY_MS = 30_000;
type Draft = { containers: string; volume: string; note: string };

function loadDraft(id: number): Draft {
  try { return { containers: "", volume: "", note: "", ...JSON.parse(sessionStorage.getItem(`act:${id}`) ?? "{}") }; }
  catch { return { containers: "", volume: "", note: "" }; }
}

export function ActPage() {
  const { id } = useParams();
  const requestId = Number(id);
  const { t, tErr } = useI18n();
  const nav = useNavigate();
  const dispatch = useAppDispatch();
  const online = useOnline();
  const user = useAppSelector((s) => s.auth.user)!;
  const shift = useAppSelector((s) => s.driver.shift);
  const task = useAppSelector((s) => s.driver.tasks.find((x) => x.id === requestId));
  const [draft, setDraft] = useState<Draft>(() => loadDraft(requestId));
  const [busy, setBusy] = useState(false);
  const started = task ? task.status !== "assigned" : false;
  const geo = useGeolocation(started);

  // Kiritilgan maydonlar sahifa yangilansa ham yo'qolmaydi (internet uzilsa ham)
  useEffect(() => { try { sessionStorage.setItem(`act:${requestId}`, JSON.stringify(draft)); } catch { /* ignore */ } }, [draft, requestId]);

  // Jonli GPS: har 30 soniyada Manager/GPS paneliga
  const last = useRef(geo.coords);
  last.current = geo.coords;
  useEffect(() => {
    if (!started || !online) return;
    const tick = () => { if (last.current) driverApi.location(last.current).catch(() => undefined); };
    tick();
    const h = window.setInterval(tick, LOCATION_EVERY_MS);
    return () => window.clearInterval(h);
  }, [started, online]);

  const files = new Set<FileKind>(task?.files ?? []);
  const fields = {
    before: files.has("before"), gps: !!geo.coords, date: true, plate: !!shift, driver: true, naryad: !!task?.naryad_no,
    contract: !!task?.contract, inn: !!task?.customer.stir, containers: Number(draft.containers) >= 1,
    note: draft.note.trim().length > 0, volume: Number(draft.volume) > 0, sign: files.has("sign"), face: files.has("face"),
  };
  // 13 maydon formada; 14-si — "chiqindi olib ketildi" rasmi (joylashuvi bilan) oxirgi tugma orqali olinadi
  const filled = Object.values(fields).filter(Boolean).length;
  const formReady = filled === Object.keys(fields).length;

  if (!task || !shift) {
    return <Alert severity="info" action={<Button onClick={() => nav("/driver")}>{t("back")}</Button>}>{t("no_tasks")}</Alert>;
  }
  const c = task.customer;
  // Koordinata tasdiqlanmagan korxona (birinchi tashrif) — masofa ko'rsatilmaydi
  const dist = geo.coords && c.location_status === "confirmed" && c.lat !== null && c.lng !== null ? distanceM(geo.coords, { lat: c.lat, lng: c.lng }) : null;

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try { await fn(); } catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); } finally { setBusy(false); }
  };
  const markFile = (kind: FileKind) => dispatch(upsertTask({ ...task, files: Array.from(new Set([...task.files, kind])), status: kind === "before" ? "onsite" : task.status }));
  const upload = (kind: FileKind, needsGps: boolean) => async (blob: Blob) => {
    if (needsGps && !geo.coords) { toast(tErr("gps_required"), "warning"); throw new Error("gps"); }
    try {
      await driverApi.upload(task.id, kind, blob, geo.coords);
      markFile(kind);
    } catch (e) {
      toast(tErr(errorCode(e), errorMessage(e)), "error");
      throw e;
    }
  };

  const goEnroute = () => run(async () => { dispatch(upsertTask({ ...(await driverApi.enroute(task.id)), files: task.files })); });

  /** "Chiqindi olib ketildi" rasmi va u olingan joy → dalolatnoma yuboriladi. */
  const submitCollected = (photo: Blob, at: Coords) => run(async () => {
    await driverApi.upload(task.id, "after", photo, at);
    markFile("after");
    const res = await driverApi.complete(task.id, {
      containers: Number(draft.containers), volume_m3: Number(draft.volume), note: draft.note.trim(), lat: at.lat, lng: at.lng,
    });
    sessionStorage.removeItem(`act:${task.id}`);
    if (res.act.in_radius === null) toast(t("done_first_visit"), "info");
    else toast(res.act.in_radius ? t("done_ok") : t("done_suspect", { m: res.act.distance_m ?? 0 }), res.act.in_radius ? "success" : "warning");
    dispatch(removeTask(task.id));
    nav("/driver");
  });

  const fail = async () => {
    const reasons: FailReason[] = ["no_waste", "no_recipient", "no_access"];
    const reason = await chooseDialog(t("fail_reason"), reasons.map((x) => ({ value: x, label: t(`fr_${x}` as MessageKey) })),
      t("confirm"), t("cancel"), true);
    if (!reason) return;
    await run(async () => {
      await driverApi.fail(task.id, reason as FailReason, draft.note || undefined);
      toast(t("failed_ok"), "info");
      dispatch(removeTask(task.id));
      dispatch(refreshDriver());
      nav("/driver");
    });
  };

  const autoRow = (label: MessageKey, value: ReactNode) => (
    <Stack direction="row" justifyContent="space-between" spacing={2}>
      <Typography color="text.secondary">{t(label)}</Typography>
      <Typography sx={{ fontFamily: "monospace", textAlign: "right" }}>{value}</Typography>
    </Stack>
  );

  return (
    <Stack spacing={2}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Button onClick={() => nav("/driver")}>← {t("back")}</Button>
        <Chip color="primary" label={t(`s_${task.status}` as "s_assigned")} />
      </Stack>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6">{task.customer.name}</Typography>
        <Typography color="text.secondary">{t("address")}: {task.customer.address}</Typography>
        <Typography color="text.secondary">{t("phone")}: {task.customer.phone}</Typography>
        <Typography sx={{ fontFamily: "monospace", mt: 1 }}>{t("naryad")}: {task.naryad_no}</Typography>
        <Box sx={{ mt: 1.5 }}><ChatButton type="request" id={task.id} size="large" /></Box>
        {!started && <Button sx={{ mt: 2 }} variant="contained" size="large" onClick={goEnroute} disabled={busy || !online}>{t("go")}</Button>}
      </Paper>

      {started && <>
        {geo.error === "denied" && <Alert severity="error">{t("gps_denied")}</Alert>}
        <Alert severity={geo.coords ? "success" : "info"}>
          {geo.coords
            ? <>{geo.coords.lat.toFixed(5)}, {geo.coords.lng.toFixed(5)} · {t("gps_accuracy", { m: geo.coords.accuracy ?? "?" })}{dist !== null ? <> · {t("distance_to", { m: dist })}</> : c.location_status !== "confirmed" && <> · {t("first_visit")}</>}</>
            : t("gps_waiting")}
        </Alert>

        <Step n={1} title={t("step1")} ok={fields.before && fields.gps}>
          <PhotoCapture done={fields.before} disabled={!online || !geo.coords} onCapture={upload("before", true)} />
        </Step>

        <Step n={2} title={t("step2")} ok={fields.containers && fields.volume && fields.note}>
          <Stack spacing={0.5} sx={{ mb: 2 }}>
            {autoRow("f_date", formatDateTime(new Date()))}
            {autoRow("f_plate", shift.vehicle.plate)}
            {autoRow("f_driver", `${user.full_name} · ${user.phone ?? ""}`)}
            {autoRow("naryad", task.naryad_no)}
            {autoRow("f_contract", task.contract ? `${task.contract.number} · ${task.contract.signed_on ?? ""}` : "—")}
            {autoRow("f_inn", task.customer.stir)}
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField id="containers" label={t("f_cont")} type="number" value={draft.containers} fullWidth
              onChange={(e) => setDraft({ ...draft, containers: e.target.value })} slotProps={{ htmlInput: { min: 1, inputMode: "numeric" } }} />
            <TextField id="volume" label={t("f_vol")} type="number" value={draft.volume} fullWidth
              onChange={(e) => setDraft({ ...draft, volume: e.target.value })} slotProps={{ htmlInput: { min: 0.5, step: 0.5, inputMode: "decimal" } }} />
          </Stack>
          <TextField id="note" label={t("f_note")} value={draft.note} multiline minRows={2} fullWidth sx={{ mt: 2 }}
            onChange={(e) => setDraft({ ...draft, note: e.target.value })} />
        </Step>

        <Step n={3} title={t("step3")} ok={fields.sign && fields.face}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>{t("sign_here")}</Typography>
          {fields.sign
            ? <Typography color="success.main" sx={{ mb: 2 }}>✓ {t("uploaded")}</Typography>
            : <SignaturePad disabled={!online || !fields.before} onSave={upload("sign", false)} />}
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" sx={{ mb: 1 }}>{t("face_photo")}</Typography>
          <PhotoCapture facing="user" done={fields.face} disabled={!online || !fields.before} onCapture={upload("face", false)} />
        </Step>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2">{t("progress", { n: filled })}</Typography>
          <LinearProgress variant="determinate" value={(filled / 14) * 100} sx={{ my: 1.5, height: 8, borderRadius: 4 }} />
          {!formReady && <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>{t("collected_locked")}</Typography>}
          <Stack direction="row" spacing={2} justifyContent="space-between" flexWrap="wrap" useFlexGap>
            <CollectedCapture disabled={!online || !formReady} busy={busy} online={online} coords={geo.coords} customer={c}
              onSubmit={submitCollected} />
            <Button color="error" variant="outlined" onClick={fail} disabled={busy || !online}>{t("fail")}</Button>
          </Stack>
        </Paper>
      </>}
    </Stack>
  );
}

function Step({ n, title, ok, children }: { n: number; title: string; ok: boolean; children: ReactNode }) {
  return (
    <Paper variant="outlined" sx={{ p: 2, borderColor: ok ? "success.main" : "divider" }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
        {ok ? <CheckCircleIcon color="success" /> : <RadioButtonUncheckedIcon color="disabled" />}
        <Typography variant="subtitle1" fontWeight={600}>{n}. {title}</Typography>
      </Stack>
      <Box>{children}</Box>
    </Paper>
  );
}
