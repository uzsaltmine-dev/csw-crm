import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Chip, List, ListItemButton, ListItemText, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { adminApi, appealsApi, customersApi, requestsApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import { ChatButton } from "@/components/Chat";
import type { MessageKey } from "@/i18n/messages";
import { confirmDialog, toast } from "@/lib/alerts";
import { formatDateTime } from "@/lib/format";
import { getSocket } from "@/lib/socket";
import type { Appeal, CustomerListItem, District, RequestItem } from "@/types";
import { EMPTY_ORDER, OrderFields, orderBody, type Order } from "./OrderFields";

/** Status chipi rangi */
export const STATUS_COLOR: Record<string, "default" | "info" | "success" | "warning" | "error"> = {
  new: "info", assigned: "info", enroute: "info", onsite: "info", done: "success", suspect: "warning", failed: "error", cancelled: "default",
};

export function RequestChips({ r }: { r: Pick<RequestItem, "is_repeat" | "overdue" | "waste_type"> }) {
  const { t } = useI18n();
  return <>
    {r.is_repeat && <Chip size="small" color="secondary" variant="outlined" label={t("repeat")} />}
    {r.overdue && <Chip size="small" color="error" label={t("overdue")} />}
    {r.waste_type === "septic" && <Chip size="small" color="info" label={t("w_septic")} />}
  </>;
}

/**
 * Call-center operatori: qo'ng'iroq → korxonani topish → ariza (takror bo'lsa tasdiq) yoki birinchi murojaat (yuridik bo'limga).
 * O'ng tomonda operator ochgan arizalar va murojaatlar holati jonli.
 */
export function OperatorHome() {
  const { t, tErr } = useI18n();
  const [q, setQ] = useState("");
  const [found, setFound] = useState<CustomerListItem[]>([]);
  const [picked, setPicked] = useState<CustomerListItem | null>(null);
  const [appealMode, setAppealMode] = useState(false);
  const [order, setOrder] = useState<Order>(EMPTY_ORDER);
  const [org, setOrg] = useState({ org_name: "", stir: "", address: "", activity_type: "", district_id: "" as number | "" });
  const [districts, setDistricts] = useState<District[]>([]);
  const [mine, setMine] = useState<RequestItem[]>([]);
  const [appeals, setAppeals] = useState<Appeal[]>([]);
  const [busy, setBusy] = useState(false);

  const loadMine = useCallback(async () => {
    const [r, a] = await Promise.all([requestsApi.list({ mine: true, limit: 30 }), appealsApi.list({ mine: true })]);
    setMine(r.items); setAppeals(a);
  }, []);
  useEffect(() => {
    adminApi.districts().then(setDistricts).catch(() => undefined);
    loadMine().catch(() => undefined);
    const s = getSocket();
    const on = () => { loadMine().catch(() => undefined); };
    s.on("request:updated", on); s.on("appeal:updated", on);
    return () => { s.off("request:updated", on); s.off("appeal:updated", on); };
  }, [loadMine]);

  // Qidiruv: yozish to'xtagach 300 ms
  useEffect(() => {
    if (q.trim().length < 2) { setFound([]); return; }
    const h = setTimeout(() => customersApi.search({ q: q.trim(), limit: 8 }).then((r) => setFound(r.items)).catch(() => setFound([])), 300);
    return () => clearTimeout(h);
  }, [q]);

  const reset = () => { setPicked(null); setAppealMode(false); setOrder(EMPTY_ORDER); setQ(""); setFound([]);
    setOrg({ org_name: "", stir: "", address: "", activity_type: "", district_id: "" }); };
  const fail = (e: unknown) => toast(tErr(errorCode(e), errorMessage(e)), "error");

  const submitRequest = async () => {
    if (!picked) return;
    setBusy(true);
    try {
      let confirm_repeat = false;
      const open = await requestsApi.openFor(picked.id);
      if (open.length) {
        const list = open.map((r) => `${r.number} (${t(`s_${r.status}` as MessageKey)})`).join(", ");
        if (!(await confirmDialog(t("repeat_title"), t("repeat_confirm"), t("cancel"), t("repeat_text", { list }), false))) return;
        confirm_repeat = true;
      }
      const r = await requestsApi.create({ customer_id: picked.id, ...orderBody(order), confirm_repeat });
      toast(t("request_opened", { n: r.number ?? "" }));
      reset();
      loadMine();
    } catch (e) { fail(e); } finally { setBusy(false); }
  };

  const submitAppeal = async () => {
    if (org.district_id === "") return;
    setBusy(true);
    try {
      const a = await appealsApi.create({ ...orderBody(order), district_id: org.district_id, org_name: org.org_name.trim(),
        stir: org.stir.trim() || null, address: org.address.trim() || null, activity_type: org.activity_type.trim() || null });
      toast(t("appeal_sent", { n: a.number ?? "" }));
      reset();
      loadMine();
    } catch (e) { fail(e); } finally { setBusy(false); }
  };

  const dName = (id: number) => districts.find((d) => d.id === id)?.name ?? "";

  return (
    <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: { xs: "1fr", md: "minmax(0, 3fr) minmax(0, 2fr)" }, alignItems: "start" }}>
      <Stack spacing={2}>
        <Typography variant="h5">{t("operator_title")}</Typography>
        <Paper variant="outlined" sx={{ p: 2 }}>
          {!picked && !appealMode && <>
            <TextField id="op-search" fullWidth autoFocus label={t("find_customer")} helperText={t("find_customer_hint")} value={q}
              onChange={(e) => setQ(e.target.value)} />
            {found.length > 0 && <List dense sx={{ mt: 1, border: 1, borderColor: "divider", borderRadius: 1 }}>
              {found.map((c) => (
                <ListItemButton key={c.id} onClick={() => setPicked(c)} data-customer={c.fixed_no}>
                  <ListItemText primary={<>{c.fixed_no} · {c.name}</>}
                    secondary={[dName(c.district_id), c.address, c.phone].filter(Boolean).join(" · ")} />
                  {c.missing_fields.length > 0 && <Chip size="small" color="error" variant="outlined"
                    label={t(c.missing_fields.includes("stir") ? "missing_stir" : "missing_contract")} />}
                </ListItemButton>
              ))}
            </List>}
            {q.trim().length >= 2 && <Button sx={{ mt: 1.5 }} variant="outlined" id="op-appeal"
              onClick={() => { setAppealMode(true); setOrg((o) => ({ ...o, org_name: q.trim() })); }}>{t("not_found_appeal")}</Button>}
          </>}

          {picked && <Stack spacing={2}>
            <Typography variant="h6">{t("new_request_for", { name: picked.name })}</Typography>
            <Typography variant="body2" color="text.secondary">{[picked.fixed_no, dName(picked.district_id), picked.address].filter(Boolean).join(" · ")}</Typography>
            {picked.missing_fields.length > 0 && <Alert severity="warning">{t("cannot_assign_hint")}</Alert>}
            <OrderFields value={order} onChange={setOrder} />
            <Stack direction="row" spacing={1}>
              <Button id="op-submit" variant="contained" disabled={busy} onClick={submitRequest}>{t("open_request")}</Button>
              <Button onClick={reset}>{t("cancel")}</Button>
            </Stack>
          </Stack>}

          {appealMode && <Stack spacing={2}>
            <Typography variant="h6">{t("appeal_title")}</Typography>
            <Typography variant="body2" color="text.secondary">{t("appeal_hint")}</Typography>
            <Box sx={{ display: "grid", gap: 1.5, gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" } }}>
              <TextField id="ap-org" size="small" label={t("org_name")} value={org.org_name} onChange={(e) => setOrg({ ...org, org_name: e.target.value })}
                sx={{ gridColumn: { sm: "1 / -1" } }} />
              <TextField id="ap-district" size="small" select label={t("district")} value={org.district_id}
                onChange={(e) => setOrg({ ...org, district_id: Number(e.target.value) })}>
                {districts.filter((d) => d.is_active).map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
              </TextField>
              <TextField id="ap-stir" size="small" label={t("stir")} value={org.stir} onChange={(e) => setOrg({ ...org, stir: e.target.value })}
                slotProps={{ htmlInput: { inputMode: "numeric", maxLength: 9 } }} />
              <TextField id="ap-address" size="small" label={t("address")} value={org.address} onChange={(e) => setOrg({ ...org, address: e.target.value })} />
              <TextField id="ap-activity" size="small" label={t("activity_type")} value={org.activity_type} onChange={(e) => setOrg({ ...org, activity_type: e.target.value })} />
            </Box>
            <OrderFields value={order} onChange={setOrder} idPrefix="ap" />
            <Stack direction="row" spacing={1}>
              <Button id="ap-submit" variant="contained" disabled={busy || org.org_name.trim().length < 2 || org.district_id === "" || (!!org.stir && !/^\d{9}$/.test(org.stir))}
                onClick={submitAppeal}>{t("send_to_legal")}</Button>
              <Button onClick={reset}>{t("cancel")}</Button>
            </Stack>
          </Stack>}
        </Paper>
      </Stack>

      <Stack spacing={2}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>{t("my_requests_today")}</Typography>
          {!mine.length && <Typography color="text.secondary">—</Typography>}
          <Stack spacing={1} id="op-my-requests">
            {mine.map((r) => (
              <Box key={r.id} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.25 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography fontWeight={600} sx={{ fontVariantNumeric: "tabular-nums" }}>{r.number}</Typography>
                  <Chip size="small" color={STATUS_COLOR[r.status]} label={t(`s_${r.status}` as MessageKey)} />
                  <RequestChips r={r} />
                </Stack>
                <Typography variant="body2">{r.customer.name}</Typography>
                <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                  <Typography variant="caption" color="text.secondary">
                    {formatDateTime(new Date(r.created_at + "Z"))}{r.due_at && `, ${t("due_at")}: ${formatDateTime(new Date(r.due_at + "Z"))}`}
                  </Typography>
                  <ChatButton type="request" id={r.id} variant="text" />
                </Stack>
              </Box>
            ))}
          </Stack>
        </Paper>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>{t("my_appeals")}</Typography>
          {!appeals.length && <Typography color="text.secondary">—</Typography>}
          <Stack spacing={1} id="op-my-appeals">
            {appeals.map((a) => (
              <Box key={a.id} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.25 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={600}>{a.number}</Typography>
                  <Chip size="small" color={a.status === "accepted" ? "success" : a.status === "rejected" ? "default" : "warning"}
                    label={t(`ap_${a.status}` as MessageKey)} />
                </Stack>
                <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                  <Typography variant="body2">{a.org_name}</Typography>
                  <ChatButton type={a.request_id ? "request" : "appeal"} id={a.request_id ?? a.id} variant="text" />
                </Stack>
                {a.reject_reason && <Typography variant="caption" color="error">{a.reject_reason}</Typography>}
              </Box>
            ))}
          </Stack>
        </Paper>
      </Stack>
    </Box>
  );
}
