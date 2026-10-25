import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Chip, MenuItem, Paper, Select, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { gpsApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useOnline } from "@/hooks/useOnline";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import { formatDateTime } from "@/lib/format";
import { getSocket } from "@/lib/socket";
import { RequestChips } from "@/pages/operator/OperatorHome";
import type { DriverTask, GpsDriver, Vehicle } from "@/types";

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
        <Typography variant="h6" sx={{ mb: 1 }}>{t("gps_requests")}</Typography>
        {requests.length > 0 && active.length === 0 && <Alert severity="info" sx={{ mb: 2 }}>{t("no_active_drivers")}</Alert>}
        {requests.length === 0 && <Typography color="text.secondary">{t("no_new_requests")}</Typography>}
        <Stack spacing={1.5}>
          {requests.map((r) => (
            <Stack key={r.id} direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
              <Stack sx={{ flex: 1, minWidth: 0 }}>
                <Typography fontWeight={600}>{r.number} · {r.customer.name}</Typography>
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
            </Stack>
          ))}
        </Stack>
      </Paper>
    </Stack>
  );
}
