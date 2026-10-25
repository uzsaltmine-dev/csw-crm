import { useEffect, useState } from "react";
import { Box, Button, MenuItem, Paper, Select, Slider, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { adminApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useCan } from "@/hooks/useCan";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import { useAppSelector } from "@/store";
import type { DistrictRadius } from "@/types";
import type { RefData } from "./AdminHome";

const MARKS = [100, 150, 200, 250, 300].map((v) => ({ value: v, label: `${v} m` }));
const OPTIONS = Array.from({ length: 21 }, (_, i) => 100 + i * 10);

/** Umumiy GPS radiusi (faqat admin) va tumanlar bo'yicha radius (settings.radius_edit — o'z tumanlari). */
export function SettingsTab(_: RefData) {
  const { t, tErr } = useI18n();
  const can = useCan();
  const isAdmin = useAppSelector((s) => s.auth.user?.role) === "admin";
  const canDistrict = can("settings.radius_edit");
  const [saved, setSaved] = useState<number | null>(null);
  const [radius, setRadius] = useState(300);
  const [rows, setRows] = useState<DistrictRadius[]>([]);
  const [busy, setBusy] = useState(false);

  const apply = (s: { gps_radius_m: number; districts: DistrictRadius[] }) => { setSaved(s.gps_radius_m); setRadius(s.gps_radius_m); setRows(s.districts); };
  useEffect(() => { adminApi.settings().then(apply).catch(() => undefined); }, []);

  const run = async (fn: () => Promise<{ gps_radius_m: number; districts: DistrictRadius[] }>) => {
    setBusy(true);
    try { apply(await fn()); toast(t("saved")); }
    catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); }
    finally { setBusy(false); }
  };

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack spacing={2} sx={{ maxWidth: 520 }}>
          <Typography variant="subtitle1" fontWeight={600}>{t("radius_default_title")}: <span style={{ fontVariantNumeric: "tabular-nums" }}>{radius} m</span></Typography>
          <Typography variant="body2" color="text.secondary">{t("gps_radius_hint")}</Typography>
          <Box sx={{ px: 1 }}>
            <Slider value={radius} min={100} max={300} step={10} marks={MARKS} disabled={!isAdmin || saved === null}
              onChange={(_e, v) => setRadius(v as number)} aria-label={t("gps_radius")} />
          </Box>
          {isAdmin && <Box><Button variant="contained" onClick={() => run(() => adminApi.saveSettings(radius))}
            disabled={busy || saved === null || radius === saved}>{t("save")}</Button></Box>}
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="subtitle1" fontWeight={600}>{t("radius_by_district")}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t("radius_by_district_hint")}</Typography>
        <Table size="small" id="district-radius">
          <TableHead><TableRow><TableCell>{t("district")}</TableCell><TableCell>{t("gps_radius")}</TableCell></TableRow></TableHead>
          <TableBody>
            {rows.map((d) => (
              <TableRow key={d.id} data-district={d.name}>
                <TableCell>{d.name}</TableCell>
                <TableCell>
                  {canDistrict
                    ? <Select size="small" value={d.gps_radius_m ?? ""} displayEmpty disabled={busy} sx={{ minWidth: 170 }}
                      onChange={(e) => run(() => adminApi.saveDistrictRadius(d.id, e.target.value === "" ? null : Number(e.target.value)))}>
                      <MenuItem value="">{t("radius_common", { m: saved ?? 300 })}</MenuItem>
                      {OPTIONS.map((m) => <MenuItem key={m} value={m}>{m} m</MenuItem>)}
                    </Select>
                    : <span>{d.gps_radius_m ? `${d.gps_radius_m} m` : t("radius_common", { m: d.effective_m })}</span>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Stack>
  );
}
