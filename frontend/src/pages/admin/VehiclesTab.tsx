import { useCallback, useEffect, useState } from "react";
import { Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField } from "@mui/material";
import { adminApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import { confirmDialog, toast } from "@/lib/alerts";
import type { AdminVehicle } from "@/types";
import { districtLabel, type RefData } from "./AdminHome";

type Form = { id?: number; plate: string; model: string; district_id: number | "" };

export function VehiclesTab({ districts, canWrite }: RefData) {
  const { t, tErr } = useI18n();
  const [vehicles, setVehicles] = useState<AdminVehicle[]>([]);
  const [district, setDistrict] = useState<number | "">("");
  const [form, setForm] = useState<Form | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => setVehicles(await adminApi.vehicles()), []);
  useEffect(() => { load().catch(() => undefined); }, [load]);

  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try { await fn(); toast(t("saved")); await load(); return true; }
    catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); return false; }
    finally { setBusy(false); }
  };
  const save = async () => {
    if (!form || form.district_id === "") return;
    const body = { plate: form.plate, model: form.model || null, district_id: form.district_id as number };
    if (await run(() => form.id ? adminApi.updateVehicle(form.id, body) : adminApi.createVehicle(body))) setForm(null);
  };
  const toggle = async (v: AdminVehicle) => {
    if (v.is_active && !(await confirmDialog(t("confirm_deactivate"), t("deactivate"), t("cancel"), v.plate))) return;
    await run(() => adminApi.updateVehicle(v.id, { is_active: !v.is_active }));
  };
  const shown = vehicles.filter((v) => !district || v.district_id === district);

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mb: 2 }} justifyContent="space-between">
        <TextField id="v-filter" size="small" select label={t("district")} value={district} sx={{ minWidth: 220 }}
          onChange={(e) => setDistrict(e.target.value === "" ? "" : Number(e.target.value))}>
          <MenuItem value="">{t("all")}</MenuItem>
          {districts.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
        </TextField>
        {canWrite && <Button variant="contained" onClick={() => setForm({ plate: "", model: "", district_id: district })}>{t("new_vehicle")}</Button>}
      </Stack>
      <TableContainer>
        <Table size="small">
          <TableHead><TableRow><TableCell>{t("plate")}</TableCell><TableCell>{t("model")}</TableCell><TableCell>{t("district")}</TableCell><TableCell>{t("status")}</TableCell>{canWrite && <TableCell />}</TableRow></TableHead>
          <TableBody>
            {shown.map((v) => (
              <TableRow key={v.id} sx={{ opacity: v.is_active ? 1 : 0.55 }}>
                <TableCell sx={{ fontFamily: "monospace" }}>{v.plate}</TableCell>
                <TableCell>{v.model ?? "—"}</TableCell>
                <TableCell>{districtLabel(districts, v.district_id)}</TableCell>
                <TableCell><Chip size="small" color={v.is_active ? "success" : "default"} label={t(v.is_active ? "active" : "inactive")} /></TableCell>
                {canWrite && <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  <Button size="small" onClick={() => setForm({ id: v.id, plate: v.plate, model: v.model ?? "", district_id: v.district_id })}>{t("edit")}</Button>
                  <Button size="small" color={v.is_active ? "error" : "success"} disabled={busy} onClick={() => toggle(v)}>{t(v.is_active ? "deactivate" : "activate")}</Button>
                </TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={!!form} onClose={() => setForm(null)} fullWidth maxWidth="xs">
        <DialogTitle>{form?.id ? t("edit") : t("new_vehicle")}</DialogTitle>
        {form && <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField id="v-plate" label={t("plate")} value={form.plate} placeholder="60 A123BC" onChange={(e) => setForm({ ...form, plate: e.target.value })} />
            <TextField id="v-model" label={t("model")} value={form.model} placeholder="ISUZU NQR" onChange={(e) => setForm({ ...form, model: e.target.value })} />
            <TextField id="v-district" select label={t("district")} value={form.district_id} onChange={(e) => setForm({ ...form, district_id: Number(e.target.value) })}>
              {districts.filter((d) => d.is_active || d.id === form.district_id).map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
            </TextField>
          </Stack>
        </DialogContent>}
        <DialogActions>
          <Button onClick={() => setForm(null)}>{t("cancel")}</Button>
          <Button variant="contained" onClick={save} disabled={busy || !form || form.plate.trim().length < 4 || form.district_id === ""}>{t("save")}</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
