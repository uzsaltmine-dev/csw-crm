import { useEffect, useId, useState } from "react";
import { Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import PhotoCameraIcon from "@mui/icons-material/PhotoCamera";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { downscale } from "@/lib/image";
import { useI18n } from "@/i18n/I18nContext";

interface Props {
  done: boolean;
  disabled?: boolean;
  facing?: "environment" | "user";
  onCapture: (blob: Blob) => Promise<void>;
}

/** Android Chrome'da `capture` atributi kamerani to'g'ridan-to'g'ri ochadi (galereya emas). */
export function PhotoCapture({ done, disabled, facing = "environment", onCapture }: Props) {
  const { t } = useI18n();
  const id = useId();
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const blob = await downscale(file);
      await onCapture(blob);
      setPreview(URL.createObjectURL(blob));
    } catch {
      // xato xabarini chaqiruvchi ko'rsatadi
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
      {preview && <Box component="img" src={preview} alt="" sx={{ width: 160, maxWidth: "100%", borderRadius: 1, border: 1, borderColor: "divider" }} />}
      <input id={id} type="file" accept="image/*" capture={facing} hidden onChange={onChange} disabled={disabled || busy} />
      <label htmlFor={id}>
        <Button component="span" variant={done ? "outlined" : "contained"} size="large" disabled={disabled || busy}
          startIcon={busy ? <CircularProgress size={18} /> : <PhotoCameraIcon />}>
          {done ? t("retake") : t("take_photo")}
        </Button>
      </label>
      {done && <Typography color="success.main" sx={{ display: "flex", gap: 0.5, alignItems: "center" }}><CheckCircleIcon fontSize="small" />{t("uploaded")}</Typography>}
    </Stack>
  );
}
