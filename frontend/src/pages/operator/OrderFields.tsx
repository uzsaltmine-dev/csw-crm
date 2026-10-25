import { Box, MenuItem, TextField } from "@mui/material";
import { useI18n } from "@/i18n/I18nContext";
import type { MessageKey } from "@/i18n/messages";
import type { RequestSource, WasteType } from "@/types";

export const WASTE_TYPES: WasteType[] = ["household", "construction", "bulky", "green", "septic"];
export const SOURCES: RequestSource[] = ["phone", "telegram", "excel", "walk_in"];

export type Order = { waste_type: WasteType; volume_estimate: string; preferred_time: string; note: string;
  caller_name: string; caller_phone: string; source: RequestSource };
export const EMPTY_ORDER: Order = { waste_type: "household", volume_estimate: "", preferred_time: "", note: "", caller_name: "", caller_phone: "", source: "phone" };

export function orderBody(o: Order) {
  const opt = (v: string) => v.trim() || null;
  return { waste_type: o.waste_type, volume_estimate: o.volume_estimate ? Number(o.volume_estimate) : null, preferred_time: opt(o.preferred_time),
    note: opt(o.note), caller_name: opt(o.caller_name), caller_phone: opt(o.caller_phone), source: o.source };
}

/** Buyurtma maydonlari: ariza ham, birinchi murojaat ham shu bilan to'ldiriladi. */
export function OrderFields({ value, onChange, idPrefix = "o" }: { value: Order; onChange: (o: Order) => void; idPrefix?: string }) {
  const { t } = useI18n();
  const set = (k: keyof Order) => (e: React.ChangeEvent<HTMLInputElement>) => onChange({ ...value, [k]: e.target.value });
  return (
    <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
      <TextField id={`${idPrefix}-waste`} size="small" select label={t("waste_type")} value={value.waste_type} onChange={set("waste_type")}>
        {WASTE_TYPES.map((w) => <MenuItem key={w} value={w}>{t(`wt_${w}` as MessageKey)}</MenuItem>)}
      </TextField>
      <TextField id={`${idPrefix}-source`} size="small" select label={t("source")} value={value.source} onChange={set("source")}>
        {SOURCES.map((s) => <MenuItem key={s} value={s}>{t(`src_${s}` as MessageKey)}</MenuItem>)}
      </TextField>
      <TextField id={`${idPrefix}-volume`} size="small" type="number" label={t("volume_estimate")} value={value.volume_estimate}
        onChange={set("volume_estimate")} slotProps={{ htmlInput: { min: 0.5, step: 0.5, inputMode: "decimal" } }} />
      <TextField id={`${idPrefix}-time`} size="small" label={t("preferred_time")} value={value.preferred_time} placeholder="09:00–12:00"
        onChange={set("preferred_time")} />
      <TextField id={`${idPrefix}-caller`} size="small" label={t("caller_name")} value={value.caller_name} onChange={set("caller_name")} />
      <TextField id={`${idPrefix}-caller-phone`} size="small" label={t("caller_phone")} value={value.caller_phone} placeholder="94 512 11 16"
        onChange={set("caller_phone")} />
      <TextField id={`${idPrefix}-note`} size="small" label={t("f_note")} value={value.note} multiline minRows={2}
        onChange={set("note")} sx={{ gridColumn: { sm: "1 / -1" } }} />
    </Box>
  );
}
