import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Chip, MenuItem, Paper, Select, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { gpsApi, requestsApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useOnline } from "@/hooks/useOnline";
import { useI18n } from "@/i18n/I18nContext";
import { ChatButton } from "@/components/Chat";
import { toast } from "@/lib/alerts";
import { formatDateTime } from "@/lib/format";
import { getSocket } from "@/lib/socket";
import { RequestChips } from "@/pages/operator/OperatorHome";
import type { DriverTask, GpsDriver, Vehicle } from "@/types";

type GpsFilter = "new" | "today" | "repeat" | "overdue" | "septic" | "all";
const FILTERS: GpsFilter[] = ["new", "today", "repeat", "overdue", "septic", "all"];
const isToday = (iso: string) => new Date(iso + "Z").toDateString() === new Date().toDateString();
const MATCH: Record<GpsFilter, (r: DriverTask) => boolean> = {
  new: (r) => r.seen === false, today: (r) => isToday(r.created_at), repeat: (r) => !!r.is_repeat, overdue: (r) => !!r.overdue,
  septic: (r) => r.waste_type === "septic", all: () => true,
};

/** GPS xodimi: ertalab smena ochadi (haydovchi + bo'sh mashina) va yangi arizalarni smenadagi haydovchiga biriktiradi.
 *  To'liq panel (xarita, filtrlar, chat) 3-bosqichda; bu — haydovchi modulini jonli sinash uchun minimal ekran. */
export function GpsHome() {
  const { t, tErr } = useI18n();
  const online = useOnline();
  const [drivers, setDrivers] = useState<GpsDriver[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [requests, setRequests] = useState<DriverTask[]>([]);
  const [pickVehicle, setPickVehicle] = useState<Record<number, number>>({});
  const [pickDriver, setPickDriver] = useState<Record<number, number>>({});
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<GpsFilter>("new");
  // shu ko'rinishda ko'rilgan arizalar "Yangilar" filtrida filtr almashguncha qoladi (haydovchi tanlayotganda yo'qolib qolmasin)
  const [seenNow, setSeenNow] = useState<Set<number>>(new Set());

  const load = useCallback(async () => {
    const [d, v, r] = await Promise.all([gpsApi.drivers(), gpsApi.freeVehicles(), gpsApi.newRequests()]);
    setDrivers(d); setVehicles(v); setRequests(r);
  }, []);

  useEffect(() => {
    load().catch(() => undefined);
    const s = getSocket();
    const onUpdate = () => { load().catch(() => undefined); };
    s.on("request:updated", onUpdate);
    const poll = window.setInterval(onUpdate, 20_000); // haydovchi smenani boshlaganini ham ko'rish uchun
    return () => { s.off("request:updated", onUpdate); window.clearInterval(poll); };
  }, [load]);

  const run = async (fn: () => Promise<string>) => {
    setBusy(true);
    try { toast(await fn()); await load(); } catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); } finally { setBusy(false); }
  };
  const active = drivers.filter((d) => d.shift?.status === "active");
  const isNew = (r: DriverTask) => r.seen === false && !seenNow.has(r.id);
  const counts = Object.fromEntries(FILTERS.map((f) => [f, f === "new" ? requests.filter(isNew).length : requests.filter(MATCH[f]).length]));
  const shown = requests.filter((r) => MATCH[filter](r) || (filter === "new" && seenNow.has(r.id)));
  const markSeen = (ids: number[]) => {
    const fresh = ids.filter((id) => requests.find((r) => r.id === id)?.seen === false && !seenNow.has(id));
    if (!fresh.length) return;
    setSeenNow((s) => new Set([...s, ...fresh]));
    requestsApi.markSeen(fresh).catch(() => undefined);
  };
  const pickFilter = (f: GpsFilter) => {
    setFilter(f);
    if (seenNow.size) {
      setRequests((rs) => rs.map((r) => (seenNow.has(r.id) ? { ...r, seen: true } : r)));
      setSeenNow(new Set());
    }
  };

  return (
    <Stack spacing={3}>
      <Typography variant="h5">{t("gps_title")}</Typography>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>{t("gps_drivers")}</Typography>
        <TableContainer>
          <Table size="small">
            <TableHead><TableRow><TableCell>{t("pick_driver")}</TableCell><TableCell>{t("vehicle")}</TableCell><TableCell /></TableRow></TableHead>
            <TableBody>
              {drivers.map((d) => (
                <TableRow key={d.id}>
                  <TableCell><b>{d.full_name}</b><br /><Typography variant="caption" color="text.secondary">{d.phone}</Typography></TableCell>
                  <TableCell>
                    {d.shift
                      ? <Stack direction="row" spacing={1} alignItems="center"><span style={{ fontFamily: "monospace" }}>{d.shift.vehicle.plate}</span>
                          <Chip size="small" color={d.shift.status === "active" ? "success" : "warning"} label={t(d.shift.status === "active" ? "shift_active" : "shift_opened")} /></Stack>
                      : vehicles.length
                        ? <Select size="small" displayEmpty value={pickVehicle[d.id] ?? ""} onChange={(e) => setPickVehicle({ ...pickVehicle, [d.id]: Number(e.target.value) })} sx={{ minWidth: 160 }}>
                            <MenuItem value="" disabled>{t("pick_vehicle")}</MenuItem>
                            {vehicles.map((v) => <MenuItem key={v.id} value={v.id}>{v.plate}</MenuItem>)}
                          </Select>
                        : <Typography variant="body2" color="text.secondary">{t("no_free_vehicles")}</Typography>}
                  </TableCell>
                  <TableCell align="right">
                    {!d.shift && <Button variant="contained" size="small" disabled={busy || !online || !pickVehicle[d.id]}
                      onClick={() => run(async () => { await gpsApi.openShift(d.id, pickVehicle[d.id]); return t("shift_opened_ok"); })}>{t("open_shift")}</Button>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }} justifyContent="space-between" sx={{ mb: 1.5 }}>
          <Typography variant="h6">{t("gps_requests")}</Typography>
          <Button size="small" disabled={!counts.new} onClick={() => markSeen(requests.filter(isNew).map((r) => r.id))}>{t("gf_mark_all")}</Button>
        </Stack>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }} id="gps-filters" role="tablist">
          {FILTERS.map((f) => <Chip key={f} data-filter={f} role="tab" aria-selected={filter === f} clickable onClick={() => pickFilter(f)}
            color={filter === f ? "primary" : "default"} variant={filter === f ? "filled" : "outlined"}
            label={<Box component="span" sx={{ fontVariantNumeric: "tabular-nums" }}>{t(`gf_${f}`)} · {counts[f]}</Box>} />)}
        </Stack>
        {requests.length > 0 && active.length === 0 && <Alert severity="info" sx={{ mb: 2 }}>{t("no_active_drivers")}</Alert>}
        {requests.length === 0 ? <Typography color="text.secondary">{t("no_new_requests")}</Typography>
          : shown.length === 0 && <Typography color="text.secondary">{t("gf_empty")}</Typography>}
        <Stack spacing={1.5} id="gps-list">
          {shown.map((r) => (
            <Stack key={r.id} data-request={r.number} data-new={isNew(r) || undefined} onClick={() => markSeen([r.id])}
              direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}
              sx={{ border: 1, borderColor: isNew(r) ? "primary.main" : "divider", borderRadius: 1, p: 1.5,
                bgcolor: isNew(r) ? "action.hover" : undefined, borderLeftWidth: isNew(r) ? 4 : 1 }}>
              <Stack sx={{ flex: 1, minWidth: 0 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={600}>{r.number} · {r.customer.name}</Typography>
                  {isNew(r) && <Chip size="small" color="primary" label={t("rq_new_badge")} sx={{ height: 20 }} />}
                </Stack>
                <Typography variant="body2" color="text.secondary">{r.customer.address} · {t("created")}: {formatDateTime(new Date(r.created_at + "Z"))}
                  {r.due_at && <> · {t("due_at")}: {formatDateTime(new Date(r.due_at + "Z"))}</>}</Typography>
                {(r.waste_type === "septic" || r.customer.missing_fields.length > 0 || r.is_repeat || r.overdue) && <Stack direction="row" spacing={0.5} sx={{ mt: 0.5, flexWrap: "wrap" }}>
                  <RequestChips r={r} />
                  {r.customer.missing_fields.map((m) => <Chip key={m} size="small" color="error" variant="outlined" label={t(m === "stir" ? "missing_stir" : "missing_contract")} />)}
                </Stack>}
                {r.customer.missing_fields.length > 0 && <Typography variant="caption" color="error">{t("cannot_assign_hint")}</Typography>}
              </Stack>
              <Select size="small" displayEmpty value={pickDriver[r.id] ?? ""} onChange={(e) => setPickDriver({ ...pickDriver, [r.id]: Number(e.target.value) })} sx={{ minWidth: 180 }} disabled={!active.length}>
                <MenuItem value="" disabled>{t("pick_driver")}</MenuItem>
                {active.map((d) => <MenuItem key={d.id} value={d.id}>{d.full_name} · {d.shift!.vehicle.plate}</MenuItem>)}
              </Select>
              <Button variant="contained" disabled={busy || !online || !pickDriver[r.id] || r.customer.missing_fields.length > 0}
                onClick={() => run(async () => { const res = await gpsApi.assign(r.id, pickDriver[r.id]); return t("assigned_ok", { n: res.naryad_no ?? "" }); })}>{t("assign")}</Button>
              <ChatButton type="request" id={r.id} />
            </Stack>
          ))}
        </Stack>
      </Paper>
    </Stack>
  );
}
