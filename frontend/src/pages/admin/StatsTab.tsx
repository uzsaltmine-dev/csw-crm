import { useEffect, useMemo, useState } from "react";
import { Box, ButtonBase, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, ToggleButton, ToggleButtonGroup, Tooltip,
  Typography } from "@mui/material";
import { statsApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import type { MessageKey } from "@/i18n/messages";
import { toast } from "@/lib/alerts";
import { formatDateTime } from "@/lib/format";
import type { StatMetrics, Stats } from "@/types";
import type { RefData } from "./AdminHome";

type Period = "today" | "month" | "last10" | "last5";
type Metric = "received" | "repeat" | "pending" | "overdue" | "done" | "not_done";
const METRICS: Metric[] = ["received", "repeat", "pending", "overdue", "done", "not_done"];
const SHARE: Partial<Record<Metric, keyof StatMetrics>> = { done: "done_share", not_done: "not_done_share" };

/**
 * Arizalar statistikasi. Kartochka bosilsa — shu ko'rsatkich tumanlar kesimida (gorizontal ustunlar, kamayish tartibida).
 * Bitta ko'rsatkich = bitta rang (kattalik); legend kerak emas — sarlavha nomlaydi. Jadval ko'rinishi ham bor.
 */
export function StatsTab(_: RefData) {
  const { t, tErr } = useI18n();
  const [period, setPeriod] = useState<Period>("today");
  const [data, setData] = useState<Stats | null>(null);
  const [metric, setMetric] = useState<Metric>("received");
  const [view, setView] = useState<"chart" | "table">("chart");

  useEffect(() => {
    statsApi.summary(period).then(setData).catch((e) => toast(tErr(errorCode(e), errorMessage(e)), "error"));
  }, [period, tErr]);

  const rows = useMemo(() => [...(data?.districts ?? [])].sort((a, b) => b[metric] - a[metric] || a.name.localeCompare(b.name)), [data, metric]);
  const max = Math.max(1, ...rows.map((r) => r[metric]));
  const label = (m: Metric) => t(`st_${m}` as MessageKey);

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }} justifyContent="space-between">
        <ToggleButtonGroup size="small" exclusive value={period} onChange={(_e, v: Period | null) => v && setPeriod(v)} id="st-period">
          {(["today", "last5", "last10", "month"] as const).map((p) => <ToggleButton key={p} value={p} sx={{ px: 2 }}>{t(`p_${p}` as MessageKey)}</ToggleButton>)}
        </ToggleButtonGroup>
        {data && <Typography variant="body2" color="text.secondary">{t("st_since", { d: formatDateTime(new Date(data.since + "Z")) })}</Typography>}
      </Stack>

      <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(3, 1fr)", lg: "repeat(6, 1fr)" } }}>
        {METRICS.map((m) => {
          const active = m === metric;
          const share = SHARE[m];
          return (
            <ButtonBase key={m} data-metric={m} onClick={() => setMetric(m)} focusRipple aria-pressed={active}
              sx={{ display: "block", textAlign: "left", p: 2, borderRadius: 2, border: 1.5, bgcolor: "background.paper",
                borderColor: active ? "primary.main" : "divider", boxShadow: active ? "0 0 0 1px var(--mui-palette-primary-main) inset" : "none",
                "&:focus-visible": { outline: "2px solid", outlineColor: "primary.main", outlineOffset: 2 } }}>
              <Typography sx={{ fontSize: 30, fontWeight: 600, lineHeight: 1.1, fontVariantNumeric: "tabular-nums" }}>{data ? data.total[m] : "—"}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{label(m)}</Typography>
              {share && data && <Typography variant="caption" color="text.secondary">{t("st_share", { p: data.total[share] })}</Typography>}
            </ButtonBase>
          );
        })}
      </Box>
      <Typography variant="caption" color="text.secondary">{t("st_click_hint")}</Typography>

      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }} spacing={1}>
          <Typography variant="subtitle1" fontWeight={600} id="st-chart-title">{t("st_by_district", { metric: label(metric) })}</Typography>
          <ToggleButtonGroup size="small" exclusive value={view} onChange={(_e, v) => v && setView(v)}>
            <ToggleButton value="chart">{t("st_chart")}</ToggleButton>
            <ToggleButton value="table">{t("st_table")}</ToggleButton>
          </ToggleButtonGroup>
        </Stack>

        {view === "chart" ? (
          <Box role="img" aria-labelledby="st-chart-title" id="st-chart" sx={{ display: "grid", gap: "2px" }}>
            {rows.map((r) => {
              const v = r[metric];
              const share = SHARE[metric];
              const tip = `${r.name}: ${v}${share ? ` (${r[share]}%)` : ""} — ${label("received")}: ${r.received}`;
              return (
                <Tooltip key={r.district_id} title={tip} placement="top" followCursor>
                  <Box data-district={r.name} sx={{ display: "grid", gridTemplateColumns: { xs: "110px 1fr 48px", sm: "170px 1fr 64px" }, alignItems: "center",
                    gap: 1.5, py: 0.75, px: 0.5, borderRadius: 1, "&:hover": { bgcolor: "action.hover" } }}>
                    <Typography variant="body2" noWrap title={r.name}>{r.name}</Typography>
                    <Box sx={{ height: 14, position: "relative" }}>
                      <Box sx={{ position: "absolute", inset: "6px 0 6px 0", bgcolor: "divider", borderRadius: 1 }} />
                      <Box sx={{ position: "relative", height: "100%", width: `${(v / max) * 100}%`, minWidth: v ? 4 : 0,
                        bgcolor: "primary.main", borderRadius: "0 4px 4px 0" }} />
                    </Box>
                    <Typography variant="body2" sx={{ textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {v}{share && <Typography component="span" variant="caption" color="text.secondary"> {r[share]}%</Typography>}
                    </Typography>
                  </Box>
                </Tooltip>
              );
            })}
          </Box>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table size="small" id="st-table">
              <TableHead><TableRow>
                <TableCell>{t("district")}</TableCell>
                {METRICS.map((m) => <TableCell key={m} align="right" sx={{ whiteSpace: "nowrap", fontWeight: m === metric ? 700 : 400 }}>{label(m)}</TableCell>)}
              </TableRow></TableHead>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.district_id}>
                    <TableCell>{r.name}</TableCell>
                    {METRICS.map((m) => <TableCell key={m} align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>
                      {r[m]}{SHARE[m] && <Typography component="span" variant="caption" color="text.secondary"> {r[SHARE[m]!]}%</Typography>}
                    </TableCell>)}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </Paper>
    </Stack>
  );
}
