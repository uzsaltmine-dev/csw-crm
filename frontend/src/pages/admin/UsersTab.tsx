import { useCallback, useEffect, useMemo, useState } from "react";
import { Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Paper, Stack, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, TextField } from "@mui/material";
import { adminApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import type { MessageKey } from "@/i18n/messages";
import { confirmDialog, toast } from "@/lib/alerts";
import { useAppSelector } from "@/store";
import type { AdminUser, Role } from "@/types";
import { districtLabel, type RefData } from "./AdminHome";

const ROLES: Role[] = ["admin", "manager", "operator", "gps", "legal", "driver"];
const NEEDS_DISTRICT: Role[] = ["driver", "gps"];
type Form = { id?: number; username: string; full_name: string; phone: string; role: Role; district_id: number | ""; password: string };
const EMPTY: Form = { username: "", full_name: "", phone: "", role: "driver", district_id: "", password: "" };

export function UsersTab({ districts, canWrite }: RefData) {
  const { t, tErr } = useI18n();
  const me = useAppSelector((s) => s.auth.user);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [role, setRole] = useState<Role | "">("");
  const [district, setDistrict] = useState<number | "">("");
  const [q, setQ] = useState("");
  const [form, setForm] = useState<Form | null>(null);
  const [reset, setReset] = useState<{ user: AdminUser; password: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const roleLabel = (r: Role) => t(`r_${r}` as MessageKey);

  const load = useCallback(async () => setUsers(await adminApi.users()), []);
  useEffect(() => { load().catch(() => undefined); }, [load]);

  const shown = useMemo(() => users.filter((u) =>
    (!role || u.role === role) && (!district || u.district_id === district) &&
    (!q || `${u.username} ${u.full_name} ${u.phone ?? ""}`.toLowerCase().includes(q.toLowerCase()))), [users, role, district, q]);

  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    try { await fn(); if (ok) toast(ok); await load(); return true; }
    catch (e) { toast(tErr(errorCode(e), errorMessage(e)), "error"); return false; }
    finally { setBusy(false); }
  };

  const save = async () => {
    if (!form) return;
    const district_id = form.district_id === "" ? null : form.district_id;
    const done = await run(() => form.id
      ? adminApi.updateUser(form.id, { full_name: form.full_name, phone: form.phone || null, role: form.role, district_id })
      : adminApi.createUser({ username: form.username.trim().toLowerCase(), full_name: form.full_name, phone: form.phone || null, role: form.role, district_id, password: form.password }),
    t("saved"));
    if (done) setForm(null);
  };

  const toggle = async (u: AdminUser) => {
    if (u.is_active && !(await confirmDialog(t("confirm_deactivate"), t("deactivate"), t("cancel"), u.full_name))) return;
    await run(() => adminApi.updateUser(u.id, { is_active: !u.is_active }), t("saved"));
  };

  const needsDistrict = form ? NEEDS_DISTRICT.includes(form.role) : false;
  const formValid = form && form.full_name.trim().length >= 2 && (!needsDistrict || form.district_id !== "") &&
    (form.id || (/^[a-z0-9_.]{3,50}$/.test(form.username.trim().toLowerCase()) && form.password.length >= 8));

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mb: 2 }}>
        <TextField id="user-search" size="small" label={t("search")} value={q} onChange={(e) => setQ(e.target.value)} sx={{ flex: 1 }} />
        <TextField id="user-role" size="small" select label={t("role")} value={role} onChange={(e) => setRole(e.target.value as Role | "")} sx={{ minWidth: 190 }}>
          <MenuItem value="">{t("all")}</MenuItem>
          {ROLES.map((r) => <MenuItem key={r} value={r}>{roleLabel(r)}</MenuItem>)}
        </TextField>
        <TextField id="user-district" size="small" select label={t("district")} value={district} onChange={(e) => setDistrict(e.target.value === "" ? "" : Number(e.target.value))} sx={{ minWidth: 190 }}>
          <MenuItem value="">{t("all")}</MenuItem>
          {districts.map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
        </TextField>
        {canWrite && <Button variant="contained" onClick={() => setForm({ ...EMPTY })}>{t("new_user")}</Button>}
      </Stack>
      <TableContainer>
        <Table size="small">
          <TableHead><TableRow>
            <TableCell>{t("username")}</TableCell><TableCell>{t("full_name")}</TableCell><TableCell>{t("role")}</TableCell>
            <TableCell>{t("district")}</TableCell><TableCell>{t("status")}</TableCell>{canWrite && <TableCell />}
          </TableRow></TableHead>
          <TableBody>
            {shown.map((u) => (
              <TableRow key={u.id} sx={{ opacity: u.is_active ? 1 : 0.55 }}>
                <TableCell sx={{ fontFamily: "monospace" }}>{u.username}</TableCell>
                <TableCell>{u.full_name}{u.phone && <><br /><small>{u.phone}</small></>}</TableCell>
                <TableCell>{roleLabel(u.role)}</TableCell>
                <TableCell>{districtLabel(districts, u.district_id)}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                    <Chip size="small" color={u.is_active ? "success" : "default"} label={t(u.is_active ? "active" : "inactive")} />
                    {u.locked_until && new Date(u.locked_until + "Z") > new Date() && <Chip size="small" color="error" label={t("locked")} />}
                    {u.must_change_password && <Chip size="small" color="warning" variant="outlined" label={t("temp_password_pending")} />}
                  </Stack>
                </TableCell>
                {canWrite && <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  <Button size="small" onClick={() => setForm({ id: u.id, username: u.username, full_name: u.full_name, phone: u.phone ?? "", role: u.role, district_id: u.district_id ?? "", password: "" })}>{t("edit")}</Button>
                  <Button size="small" onClick={() => setReset({ user: u, password: "" })}>{t("reset_password")}</Button>
                  {u.id !== me?.id && <Button size="small" color={u.is_active ? "error" : "success"} disabled={busy} onClick={() => toggle(u)}>{t(u.is_active ? "deactivate" : "activate")}</Button>}
                </TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={!!form} onClose={() => setForm(null)} fullWidth maxWidth="sm">
        <DialogTitle>{form?.id ? t("edit") : t("new_user")}</DialogTitle>
        {form && <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField id="f-username" label={t("username")} value={form.username} disabled={!!form.id} helperText={t("username_hint")}
              onChange={(e) => setForm({ ...form, username: e.target.value })} autoCapitalize="none" />
            <TextField id="f-fullname" label={t("full_name")} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
            <TextField id="f-phone" label={t("phone")} value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} placeholder="+998 90 123-45-67" />
            <TextField id="f-role" select label={t("role")} value={form.role} disabled={form.id === me?.id} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
              {ROLES.map((r) => <MenuItem key={r} value={r}>{roleLabel(r)}</MenuItem>)}
            </TextField>
            <TextField id="f-district" select label={t("district")} value={form.district_id} required={needsDistrict}
              onChange={(e) => setForm({ ...form, district_id: e.target.value === "" ? "" : Number(e.target.value) })}>
              {!needsDistrict && <MenuItem value="">—</MenuItem>}
              {districts.filter((d) => d.is_active || d.id === form.district_id).map((d) => <MenuItem key={d.id} value={d.id}>{d.name}</MenuItem>)}
            </TextField>
            {!form.id && <TextField id="f-password" label={t("temp_password")} value={form.password} helperText={t("temp_password_hint")}
              onChange={(e) => setForm({ ...form, password: e.target.value })} />}
          </Stack>
        </DialogContent>}
        <DialogActions>
          <Button onClick={() => setForm(null)}>{t("cancel")}</Button>
          <Button variant="contained" onClick={save} disabled={busy || !formValid}>{t("save")}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!reset} onClose={() => setReset(null)} fullWidth maxWidth="xs">
        <DialogTitle>{t("reset_password")}: {reset?.user.username}</DialogTitle>
        <DialogContent>
          <TextField id="reset-password" sx={{ mt: 1 }} fullWidth label={t("temp_password")} helperText={t("temp_password_hint")}
            value={reset?.password ?? ""} onChange={(e) => reset && setReset({ ...reset, password: e.target.value })} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReset(null)}>{t("cancel")}</Button>
          <Button variant="contained" disabled={busy || (reset?.password.length ?? 0) < 8}
            onClick={async () => { if (reset && await run(() => adminApi.resetPassword(reset.user.id, reset.password), t("saved"))) setReset(null); }}>{t("save")}</Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
}
