import { useCallback, useEffect, useState } from "react";
import { Alert, Badge, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
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
            ? <Badge color="error" badgeContent={situation.unread} max={99} sx={{ "& .MuiBadge-badge": { right: -12 } }}>{t("tab_situation")}</Badge>
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

export function districtLabel(districts: District[], id: number | null | undefined): string {
  return districts.find((d) => d.id === id)?.name ?? "—";
}
