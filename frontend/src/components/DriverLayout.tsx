import type { ReactNode } from "react";
import { Alert, AppBar, Box, Button, Container, MenuItem, Select, Toolbar, Typography } from "@mui/material";
import { useOnline } from "@/hooks/useOnline";
import { LANGS, useI18n, type Lang } from "@/i18n/I18nContext";
import { useAppDispatch, useAppSelector } from "@/store";
import { logout } from "@/store/authSlice";

export function DriverLayout({ children }: { children: ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const online = useOnline();
  const user = useAppSelector((s) => s.auth.user);
  const plate = useAppSelector((s) => s.driver.shift?.vehicle.plate);
  const dispatch = useAppDispatch();
  return (
    <Box sx={{ minHeight: "100%", bgcolor: "background.default" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 1.5, flexWrap: "wrap" }}>
          <Typography variant="h6" color="primary" sx={{ fontWeight: 700, mr: "auto" }}>CSW</Typography>
          <Typography variant="body2" color="text.secondary">{user?.full_name}{plate ? ` · ${plate}` : ""}</Typography>
          <Select size="small" value={lang} onChange={(e) => setLang(e.target.value as Lang)} aria-label="Language">
            {LANGS.map((l) => <MenuItem key={l.id} value={l.id}>{l.label}</MenuItem>)}
          </Select>
          <Button onClick={() => dispatch(logout())}>{t("logout")}</Button>
        </Toolbar>
      </AppBar>
      {!online && <Alert severity="warning" square>{t("offline")}</Alert>}
      <Container maxWidth="md" sx={{ py: 2 }}>{children}</Container>
    </Box>
  );
}
