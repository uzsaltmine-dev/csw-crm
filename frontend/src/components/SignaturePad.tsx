import { useEffect, useRef, useState } from "react";
import { Box, Button, Stack } from "@mui/material";
import { useI18n } from "@/i18n/I18nContext";

interface Props { disabled?: boolean; onSave: (png: Blob) => Promise<void> }

export function SignaturePad({ disabled, onSave }: Props) {
  const { t } = useI18n();
  const ref = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ctx = ref.current!.getContext("2d")!;
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.strokeStyle = "#1b2a22";
  }, []);

  const point = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const c = ref.current!, r = c.getBoundingClientRect();
    return [((e.clientX - r.left) * c.width) / r.width, ((e.clientY - r.top) * c.height) / r.height] as const;
  };

  const down = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (disabled) return;
    drawing.current = true;
    ref.current!.setPointerCapture(e.pointerId);
    const ctx = ref.current!.getContext("2d")!, [x, y] = point(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
  };
  const move = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    const ctx = ref.current!.getContext("2d")!, [x, y] = point(e);
    ctx.lineTo(x, y);
    ctx.stroke();
    setDirty(true);
  };
  const up = () => { drawing.current = false; };
  const clear = () => {
    const c = ref.current!;
    c.getContext("2d")!.clearRect(0, 0, c.width, c.height);
    setDirty(false);
  };
  const save = async () => {
    setBusy(true);
    try {
      const blob = await new Promise<Blob>((res, rej) => ref.current!.toBlob((b) => (b ? res(b) : rej(new Error("empty"))), "image/png"));
      await onSave(blob);
    } catch {
      // xato xabarini chaqiruvchi ko'rsatadi
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack spacing={1}>
      <Box component="canvas" ref={ref} width={900} height={260} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
        sx={{ width: "100%", height: 180, bgcolor: "#fff", border: 1, borderStyle: "dashed", borderColor: "divider", borderRadius: 1, touchAction: "none" }} />
      <Stack direction="row" spacing={1}>
        <Button onClick={clear} disabled={disabled || !dirty}>{t("clear")}</Button>
        <Button variant="contained" onClick={save} disabled={disabled || !dirty || busy}>{t("save_sign")}</Button>
      </Stack>
    </Stack>
  );
}
