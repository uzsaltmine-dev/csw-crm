import { useEffect, useMemo, useRef, useState } from "react";
import { Box, ButtonBase, InputAdornment, Link, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TableSortLabel,
  TextField, Typography } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import { useNavigate } from "react-router-dom";
import { accountingApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { STAGE } from "@/components/Stage";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import { getSocket } from "@/lib/socket";
import type { CompanyRow } from "@/types";
import type { RefData } from "./AdminHome";

type Key = "name" | "code" | "debit" | "credit" | "volume_m3";
export const fmtMoney = (v: number) => `${Math.round(v).toLocaleString("ru-RU").replace(/ /g, " ")} so'm`;
export const fmtM3 = (v: number) => `${(Math.round(v * 100) / 100).toLocaleString("ru-RU")} m³`;

/** Legal/buxgalter «Korxonalar»: faqat statistika — shartnomasi bor korxonalar soni (yashil panel) va saralanadigan jadval.
 *  Har bir son bosilsa yangi sahifa: debitor/kreditor — ikki davrni solishtirish, kub — yashil murojaatlar. */
export function CompaniesTab({ districts, districtId, showDistrict, hidePanel, backTo = "/admin#companies" }: RefData & { districtId?: number;
  showDistrict?: boolean; hidePanel?: boolean; backTo?: string }) {
  const { t, tErr } = useI18n();
  const nav = useNavigate();
  const [data, setData] = useState<Awaited<ReturnType<typeof accountingApi.companies>> | null>(null);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<{ key: Key; dir: "asc" | "desc" }>({ key: "name", dir: "asc" });
  const table = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = () => accountingApi.companies(undefined, districtId).then(setData).catch((e) => toast(tErr(errorCode(e), errorMessage(e)), "error"));
    load();
    // Murojaat yashil bo'lsa (kub, debitor) jadval darhol yangilanadi
    const s = getSocket();
    s.on("request:updated", load);
    return () => { s.off("request:updated", load); };
  }, [tErr, districtId]);

  const rows = useMemo(() => {
    const t0 = q.trim().toLowerCase();
    const list = (data?.items ?? []).filter((r) => !t0 || r.name.toLowerCase().includes(t0) || (r.code ?? "").toLowerCase().includes(t0));
    const k = sort.key, m = sort.dir === "asc" ? 1 : -1;
    return [...list].sort((a, b) => m * (k === "name" || k === "code"
      ? String(a[k] ?? "").localeCompare(String(b[k] ?? ""), "uz") : (a[k] as number) - (b[k] as number)));
  }, [data, q, sort]);
  const head = (k: Key, label: string, right = false) => (
    <TableCell align={right ? "right" : "left"} sortDirection={sort.key === k ? sort.dir : false}>
      <TableSortLabel data-sort={k} active={sort.key === k} direction={sort.key === k ? sort.dir : "asc"}
        onClick={() => setSort((s) => ({ key: k, dir: s.key === k && s.dir === "asc" ? "desc" : "asc" }))}>{label}</TableSortLabel>
    </TableCell>
  );
  // Ortga: sahifa qaysi bo'limdan ochilgan bo'lsa o'shanga qaytadi (admin/manager — Korxonalar › Statistika)
  const go = (r: CompanyRow, view: string) => nav(`/admin/korxona/${r.customer_id}/${view}`, { state: { from: backTo } });
  const num = (r: CompanyRow, view: string, text: string, color?: string) => (
    <Link component="button" data-go={`${r.customer_id}-${view}`} onClick={() => go(r, view)} underline="hover"
      sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 600, color: color ?? "inherit", textAlign: "right" }}>{text}</Link>
  );

  return (
    <Stack spacing={2}>
      {!hidePanel && <ButtonBase id="contracted-panel" focusRipple onClick={() => table.current?.scrollIntoView({ behavior: "smooth", block: "start" })}
        sx={{ display: "block", textAlign: "left", borderRadius: 2, p: 3, bgcolor: STAGE.green.strong, color: "#fff" }}>
        <Typography sx={{ fontSize: 44, fontWeight: 700, lineHeight: 1, fontVariantNumeric: "tabular-nums" }} data-count>
          {data ? data.total_contracted : "—"}</Typography>
        <Typography sx={{ mt: 0.5, fontSize: 17 }}>{t("cmp_contracted")}</Typography>
        <Typography variant="caption" sx={{ opacity: 0.85 }}>{t("cmp_contracted_hint")}</Typography>
      </ButtonBase>}

      <Paper variant="outlined" sx={{ p: 2 }} ref={table} id="companies-table">
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }} sx={{ mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600} sx={{ flex: 1 }}>{t("cmp_table")}</Typography>
          <TextField size="small" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("cmp_search")} id="cmp-search"
            InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }} sx={{ minWidth: 280 }} />
        </Stack>
        <TableContainer>
          <Table size="small">
            <TableHead><TableRow>
              {head("name", t("cmp_name"))}{head("code", t("cust_code"))}{showDistrict && <TableCell>{t("district")}</TableCell>}{head("debit", t("cmp_debit"), true)}
              {head("credit", t("cmp_credit"), true)}{head("volume_m3", t("cmp_volume"), true)}
            </TableRow></TableHead>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.customer_id} hover data-row={r.code}>
                  <TableCell><Link component="button" onClick={() => go(r, "debit")} underline="hover" sx={{ color: "inherit", textAlign: "left" }}>{r.name}</Link></TableCell>
                  <TableCell sx={{ fontFamily: "ui-monospace, monospace", fontWeight: 700 }}>
                    <Link component="button" onClick={() => go(r, "debit")} underline="hover" sx={{ color: "inherit" }}>{r.code}</Link></TableCell>
                  {showDistrict && <TableCell>{districts.find((d) => d.id === r.district_id)?.name ?? ""}</TableCell>}
                  <TableCell align="right">{num(r, "debit", fmtMoney(r.debit), r.debit > 0 ? "error.main" : undefined)}</TableCell>
                  <TableCell align="right">{num(r, "credit", fmtMoney(r.credit), r.credit > 0 ? "success.main" : undefined)}</TableCell>
                  <TableCell align="right">{num(r, "volume", fmtM3(r.volume_m3))}</TableCell>
                </TableRow>
              ))}
              {data && <TableRow sx={{ "& td": { fontWeight: 700, borderBottom: 0 } }}>
                <TableCell>{t("st_total")} ({rows.length})</TableCell><TableCell />{showDistrict && <TableCell />}
                <TableCell align="right">{fmtMoney(rows.reduce((s, r) => s + r.debit, 0))}</TableCell>
                <TableCell align="right">{fmtMoney(rows.reduce((s, r) => s + r.credit, 0))}</TableCell>
                <TableCell align="right">{fmtM3(rows.reduce((s, r) => s + r.volume_m3, 0))}</TableCell>
              </TableRow>}
            </TableBody>
          </Table>
        </TableContainer>
        <Box sx={{ mt: 1 }}><Typography variant="caption" color="text.secondary">{t("cmp_note")}</Typography></Box>
      </Paper>
    </Stack>
  );
}
