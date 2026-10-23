import { useEffect, useState } from "react";
import { Box, Button, Paper, Slider, Stack, Typography } from "@mui/material";
import { adminApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import type { RefData } from "./AdminHome";

const MARKS = [100, 150, 200, 250, 300].map((v) => ({ value: v, label: `${v} m` }));

export function SettingsTab({ canWrite }: RefData) {
  const { t, tErr } = useI18n();
  const [saved, setSaved] = useState<number | null>(null);
  const [radius, setRadius] = useState(300);
  const [busy, setBusy] = useState(false);

  useEffect(() => { adminApi.settings().then((s) => { setSaved(s.gps_radius_m); setRadius(s.gps_radius_m); }).catch(() => undefined); }, []);

  const save = async () => {
    setBusy(true);
    try { const s = await adminApi.saveSettings(radius); setSaved(s.gps_radius_m); toast(t("saved")); }
    catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); }
    finally { setBusy(false); }
  };

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack spacing={2} sx={{ maxWidth: 520 }}>
        <Typography variant="subtitle1" fontWeight={600}>{t("gps_radius")}: <span style={{ fontFamily: "monospace" }}>{radius} m</span></Typography>
        <Typography variant="body2" color="text.secondary">{t("gps_radius_hint")}</Typography>
        <Box sx={{ px: 1 }}>
          <Slider value={radius} min={100} max={300} step={10} marks={MARKS} disabled={!canWrite || saved === null}
            onChange={(_, v) => setRadius(v as number)} aria-label={t("gps_radius")} />
        </Box>
        {canWrite && <Box><Button variant="contained" onClick={save} disabled={busy || saved === null || radius === saved}>{t("save")}</Button></Box>}
      </Stack>
    </Paper>
  );
}
