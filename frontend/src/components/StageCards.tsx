import type { ReactNode } from "react";
import { Box, Chip, Stack, Typography } from "@mui/material";
import { useI18n } from "@/i18n/I18nContext";
import { formatDateTime } from "@/lib/format";
import { RequestChips } from "@/pages/operator/OperatorHome";
import type { DriverTask } from "@/types";

type Card = Omit<DriverTask, "files">;
import { CopyValue, RedTimer, STAGE, SinceTimer, redColor, hoursSince } from "./Stage";

const dt = (s?: string | null) => (s ? formatDateTime(new Date(s + "Z")) : "—");

/** Qizil karta: mashina biriktirilmagan. Rang 72 soat davomida to'qlashadi, keyin qora. */
export function RedCard({ r, now, children, isNew }: { r: Card; now: number; children?: ReactNode; isNew?: boolean }) {
  const { t } = useI18n();
  const h = hoursSince(r.created_at, now);
  return (
    <Box data-card="red" data-request={r.number} data-new={isNew || undefined}
      sx={{ bgcolor: redColor(h), color: "#fff", borderRadius: 2, p: 2, boxShadow: isNew ? "0 0 0 3px #ffb4b4" : "0 1px 3px rgba(0,0,0,.25)",
        transition: "background-color .6s", "& .MuiChip-outlined": { color: "#fff", borderColor: "rgba(255,255,255,.7)" } }}>
      <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="flex-start">
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography sx={{ fontWeight: 700, fontSize: 17 }}>{r.number} · {r.customer.name}</Typography>
            {isNew && <Chip size="small" label={t("rq_new_badge")} sx={{ bgcolor: "#fff", color: "#b71c1c", fontWeight: 700, height: 20 }} />}
            {h >= 72 && <Chip size="small" label={t("stg_overdue")} sx={{ bgcolor: "#ffeb3b", color: "#000", fontWeight: 700, height: 20 }} />}
          </Stack>
          <Typography variant="body2" sx={{ opacity: 0.9 }}>{r.customer.address} · {t("created")}: {dt(r.created_at)}</Typography>
          <Stack direction="row" spacing={2.5} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
            <CopyValue value={r.customer.code} label={t("cust_code")} big />
            <CopyValue value={r.customer.stir} label="STIR" />
          </Stack>
          <Stack direction="row" spacing={0.5} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap><RequestChips r={r} /></Stack>
        </Box>
        <RedTimer createdAt={r.created_at} now={now} />
      </Stack>
      {children && <Box sx={{ mt: 1.5 }}>{children}</Box>}
    </Box>
  );
}

/** Sariq karta: mashina biriktirilgan, chiqindi olinishi va varaqa qaytishi kutilmoqda. */
export function YellowCard({ r, now, children, isNew }: { r: Card; now: number; children?: ReactNode; isNew?: boolean }) {
  const { t } = useI18n();
  const f = r.order_form;
  const c = STAGE.yellow;
  return (
    <Box data-card="yellow" data-request={r.number} data-new={isNew || undefined}
      sx={{ bgcolor: c.bg, color: c.ink, border: 2, borderColor: isNew ? c.strong : c.border, borderRadius: 2, p: 2 }}>
      <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="flex-start">
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography sx={{ fontWeight: 700, fontSize: 17 }}>{r.customer.name}</Typography>
            {isNew && <Chip size="small" label={t("rq_new_badge")} sx={{ bgcolor: c.strong, color: "#fff", height: 20 }} />}
            {r.status === "failed" && <Chip size="small" color="error" label={t("s_failed")} sx={{ height: 20 }} />}
            {f?.locked && <Chip size="small" color="error" label={t("of_locked")} sx={{ height: 20 }} />}
          </Stack>
          <Stack direction="row" spacing={2.5} sx={{ mt: 0.75 }} flexWrap="wrap" useFlexGap alignItems="flex-end">
            <CopyValue value={r.customer.code} label={t("cust_code")} big id={`code-${r.id}`} />
            <CopyValue value={r.customer.stir} label="STIR" />
          </Stack>
          <Typography variant="body2" sx={{ mt: 0.75 }}>
            {r.number}{f && <> · {t(f.printed ? "of_is_printed" : "of_not_printed")}</>}
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.85 }}>
            🚛 {r.vehicle?.plate ?? "—"} · {r.driver_name ?? "—"} · {r.customer.address ?? ""}
          </Typography>
        </Box>
        <SinceTimer since={r.assigned_at} now={now} label={t("stg_since_assigned")} />
      </Stack>
      {children && <Box sx={{ mt: 1.5 }}>{children}</Box>}
    </Box>
  );
}

/** Yashil karta: bajarilgan. */
export function GreenCard({ r, children }: { r: Card; children?: ReactNode }) {
  const { t } = useI18n();
  const f = r.order_form;
  const c = STAGE.green;
  return (
    <Box data-card="green" data-request={r.number} sx={{ bgcolor: c.bg, color: c.ink, border: 1.5, borderColor: c.border, borderRadius: 2, p: 1.75 }}>
      <Stack direction="row" spacing={2} justifyContent="space-between" alignItems="flex-start">
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography sx={{ fontWeight: 700 }}>{r.customer.name}</Typography>
            <Typography sx={{ fontFamily: "ui-monospace, monospace", fontWeight: 700 }}>{r.customer.code}</Typography>
            {r.status === "suspect" && <Chip size="small" color="warning" label={t("s_suspect")} sx={{ height: 20 }} />}
          </Stack>
          <Typography variant="body2">
            {r.number} · {t("of_no")}: {f?.number ?? "—"} · 🚛 {r.vehicle?.plate ?? "—"} · {r.driver_name ?? "—"}
          </Typography>
          {f?.volume_m3 != null && <Typography variant="body2">
            {f.volume_m3} m³ · {t(f.waste_kind === "liquid" ? "of_liquid" : "of_solid")} · {t(f.closed_via === "act" ? "of_via_act" : "of_via_form")}
          </Typography>}
        </Box>
        <Box sx={{ textAlign: "right" }}>
          <Typography variant="caption" sx={{ display: "block" }}>{t("rq_finished")}</Typography>
          <Typography variant="body2" fontWeight={600} sx={{ fontVariantNumeric: "tabular-nums" }}>{dt(r.finished_at)}</Typography>
        </Box>
      </Stack>
      {children && <Box sx={{ mt: 1 }}>{children}</Box>}
    </Box>
  );
}
