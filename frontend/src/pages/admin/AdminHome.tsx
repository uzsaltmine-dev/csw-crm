import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";
import { useSituation } from "@/components/Situation";
import { adminApi } from "@/api/endpoints";
import { useI18n } from "@/i18n/I18nContext";
import { useAppSelector } from "@/store";
import type { District, Region } from "@/types";
import { CustomersTab } from "./CustomersTab";
import { DistrictsTab } from "./DistrictsTab";
import { SettingsTab } from "./SettingsTab";
import { SituationTab } from "./SituationTab";
import { UsersTab } from "./UsersTab";
import { VehiclesTab } from "./VehiclesTab";

const TABS = ["situation", "customers", "users", "districts", "vehicles", "settings"] as const;
type TabId = (typeof TABS)[number];

export interface RefData { regions: Region[]; districts: District[]; reload: () => Promise<void>; canWrite: boolean }

/** Admin: yozadi; Manager: ko'radi va koordinatani tasdiqlaydi; Yurist: faqat "Korxonalar" (backend ham shuni tekshiradi). */
export function AdminHome() {
  const { t } = useI18n();
  const role = useAppSelector((s) => s.auth.user?.role);
  const canWrite = role === "admin";
  const tabs: readonly TabId[] = role === "legal" ? ["customers"] : TABS;
  const loc = useLocation();
  const nav = useNavigate();
  const situation = useSituation();
  const tab: TabId = tabs.find((x) => loc.hash === `#${x}`) ?? tabs[0];
  const [regions, setRegions] = useState<Region[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);

  const reload = useCallback(async () => {
    const [r, d] = await Promise.all([adminApi.regions(), adminApi.districts()]);
    setRegions(r);
    setDistricts(d);
  }, []);
  useEffect(() => { reload().catch(() => undefined); }, [reload]);

  const ref: RefData = { regions, districts, reload, canWrite };
  // Yorliq URL'dagi #hash'da: qo'ng'iroqcha "/admin#situation" ga o'tkazadi
  const pick = (v: TabId) => nav({ hash: `#${v}` }, { replace: true });

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t(role === "legal" ? "customers_title" : "admin_title")}</Typography>
      {!canWrite && tab !== "customers" && tab !== "situation" && <Alert severity="info">{t("read_only")}</Alert>}
      <Paper variant="outlined">
        <Tabs value={tab} onChange={(_, v: TabId) => pick(v)} variant="scrollable" allowScrollButtonsMobile>
          {tabs.map((x) => <Tab key={x} value={x} label={x === "situation" && situation?.unread
            ? <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: 0.75 }}>{t("tab_situation")}<CountPill n={situation.unread} /></Box>
            : t(`tab_${x}`)} />)}
        </Tabs>
      </Paper>
      {tab === "situation" && <SituationTab {...ref} />}
      {tab === "customers" && <CustomersTab {...ref} />}
      {tab === "users" && <UsersTab {...ref} />}
      {tab === "districts" && <DistrictsTab {...ref} />}
      {tab === "vehicles" && <VehiclesTab {...ref} />}
      {tab === "settings" && <SettingsTab {...ref} />}
    </Stack>
  );
}

/** Yorliq ichidagi son: absolute badge emas — yorliq chegarasidan chiqmaydi va kesilmaydi. */
export function CountPill({ n }: { n: number }) {
  return <Box component="span" data-testid="count-pill" sx={{ minWidth: 20, height: 20, px: 0.75, borderRadius: 10, bgcolor: "error.main", color: "error.contrastText",
    fontSize: 12, fontWeight: 600, lineHeight: "20px", textAlign: "center", fontVariantNumeric: "tabular-nums" }}>{n > 99 ? "99+" : n}</Box>;
}

export function districtLabel(districts: District[], id: number | null | undefined): string {
  return districts.find((d) => d.id === id)?.name ?? "—";
}
