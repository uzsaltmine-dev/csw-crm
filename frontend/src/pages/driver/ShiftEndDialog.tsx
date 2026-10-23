import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Stack, TextField } from "@mui/material";
import { driverApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useOnline } from "@/hooks/useOnline";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import { useAppDispatch } from "@/store";
import { refreshDriver } from "@/store/driverSlice";
import type { Shift } from "@/types";

export function ShiftEndDialog({ shift, open, onClose }: { shift: Shift; open: boolean; onClose: () => void }) {
  const { t, tErr } = useI18n();
  const online = useOnline();
  const dispatch = useAppDispatch();
  const [odometer, setOdometer] = useState("");
  const [fuel, setFuel] = useState("");
  const [busy, setBusy] = useState(false);
  const tooLow = odometer !== "" && Number(odometer) < (shift.odometer_start ?? 0);

  const submit = async () => {
    setBusy(true);
    try {
      const s = await driverApi.endShift(shift.id, Number(odometer), Number(fuel));
      toast(t("shift_summary", { km: s.distance_km ?? 0, fuel: s.fuel_used ?? 0 }));
      onClose();
      dispatch(refreshDriver());
    } catch (e) {
      toast(tErr(errorCode(e), errorMessage(e)), "error");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{t("shift_end_title")}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField id="odometer-end" label={t("odometer")} type="number" value={odometer} onChange={(e) => setOdometer(e.target.value)}
            error={tooLow} helperText={tooLow ? tErr("odometer_decreased") : `≥ ${shift.odometer_start ?? 0}`} />
          <TextField id="fuel-end" label={t("fuel")} type="number" value={fuel} onChange={(e) => setFuel(e.target.value)} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("cancel")}</Button>
        <Button variant="contained" onClick={submit} disabled={busy || !online || odometer === "" || fuel === "" || tooLow}>{t("end_shift")}</Button>
      </DialogActions>
    </Dialog>
  );
}
