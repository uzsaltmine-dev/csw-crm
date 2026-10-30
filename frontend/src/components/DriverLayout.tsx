import type { ReactNode } from "react";
import { Alert, AppBar, Box, Button, Container, MenuItem, Select, Toolbar, Typography } from "@mui/material";
import { SituationBell, SituationProvider } from "@/components/Situation";
import { useOnline } from "@/hooks/useOnline";
import { LANGS, useI18n, type Lang } from "@/i18n/I18nContext";
import { useAppDispatch, useAppSelector } from "@/store";
import { logout } from "@/store/authSlice";

export function DriverLayout({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  const { t, lang, setLang } = useI18n();
  const online = useOnline();
  const user = useAppSelector((s) => s.auth.user);
  const plate = useAppSelector((s) => s.driver.today?.vehicle?.plate);
  const dispatch = useAppDispatch();
  const watcher = user?.role === "admin"; // Vaziyat paneli — faqat admin
  const page = (
    <Box sx={{ minHeight: "100%", bgcolor: "background.default" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 1.5, flexWrap: "wrap" }}>
          <Typography variant="h6" color="primary" sx={{ fontWeight: 700, mr: "auto" }}>CSW</Typography>
          {watcher && <SituationBell />}
          <Typography variant="body2" color="text.secondary">{user?.full_name}{plate ? ` · ${plate}` : ""}</Typography>
          <Select size="small" value={lang} onChange={(e) => setLang(e.target.value as Lang)} aria-label="Language">
            {LANGS.map((l) => <MenuItem key={l.id} value={l.id}>{l.label}</MenuItem>)}
          </Select>
          <Button onClick={() => dispatch(logout())}>{t("logout")}</Button>
        </Toolbar>
      </AppBar>
      {!online && <Alert severity="warning" square>{t("offline")}</Alert>}
      <Container maxWidth={wide ? "lg" : "md"} sx={{ py: 2 }}>{children}</Container>
    </Box>
  );
  // Admin va manager: Vaziyat paneli hodisalari jonli keladi (qo'ng'iroqcha + popup)
  // Yozishma: o'qilmaganlar, jonli toast va yon panel — har bir rol uchun
  return watcher ? <SituationProvider>{page}</SituationProvider> : page;
}
