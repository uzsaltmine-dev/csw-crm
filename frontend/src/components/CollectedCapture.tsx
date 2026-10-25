import { useEffect, useId, useRef, useState } from "react";
import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Link, Stack, Typography } from "@mui/material";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import PlaceIcon from "@mui/icons-material/Place";
import { distanceM } from "@/hooks/useGeolocation";
import { useI18n } from "@/i18n/I18nContext";
import { formatDateTime } from "@/lib/format";
import { downscale } from "@/lib/image";
import type { Coords, Customer } from "@/types";

interface Props {
  disabled: boolean;
  busy: boolean;
  online: boolean;
  coords: Coords | null;     // jonli GPS; rasm olingan paytdagi qiymati muzlatiladi
  customer: Customer;
  onSubmit: (photo: Blob, at: Coords) => Promise<void> | void;
}

/**
 * "Chiqindi olib ketildi" tugmasi: bosilganda planshet kamerasi ochiladi (capture — galereya emas).
 * Rasm olingach oynada rasm va u olingan joy (GPS, aniqlik, vaqt) ko'rsatiladi; haydovchi "Dalolatnomani yuborish"ni bosadi.
 */
export function CollectedCapture({ disabled, busy, online, coords, customer, onSubmit }: Props) {
  const { t } = useI18n();
  const id = useId();
  const [photo, setPhoto] = useState<{ blob: Blob; url: string; at: Coords; time: Date } | null>(null);
  const [processing, setProcessing] = useState(false);
  const [gpsMissing, setGpsMissing] = useState(false);
  const live = useRef(coords);
  live.current = coords;
  useEffect(() => () => { if (photo) URL.revokeObjectURL(photo.url); }, [photo]);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const at = live.current; // rasm olingan paytdagi joylashuv
    if (!at) { setGpsMissing(true); return; }
    setGpsMissing(false);
    setProcessing(true);
    try {
      const blob = await downscale(file);
      setPhoto({ blob, url: URL.createObjectURL(blob), at: { ...at }, time: new Date() });
    } finally { setProcessing(false); }
  };
  const close = () => { if (!busy) { setPhoto(null); setGpsMissing(false); } };

  const c = customer;
  const dist = photo && c.location_status === "confirmed" && c.lat !== null && c.lng !== null ? distanceM(photo.at, { lat: c.lat, lng: c.lng }) : null;
  const cameraButton = (variant: "contained" | "outlined", label: string, btnId?: string) => (
    <label htmlFor={id}>
      <Button id={btnId} component="span" variant={variant} size="large" startIcon={processing ? <CircularProgress size={18} /> : <PhotoCameraIcon />}
        disabled={disabled || busy || processing}>{label}</Button>
    </label>
  );

  return (
    <>
      <input id={id} type="file" accept="image/*" capture="environment" hidden onChange={onFile} disabled={disabled || busy} />
      {cameraButton("contained", t("waste_collected"), "collected-btn")}

      <Dialog open={!!photo || gpsMissing} onClose={close} fullWidth maxWidth="sm">
        <DialogTitle>{t("waste_collected")}</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2}>
            {gpsMissing && <Alert severity="warning">{t("err_gps_required")}</Alert>}
            {photo && <>
              <Box component="img" src={photo.url} alt={t("waste_collected")} id="collected-preview"
                sx={{ width: "100%", maxHeight: 360, objectFit: "contain", borderRadius: 1, border: 1, borderColor: "divider", bgcolor: "action.hover" }} />
              <Stack direction="row" spacing={1.5} alignItems="flex-start" id="collected-location">
                <PlaceIcon color="primary" />
                <Box>
                  <Typography sx={{ fontVariantNumeric: "tabular-nums" }}>{photo.at.lat.toFixed(6)}, {photo.at.lng.toFixed(6)}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    {t("gps_accuracy", { m: photo.at.accuracy ?? "?" })}, {formatDateTime(photo.time)}
                    {dist !== null && <>, {t("distance_to", { m: dist })}</>}
                  </Typography>
                  <Link variant="body2" href={`https://www.google.com/maps?q=${photo.at.lat},${photo.at.lng}`} target="_blank" rel="noopener">{t("open_map")}</Link>
                </Box>
              </Stack>
              <Typography variant="body2" color="text.secondary">{t("collected_hint")}</Typography>
            </>}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 2, gap: 1, flexWrap: "wrap" }}>
          <Button onClick={close} disabled={busy}>{t("cancel")}</Button>
          {cameraButton("outlined", photo ? t("retake") : t("take_photo"))}
          {photo && <Button id="send-act" variant="contained" size="large" disabled={busy || !online}
            onClick={() => onSubmit(photo.blob, photo.at)}>{busy ? t("sending") : t("send_act")}</Button>}
        </DialogActions>
      </Dialog>
    </>
  );
}
