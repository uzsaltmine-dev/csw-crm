import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, Chip, CircularProgress, MenuItem, Paper, Stack, Tab, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Tabs, TextField, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { accountingApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import type { MessageKey } from "@/i18n/messages";
import { toast } from "@/lib/alerts";
import type { CompanyCompare, GreenItem } from "@/types";
import { fmtM3, fmtMoney } from "./CompaniesTab";

type View = "debit" | "credit" | "volume";
type Range = [string, string];
const iso = (d: Date) => d.toISOString().slice(0, 10);
const today = () => new Date(Date.now() + 5 * 3600_000);

/** Tayyor davrlar: shu oy, o'tgan oy, shu chorak, o'tgan chorak, shu yil, o'tgan yil. */
function preset(key: string): Range {
  const n = today(), y = n.getUTCFullYear(), m = n.getUTCMonth();
  const D = (yy: number, mm: number, dd: number) => iso(new Date(Date.UTC(yy, mm, dd)));
  const q = Math.floor(m / 3) * 3;
  switch (key) {
    case "this_month": return [D(y, m, 1), iso(n)];
    case "last_month": return [D(y, m - 1, 1), D(y, m, 0)];
    case "this_quarter": return [D(y, q, 1), iso(n)];
    case "last_quarter": return [D(y, q - 3, 1), D(y, q, 0)];
    case "this_year": return [D(y, 0, 1), iso(n)];
    default: return [D(y - 1, 0, 1), D(y - 1, 11, 31)];
  }
}
const PRESETS = ["this_month", "last_month", "this_quarter", "last_quarter", "this_year", "last_year"];

function PeriodPicker({ id, label, value, onChange }: { id: string; label: string; value: Range; onChange: (r: Range) => void }) {
  const { t } = useI18n();
  return (
    <Paper variant="outlined" sx={{ p: 1.5, flex: 1 }} id={id}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>{label}</Typography>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <TextField select size="small" label={t("cp_preset")} value="" onChange={(e) => onChange(preset(e.target.value))} sx={{ minWidth: 150 }}>
          {PRESETS.map((p) => <MenuItem key={p} value={p}>{t(`cp_${p}` as MessageKey)}</MenuItem>)}
        </TextField>
        <TextField size="small" type="date" label={t("date_from")} value={value[0]} onChange={(e) => onChange([e.target.value, value[1]])}
          InputLabelProps={{ shrink: true }} inputProps={{ "data-from": true }} />
        <TextField size="small" type="date" label={t("date_to")} value={value[1]} onChange={(e) => onChange([value[0], e.target.value])}
          InputLabelProps={{ shrink: true }} inputProps={{ "data-to": true }} />
      </Stack>
    </Paper>
  );
}

function Diff({ a, b, good }: { a: number; b: number; good: "up" | "down" }) {
  const d = b - a;
  const pct = a ? Math.round((d / Math.abs(a)) * 1000) / 10 : null;
  const better = good === "up" ? d > 0 : d < 0;
  if (!d) return <Chip size="small" label="0" />;
  return <Chip size="small" color={better ? "success" : "error"} data-diff
    label={`${d > 0 ? "+" : "−"}${fmtMoney(Math.abs(d))}${pct !== null ? ` (${d > 0 ? "+" : "−"}${Math.abs(pct)}%)` : ""}`} />;
}

/** Korxona sahifasi: debitor yoki kreditor — ikki davrni solishtirish; kub — barcha yashil murojaatlar (har birining kubi). */
export function CompanyPage() {
  const { t, tErr } = useI18n();
  const nav = useNavigate();
  const loc = useLocation();
  // Ortga — qaysi bo'limdan kelingan bo'lsa o'sha (yo'q bo'lsa rol bo'yicha Korxonalar)
  const back = (loc.state as { from?: string } | null)?.from ?? "/admin#companies";
  const { id, view: v } = useParams();
  const cid = Number(id);
  const view: View = v === "credit" || v === "volume" ? v : "debit";
  const [a, setA] = useState<Range>(preset("last_month"));
  const [b, setB] = useState<Range>(preset("this_month"));
  const [cmp, setCmp] = useState<CompanyCompare | null>(null);
  const [green, setGreen] = useState<{ items: GreenItem[]; total_m3: number; count: number; customer: CompanyCompare["customer"] } | null>(null);
  const fail = (e: unknown) => toast(tErr(errorCode(e), errorMessage(e)), "error");

  useEffect(() => {
    if (view === "volume") accountingApi.green(cid).then(setGreen).catch(fail);
    else if (a[0] && a[1] && b[0] && b[1]) accountingApi.compare(cid, a, b).then(setCmp).catch(fail);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cid, view, a[0], a[1], b[0], b[1]]);

  const cust = (view === "volume" ? green?.customer : cmp?.customer);
  const isDebit = view === "debit";
  const chart = useMemo(() => (cmp?.months ?? []).map((m) => ({ ...m, label: m.month.slice(5) + "." + m.month.slice(2, 4) })), [cmp]);

  return (
    <Stack spacing={2} id="company-page">
      <Stack direction="row" spacing={1} alignItems="center">
        <Button startIcon={<ArrowBackIcon />} onClick={() => nav(back)}>{t("back")}</Button>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h5" noWrap>{cust?.name ?? "…"}</Typography>
          <Typography color="text.secondary"><b style={{ fontFamily: "ui-monospace, monospace" }}>{cust?.code}</b>{cust?.stir && ` · STIR ${cust.stir}`}</Typography>
        </Box>
      </Stack>
      <Paper variant="outlined">
        <Tabs value={view} onChange={(_, x) => nav(`/admin/korxona/${cid}/${x}`, { replace: true, state: loc.state })}>
          <Tab value="debit" id="cp-tab-debit" label={t("cmp_debit")} />
          <Tab value="credit" id="cp-tab-credit" label={t("cmp_credit")} />
          <Tab value="volume" id="cp-tab-volume" label={t("cmp_volume")} />
        </Tabs>
      </Paper>

      {view !== "volume" && <>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <PeriodPicker id="period-a" label={t("cp_period1")} value={a} onChange={setA} />
          <PeriodPicker id="period-b" label={t("cp_period2")} value={b} onChange={setB} />
        </Stack>
        {!cmp ? <CircularProgress size={24} /> : <>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>{t(isDebit ? "cp_debit_title" : "cp_credit_title")}</Typography>
            <TableContainer>
              <Table size="small" id="compare-table">
                <TableHead><TableRow>
                  <TableCell />
                  <TableCell align="right">{t("cp_period1")}<br /><Typography variant="caption">{cmp.periods[0].from} — {cmp.periods[0].to}</Typography></TableCell>
                  <TableCell align="right">{t("cp_period2")}<br /><Typography variant="caption">{cmp.periods[1].from} — {cmp.periods[1].to}</Typography></TableCell>
                  <TableCell align="right">{t("cp_diff")}</TableCell>
                </TableRow></TableHead>
                <TableBody>
                  {([[isDebit ? "debit" : "credit", "cp_end", isDebit ? "down" : "up"], ["charged", "cp_charged", "up"], ["paid", "cp_paid", "up"],
                    ["opening", "cp_opening", "down"]] as const).map(([k, label, good]) => (
                    <TableRow key={k} data-line={k} sx={k === "debit" || k === "credit" ? { "& td": { fontWeight: 700, fontSize: 15 } } : undefined}>
                      <TableCell>{t(label)}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmtMoney(cmp.periods[0][k])}</TableCell>
                      <TableCell align="right" sx={{ fontVariantNumeric: "tabular-nums" }}>{fmtMoney(cmp.periods[1][k])}</TableCell>
                      <TableCell align="right"><Diff a={cmp.periods[0][k]} b={cmp.periods[1][k]} good={good} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1 }}>{t("cp_hint")}</Typography>
          </Paper>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1 }}>{t("cp_months")}</Typography>
            <Box sx={{ height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={chart} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
                  <CartesianGrid vertical={false} strokeOpacity={0.3} />
                  <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
                  <YAxis tickFormatter={(v) => `${Math.round(v / 1000)}k`} tickLine={false} axisLine={false} fontSize={12} width={48} />
                  <Tooltip formatter={(v: number, n: string) => [fmtMoney(v), n]} />
                  <Legend />
                  <Bar dataKey="charged" name={t("cp_charged")} fill="#c98a00" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="paid" name={t("cp_paid")} fill="#1f8a4c" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Box>
            <Table size="small" sx={{ mt: 1 }}>
              <TableHead><TableRow><TableCell>{t("cp_month")}</TableCell><TableCell align="right">{t("cp_charged")}</TableCell>
                <TableCell align="right">{t("cp_paid")}</TableCell><TableCell align="right">{t("cp_balance_end")}</TableCell></TableRow></TableHead>
              <TableBody>{cmp.months.map((m) => (
                <TableRow key={m.month}><TableCell>{m.month}</TableCell><TableCell align="right">{fmtMoney(m.charged)}</TableCell>
                  <TableCell align="right">{fmtMoney(m.paid)}</TableCell>
                  <TableCell align="right" sx={{ color: m.closing > 0 ? "error.main" : m.closing < 0 ? "success.main" : undefined }}>
                    {m.closing > 0 ? `${t("cmp_debit")}: ${fmtMoney(m.closing)}` : m.closing < 0 ? `${t("cmp_credit")}: ${fmtMoney(-m.closing)}` : "0"}</TableCell>
                </TableRow>))}</TableBody>
            </Table>
          </Paper>
        </>}
      </>}

      {view === "volume" && (!green ? <CircularProgress size={24} /> : <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="baseline" sx={{ mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600}>{t("cp_green_title", { n: green.count })}</Typography>
          <Typography sx={{ fontWeight: 700, fontSize: 20 }} data-total>{fmtM3(green.total_m3)}</Typography>
        </Stack>
        {!green.items.length ? <Alert severity="info">{t("ord_no_green")}</Alert> : <TableContainer>
          <Table size="small" id="green-table">
            <TableHead><TableRow>
              <TableCell>{t("date")}</TableCell><TableCell>{t("rq_number")}</TableCell><TableCell align="right">{t("cp_m3")}</TableCell>
              <TableCell>{t("waste_type")}</TableCell><TableCell>{t("vehicle")}</TableCell><TableCell>{t("rq_driver")}</TableCell>
              <TableCell>{t("cp_closed")}</TableCell><TableCell align="right">{t("cp_amount")}</TableCell>
            </TableRow></TableHead>
            <TableBody>{green.items.map((g) => (
              <TableRow key={g.id} data-green={g.number}>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{g.day}</TableCell><TableCell>{g.number}</TableCell>
                <TableCell align="right" sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{fmtM3(g.volume_m3)}</TableCell>
                <TableCell>{t(`wt_${g.waste_type}` as MessageKey)}</TableCell><TableCell>{g.plate ?? "—"}</TableCell><TableCell>{g.driver_name ?? "—"}</TableCell>
                <TableCell>{g.closed_via ? t(g.closed_via === "act" ? "of_via_act" : "of_via_form") : "—"}</TableCell>
                <TableCell align="right">{g.amount ? fmtMoney(g.amount) : "—"}</TableCell>
              </TableRow>))}
              <TableRow sx={{ "& td": { fontWeight: 700 } }}><TableCell colSpan={2}>{t("st_total")}</TableCell>
                <TableCell align="right">{fmtM3(green.total_m3)}</TableCell><TableCell colSpan={5} /></TableRow>
            </TableBody>
          </Table>
        </TableContainer>}
      </Paper>)}
    </Stack>
  );
}
