import { useEffect, useState } from "react";
import { Box, Button, Dialog, FormControlLabel, Radio, RadioGroup, Stack, Typography } from "@mui/material";

/** shadcn/ui AlertDialog uslubidagi tasdiqlash/tanlash oynasi. Bitta DialogHost butun ilova uchun. */
export interface DialogRequest {
  kind: "confirm" | "choose";
  title: string;
  description?: string;
  options?: { value: string; label: string }[];
  confirmText: string;
  cancelText: string;
  destructive?: boolean;
}
type Pending = DialogRequest & { resolve: (v: unknown) => void };

let push: ((p: Pending) => void) | null = null;

export function openDialog<T>(req: DialogRequest): Promise<T | null> {
  return new Promise((resolve) => {
    if (!push) { resolve(null); return; }
    push({ ...req, resolve: resolve as (v: unknown) => void });
  });
}

export function DialogHost() {
  const [cur, setCur] = useState<Pending | null>(null);
  const [choice, setChoice] = useState("");
  useEffect(() => {
    push = (p) => { setChoice(p.options?.[0]?.value ?? ""); setCur(p); };
    return () => { push = null; };
  }, []);
  const close = (value: unknown) => { cur?.resolve(value); setCur(null); };

  return (
    <Dialog open={!!cur} onClose={() => close(null)} maxWidth="xs" fullWidth
      PaperProps={{ sx: { borderRadius: 2, border: 1, borderColor: "divider", boxShadow: "0 10px 38px -10px rgba(22,23,24,.35), 0 10px 20px -15px rgba(22,23,24,.2)" } }}>
      {cur && <Box sx={{ p: 3 }} role="alertdialog" aria-labelledby="dlg-title">
        <Typography id="dlg-title" variant="h6" sx={{ fontSize: 18, fontWeight: 600, lineHeight: 1.3 }}>{cur.title}</Typography>
        {cur.description && <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{cur.description}</Typography>}
        {cur.kind === "choose" && <RadioGroup value={choice} onChange={(e) => setChoice(e.target.value)} sx={{ mt: 1.5 }}>
          {cur.options?.map((o) => <FormControlLabel key={o.value} value={o.value} control={<Radio size="small" />} label={o.label}
            sx={{ mx: 0, px: 1, py: 0.25, borderRadius: 1, "&:hover": { bgcolor: "action.hover" } }} />)}
        </RadioGroup>}
        <Stack direction={{ xs: "column-reverse", sm: "row" }} spacing={1} justifyContent="flex-end" sx={{ mt: 3 }}>
          <Button variant="outlined" color="inherit" sx={{ borderColor: "divider" }} onClick={() => close(null)}>{cur.cancelText}</Button>
          <Button variant="contained" color={cur.destructive ? "error" : "primary"} disableElevation autoFocus
            onClick={() => close(cur.kind === "choose" ? choice : true)}>{cur.confirmText}</Button>
        </Stack>
      </Box>}
    </Dialog>
  );
}
