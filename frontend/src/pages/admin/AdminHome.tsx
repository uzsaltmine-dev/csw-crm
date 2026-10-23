import { useCallback, useEffect, useState } from "react";
import { Alert, Paper, Stack, Tab, Tabs, Typography } from "@mui/material";
import { adminApi } from "@/api/endpoints";
import { useI18n } from "@/i18n/I18nContext";
import { useAppSelector } from "@/store";
import type { District, Region } from "@/types";
import { DistrictsTab } from "./DistrictsTab";
import { SettingsTab } from "./SettingsTab";
import { UsersTab } from "./UsersTab";
import { VehiclesTab } from "./VehiclesTab";

const TABS = ["users", "districts", "vehicles", "settings"] as const;
type TabId = (typeof TABS)[number];

export interface RefData { regions: Region[]; districts: District[]; reload: () => Promise<void>; canWrite: boolean }

/** Admin: yozadi; Manager: faqat ko'radi (backend ham shuni tekshiradi). */
export function AdminHome() {
  const { t } = useI18n();
  const role = useAppSelector((s) => s.auth.user?.role);
  const canWrite = role === "admin";
  const [tab, setTab] = useState<TabId>(() => (TABS.find((x) => location.hash === `#${x}`) ?? "users"));
  const [regions, setRegions] = useState<Region[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);

  const reload = useCallback(async () => {
    const [r, d] = await Promise.all([adminApi.regions(), adminApi.districts()]);
    setRegions(r);
    setDistricts(d);
  }, []);
  useEffect(() => { reload().catch(() => undefined); }, [reload]);

  const ref: RefData = { regions, districts, reload, canWrite };
  const pick = (v: TabId) => { setTab(v); history.replaceState(null, "", `#${v}`); };

  return (
    <Stack spacing={2}>
      <Typography variant="h5">{t("admin_title")}</Typography>
      {!canWrite && <Alert severity="info">{t("read_only")}</Alert>}
      <Paper variant="outlined">
        <Tabs value={tab} onChange={(_, v: TabId) => pick(v)} variant="scrollable" allowScrollButtonsMobile>
          <Tab value="users" label={t("tab_users")} />
          <Tab value="districts" label={t("tab_districts")} />
          <Tab value="vehicles" label={t("tab_vehicles")} />
          <Tab value="settings" label={t("tab_settings")} />
        </Tabs>
      </Paper>
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
