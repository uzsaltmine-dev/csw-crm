import { useState } from "react";
import { Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { driverApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { PhotoCapture } from "@/components/PhotoCapture";
import { useOnline } from "@/hooks/useOnline";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import { useAppDispatch } from "@/store";
import { refreshDriver } from "@/store/driverSlice";
import type { Shift } from "@/types";

/** Smena boshi: mashina rasmi, spidometr va yoqilg'i (GPS xodimi smenani ochgandan keyin). */
export function ShiftStart({ shift }: { shift: Shift }) {
  const { t, tErr } = useI18n();
  const online = useOnline();
  const dispatch = useAppDispatch();
  const [photo, setPhoto] = useState<Blob | null>(null);
  const [odometer, setOdometer] = useState("");
  const [fuel, setFuel] = useState("");
  const [busy, setBusy] = useState(false);
  const valid = photo && odometer !== "" && fuel !== "" && Number(odometer) >= 0 && Number(fuel) >= 0;

  const submit = async () => {
    if (!valid) return;
    setBusy(true);
    try {
      await driverApi.startShift(shift.id, Number(odometer), Number(fuel), photo);
      toast(t("shift_started_at"));
      dispatch(refreshDriver());
    } catch (e) {
      toast(tErr(errorCode(e), errorMessage(e)), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack spacing={2.5}>
        <Typography variant="h6">{t("shift_start_title")}</Typography>
        <Typography>{t("vehicle")}: <b>{shift.vehicle.plate}</b>{shift.vehicle.model ? ` · ${shift.vehicle.model}` : ""}</Typography>
        <Stack spacing={1}>
          <Typography variant="subtitle2">{t("vehicle_photo")}</Typography>
          <PhotoCapture done={!!photo} onCapture={async (b) => setPhoto(b)} />
        </Stack>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField id="odometer" label={t("odometer")} type="number" inputMode="numeric" value={odometer}
            onChange={(e) => setOdometer(e.target.value)} slotProps={{ htmlInput: { min: 0 } }} fullWidth />
          <TextField id="fuel" label={t("fuel")} type="number" inputMode="decimal" value={fuel}
            onChange={(e) => setFuel(e.target.value)} slotProps={{ htmlInput: { min: 0, step: 0.1 } }} fullWidth />
        </Stack>
        <Button variant="contained" size="large" onClick={submit} disabled={!valid || busy || !online}>{t("start_shift")}</Button>
      </Stack>
    </Paper>
  );
}
