import type { ReactNode } from "react";
import { Box, MenuItem, Select, Stack, Typography } from "@mui/material";
import { LANGS, useI18n, type Lang } from "@/i18n/I18nContext";

/**
 * Login va parol almashtirish sahifalari uchun umumiy ramka.
 * Chapda — CSW dunyosi: mashina yo'nalishi, chiqindi olinadigan nuqtalar va GPS radiusi halqasi.
 * O'ngda — forma. Telefonda chap panel yuqoridagi ixcham tasmaga aylanadi.
 */
const FOREST = "#123d2e";
const LEAF = "#8fd3a7";
const SIGNAL = "#e8b04a";

function RouteArt() {
  // Yo'nalish: depo → 4 ta korxona; oxirgi nuqtada GPS radiusi halqasi (dalolatnoma shu doirada yopiladi)
  return (
    <Box component="svg" viewBox="0 0 400 300" aria-hidden sx={{ width: "100%", maxWidth: 440, height: "auto", display: "block" }}>
      <defs>
        <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M24 0H0V24" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="400" height="300" fill="url(#grid)" />
      <path d="M40 250 C 90 250, 90 190, 140 185 S 200 120, 250 130 S 300 70, 340 64" fill="none" stroke={LEAF} strokeWidth="3"
        strokeLinecap="round" strokeDasharray="1 9" />
      <path d="M40 250 C 90 250, 90 190, 140 185 S 200 120, 250 130" fill="none" stroke={LEAF} strokeWidth="3" strokeLinecap="round" />
      <rect x="28" y="238" width="24" height="24" rx="5" fill={LEAF} />
      {[[140, 185], [250, 130]].map(([x, y]) => (
        <g key={x}><circle cx={x} cy={y} r="9" fill={FOREST} stroke={LEAF} strokeWidth="3" /><path d={`M${x - 4} ${y}l3 3l5 -6`} stroke={LEAF} strokeWidth="2.2" fill="none" strokeLinecap="round" /></g>
      ))}
      <circle cx="340" cy="64" r="44" fill="rgba(232,176,74,0.10)" stroke={SIGNAL} strokeWidth="1.5" strokeDasharray="4 5" />
      <circle cx="340" cy="64" r="9" fill={SIGNAL} />
      <circle cx="300" cy="230" r="7" fill="none" stroke="rgba(255,255,255,0.35)" strokeWidth="2" />
    </Box>
  );
}

export function AuthShell({ children, steps }: { children: ReactNode; steps?: string[] }) {
  const { t, lang, setLang } = useI18n();
  return (
    <Box sx={{ minHeight: "100dvh", display: "grid", gridTemplateColumns: { xs: "1fr", md: "minmax(360px, 44%) 1fr" }, bgcolor: "background.default" }}>
      <Box component="aside" sx={{ bgcolor: FOREST, color: "#eaf3ee", px: { xs: 2.5, md: 6 }, py: { xs: 2.5, md: 6 },
        display: "flex", flexDirection: "column", gap: { xs: 1.5, md: 4 } }}>
        <Stack direction="row" alignItems="baseline" spacing={1.5}>
          <Typography component="span" sx={{ fontSize: { xs: 26, md: 34 }, fontWeight: 700, letterSpacing: "-0.02em", color: "#fff" }}>CSW</Typography>
          <Typography component="span" sx={{ fontSize: 15, color: LEAF }}>{t("auth_tagline")}</Typography>
        </Stack>
        <Box sx={{ display: { xs: "none", md: "block" }, my: "auto" }}><RouteArt /></Box>
        {steps && <Box component="ol" sx={{ display: { xs: "none", md: "grid" }, gap: 2, m: 0, p: 0, listStyle: "none", counterReset: "s" }}>
          {steps.map((s) => (
            <Box component="li" key={s} sx={{ display: "grid", gridTemplateColumns: "28px 1fr", gap: 1.5, alignItems: "start", fontSize: 15, lineHeight: 1.45,
              counterIncrement: "s", "&::before": { content: "counter(s)", width: 28, height: 28, borderRadius: "50%", border: `1.5px solid ${LEAF}`,
                color: LEAF, display: "grid", placeItems: "center", fontSize: 13, fontWeight: 600 } }}>
              <span>{s}</span>
            </Box>
          ))}
        </Box>}
      </Box>

      <Box component="main" sx={{ display: "flex", flexDirection: "column", px: { xs: 2, sm: 4 }, py: { xs: 2, md: 4 } }}>
        <Box sx={{ display: "flex", justifyContent: "flex-end" }}>
          <Select size="small" value={lang} onChange={(e) => setLang(e.target.value as Lang)} inputProps={{ "aria-label": t("language") }}
            sx={{ minWidth: 140 }}>
            {LANGS.map((l) => <MenuItem key={l.id} value={l.id}>{l.label}</MenuItem>)}
          </Select>
        </Box>
        <Box sx={{ flex: 1, display: "grid", placeItems: "center", py: { xs: 3, md: 0 } }}>
          <Box sx={{ width: "100%", maxWidth: 400 }}>{children}</Box>
        </Box>
      </Box>
    </Box>
  );
}
