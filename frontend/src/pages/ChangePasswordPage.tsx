import { useState } from "react";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import CheckCircle from "@mui/icons-material/CheckCircle";
import RadioButtonUnchecked from "@mui/icons-material/RadioButtonUnchecked";
import { Navigate } from "react-router-dom";
import { authApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { AuthShell } from "@/components/AuthShell";
import { PasswordField } from "@/components/PasswordField";
import { useI18n } from "@/i18n/I18nContext";
import type { MessageKey } from "@/i18n/messages";
import { toast } from "@/lib/alerts";
import { homePath } from "@/lib/routes";
import { useAppDispatch, useAppSelector } from "@/store";
import { logout, setUser } from "@/store/authSlice";

/** Admin vaqtinchalik parol bergan xodim birinchi kirishda shu yerga yo'naltiriladi. */
export function ChangePasswordPage() {
  const { t, tErr } = useI18n();
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!user) return <Navigate to="/login" replace />;
  if (!user.must_change_password) return <Navigate to={homePath(user)} replace />;

  // Backend bilan bir xil qoidalar (auth_service.check_password_strength)
  const rules: [MessageKey, boolean][] = [
    ["pw_rule_length", next.length >= 8],
    ["pw_rule_letter", /\p{L}/u.test(next)],
    ["pw_rule_digit", /\d/.test(next)],
    ["pw_rule_differs", next !== "" && next !== current],
    ["pw_rule_match", next !== "" && next === repeat],
  ];
  const ok = current !== "" && rules.every(([, v]) => v);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ok) return;
    setBusy(true);
    setError(null);
    try {
      dispatch(setUser(await authApi.changePassword(current, next)));
      toast(t("password_changed"));
    } catch (err) {
      setError(tErr(errorCode(err), errorMessage(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell steps={[t("auth_step_1"), t("auth_step_2"), t("auth_step_3")]}>
      <Box component="form" onSubmit={submit} noValidate>
        <Typography component="h1" sx={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.01em", lineHeight: 1.2 }}>{t("change_pw_title")}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>{t("change_pw_hello", { name: user.full_name })}</Typography>
        <Stack spacing={2}>
          <PasswordField id="current-password" label={t("current_password")} value={current} onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password" helperText={t("current_password_help")} fullWidth />
          <PasswordField id="new-password" label={t("new_password")} value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" fullWidth />
          <PasswordField id="repeat-password" label={t("repeat_password")} value={repeat} onChange={(e) => setRepeat(e.target.value)}
            error={repeat !== "" && repeat !== next} autoComplete="new-password" fullWidth />
          <Box component="ul" aria-live="polite" sx={{ m: 0, p: 0, listStyle: "none", display: "grid", gap: 0.75 }}>
            {rules.map(([key, met]) => (
              <Box component="li" key={key} data-met={met} sx={{ display: "flex", alignItems: "center", gap: 1, fontSize: 14,
                color: met ? "success.main" : "text.secondary" }}>
                {met ? <CheckCircle sx={{ fontSize: 18 }} /> : <RadioButtonUnchecked sx={{ fontSize: 18 }} />}{t(key)}
              </Box>
            ))}
          </Box>
          {error && <Alert severity="error" variant="outlined">{error}</Alert>}
          <Button type="submit" variant="contained" size="large" fullWidth disableElevation disabled={busy || !ok}>{t("save_password")}</Button>
          <Button variant="text" color="inherit" onClick={() => dispatch(logout())}>{t("logout")}</Button>
        </Stack>
      </Box>
    </AuthShell>
  );
}
