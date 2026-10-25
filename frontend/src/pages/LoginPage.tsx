import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { Navigate } from "react-router-dom";
import { useOnline } from "@/hooks/useOnline";
import { homePath } from "@/lib/routes";
import { useI18n } from "@/i18n/I18nContext";
import { useAppDispatch, useAppSelector } from "@/store";
import { login } from "@/store/authSlice";
import { PasswordField } from "@/components/PasswordField";

export function LoginPage() {
  const { t, tErr } = useI18n();
  const dispatch = useAppDispatch();
  const online = useOnline();
  const { user, error } = useAppSelector((s) => s.auth);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homePath(user)} replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    await dispatch(login({ username, password }));
    setBusy(false);
  };

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", bgcolor: "background.default", px: 2 }}>
      <Paper component="form" onSubmit={submit} sx={{ p: 4, width: "100%", maxWidth: 380 }} variant="outlined">
        <Stack spacing={2}>
          <Typography variant="h5" fontWeight={700} color="primary">CSW</Typography>
          <Typography variant="h6">{t("login_title")}</Typography>
          {!online && <Alert severity="warning">{t("offline")}</Alert>}
          {error && <Alert severity="error">{tErr(error)}</Alert>}
          {import.meta.env.VITE_DEMO === "1" && <Alert severity="info">{t("demo_hint")}</Alert>}
          <TextField id="username" label={t("username")} value={username} onChange={(e) => setUsername(e.target.value)}
            autoComplete="username" autoCapitalize="none" required />
          <PasswordField id="password" label={t("password")} value={password} onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password" required />
          <Button type="submit" variant="contained" size="large" disabled={busy || !online}>{t("sign_in")}</Button>
        </Stack>
      </Paper>
    </Box>
  );
}
