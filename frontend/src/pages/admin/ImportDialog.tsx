import { useEffect, useState } from "react";
import { Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, LinearProgress, Stack, Table, TableBody, TableCell,
  TableHead, TableRow, Typography } from "@mui/material";
import { customersApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import { formatDateTime } from "@/lib/format";
import { toast } from "@/lib/alerts";
import type { ImportBatch, ImportResult } from "@/types";

/** Ikki qadam: 1) tahlil (dry_run, bazaga yozilmaydi) 2) "Import qilish". */
export function ImportDialog({ onClose, onImported }: { onClose: () => void; onImported: () => void }) {
  const { t, tErr } = useI18n();
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<ImportResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<ImportBatch[]>([]);

  const loadHistory = () => customersApi.batches().then(setHistory).catch(() => undefined);
  useEffect(() => { loadHistory(); }, []);

  const send = async (dryRun: boolean) => {
    if (!file) return;
    setBusy(true);
    try {
      const res = await customersApi.importFile(file, dryRun);
      setReport(res);
      if (!dryRun) { toast(t("import_done", { n: res.customers_new })); onImported(); loadHistory(); }
    } catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); }
    finally { setBusy(false); }
  };

  const stat = (label: string, value: number, color?: string) => (
    <Box sx={{ p: 1.5, border: 1, borderColor: "divider", borderRadius: 1 }}>
      <Typography variant="h6" sx={{ color, fontVariantNumeric: "tabular-nums" }}>{value}</Typography>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
    </Box>
  );

  return (
    <Dialog open onClose={busy ? undefined : onClose} fullWidth maxWidth="md">
      <DialogTitle>{t("import_excel")}</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Typography variant="body2" color="text.secondary">{t("import_hint")}</Typography>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <Button component="label" variant="outlined" disabled={busy}>{t("choose_file")}
              <input id="imp-file" hidden type="file" accept=".xlsx,.xls,.csv,.docx,.pdf"
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); setReport(null); e.target.value = ""; }} />
            </Button>
            <Typography variant="body2" sx={{ wordBreak: "break-all" }}>{file?.name ?? "—"}</Typography>
          </Stack>
          {busy && <LinearProgress />}

          {report && <>
            <Alert severity={report.dry_run ? "info" : "success"}>
              {report.dry_run ? `${t("imp_format", { f: report.file_kind.toUpperCase() })}, ${t("imp_sheet")}: «${report.sheet}»` : t("import_done", { n: report.customers_new })}
            </Alert>
            <Box sx={{ display: "grid", gap: 1, gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(4, 1fr)" } }}>
              {stat(t("imp_rows"), report.rows_total)}
              {stat(t("imp_new"), report.customers_new, "success.main")}
              {stat(t("imp_existing"), report.customers_existing)}
              {stat(t("imp_contacts"), report.contacts_added)}
              {stat(t("imp_skipped"), report.rows_skipped, report.rows_skipped ? "error.main" : undefined)}
              {stat(t("imp_septic"), report.septic_rows)}
              {stat(t("imp_errors"), report.errors.length, report.errors.length ? "warning.main" : undefined)}
            </Box>
            <Table size="small">
              <TableHead><TableRow><TableCell>{t("district")}</TableCell><TableCell align="right">{t("tab_customers")}</TableCell></TableRow></TableHead>
              <TableBody>{Object.entries(report.by_district).sort((a, b) => b[1] - a[1]).map(([d, n]) =>
                <TableRow key={d}><TableCell>{d}</TableCell><TableCell align="right">{n}</TableCell></TableRow>)}</TableBody>
            </Table>
            {report.errors.length > 0 && <Box>
              <Typography variant="subtitle2" gutterBottom>{t("imp_errors")}</Typography>
              <Box sx={{ maxHeight: 220, overflow: "auto", border: 1, borderColor: "divider", borderRadius: 1 }}>
                <Table size="small" stickyHeader>
                  <TableHead><TableRow><TableCell>{t("imp_row")}</TableCell><TableCell>{t("status")}</TableCell></TableRow></TableHead>
                  <TableBody>{report.errors.map((e, i) => <TableRow key={i}><TableCell>{e.row}</TableCell><TableCell>{e.message}</TableCell></TableRow>)}</TableBody>
                </Table>
              </Box>
            </Box>}
          </>}

          {history.length > 0 && <Box>
            <Typography variant="subtitle2" gutterBottom>{t("import_history")}</Typography>
            <Table size="small">
              <TableHead><TableRow><TableCell>{t("date")}</TableCell><TableCell>{t("file")}</TableCell><TableCell align="right">{t("imp_rows")}</TableCell>
                <TableCell align="right">{t("imp_new")}</TableCell><TableCell align="right">{t("imp_existing")}</TableCell><TableCell align="right">{t("imp_skipped")}</TableCell></TableRow></TableHead>
              <TableBody>{history.map((b) => <TableRow key={b.id}>
                <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDateTime(new Date(b.created_at + "Z"))}</TableCell>
                <TableCell sx={{ wordBreak: "break-all" }}>{b.file_name}</TableCell><TableCell align="right">{b.rows_total}</TableCell>
                <TableCell align="right">{b.customers_created}</TableCell><TableCell align="right">{b.customers_merged}</TableCell><TableCell align="right">{b.rows_skipped}</TableCell>
              </TableRow>)}</TableBody>
            </Table>
          </Box>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>{t("close")}</Button>
        <Button variant="outlined" onClick={() => send(true)} disabled={busy || !file}>{t("analyze")}</Button>
        <Button variant="contained" onClick={() => send(false)} disabled={busy || !file || !report?.dry_run}>{t("do_import")}</Button>
      </DialogActions>
    </Dialog>
  );
}
