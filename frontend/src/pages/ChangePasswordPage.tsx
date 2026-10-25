import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, Typography } from "@mui/material";
import { Navigate } from "react-router-dom";
import { authApi } from "@/api/endpoints";
import { errorCode, errorMessage } from "@/api/client";
import { useI18n } from "@/i18n/I18nContext";
import { toast } from "@/lib/alerts";
import { homePath } from "@/lib/routes";
import { useAppDispatch, useAppSelector } from "@/store";
import { setUser } from "@/store/authSlice";
import { PasswordField } from "@/components/PasswordField";

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
  const mismatch = repeat !== "" && next !== repeat;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mismatch) return;
    setBusy(true);
    setError(null);
    try {
      dispatch(setUser(await authApi.changePassword(current, next)));
      toast(t("saved"));
    } catch (err) {
      setError(tErr(errorCode(err), errorMessage(err)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", bgcolor: "background.default", px: 2 }}>
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 4, width: "100%", maxWidth: 420 }}>
        <Stack spacing={2}>
          <Typography variant="h6">{t("change_pw_title")}</Typography>
          <Typography variant="body2" color="text.secondary">{t("change_pw_text")}</Typography>
          {error && <Alert severity="error">{error}</Alert>}
          <PasswordField id="current-password" label={t("current_password")} value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" required />
          <PasswordField id="new-password" label={t("new_password")} value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required />
          <PasswordField id="repeat-password" label={t("repeat_password")} value={repeat} onChange={(e) => setRepeat(e.target.value)}
            error={mismatch} helperText={mismatch ? t("passwords_differ") : " "} autoComplete="new-password" required />
          <Button type="submit" variant="contained" size="large" disabled={busy || mismatch || !current || !next}>{t("save")}</Button>
        </Stack>
      </Paper>
    </Box>
  );
}
