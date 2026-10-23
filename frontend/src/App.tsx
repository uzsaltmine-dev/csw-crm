import { useEffect, type ReactNode } from "react";
import { Alert, Box, CircularProgress } from "@mui/material";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { DriverLayout } from "@/components/DriverLayout";
import { useI18n } from "@/i18n/I18nContext";
import { closeSocket, getSocket } from "@/lib/socket";
import { LoginPage } from "@/pages/LoginPage";
import { ActPage } from "@/pages/driver/ActPage";
import { DriverHome } from "@/pages/driver/DriverHome";
import { useAppDispatch, useAppSelector } from "@/store";
import { loadMe, sessionExpired } from "@/store/authSlice";
import { refreshDriver } from "@/store/driverSlice";
import type { Role } from "@/types";

function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { user, status } = useAppSelector((s) => s.auth);
  if (status !== "ready") return <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh" }}><CircularProgress /></Box>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to="/" replace />;
  return <>{children}</>;
}

/** Haydovchi bo'limi: holatni yuklaydi va Socket.IO orqali yangilanib turadi. */
function DriverSection({ children }: { children: ReactNode }) {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch(refreshDriver());
    const s = getSocket();
    const onUpdate = () => dispatch(refreshDriver());
    s.on("request:updated", onUpdate);
    s.on("connect", onUpdate); // qayta ulanganda o'tkazib yuborilganlarni olish
    return () => { s.off("request:updated", onUpdate); s.off("connect", onUpdate); closeSocket(); };
  }, [dispatch]);
  return <DriverLayout>{children}</DriverLayout>;
}

function Home() {
  const user = useAppSelector((s) => s.auth.user);
  const status = useAppSelector((s) => s.auth.status);
  if (status !== "ready") return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === "driver") return <Navigate to="/driver" replace />;
  return <Alert severity="info" sx={{ m: 2 }}>Bu rol uchun panel keyingi bosqichda qo'shiladi ({user.role}).</Alert>;
}

export function App() {
  const dispatch = useAppDispatch();
  const { t } = useI18n();
  useEffect(() => {
    dispatch(loadMe());
    const onLogout = () => dispatch(sessionExpired());
    window.addEventListener("csw:logout", onLogout);
    return () => window.removeEventListener("csw:logout", onLogout);
  }, [dispatch]);
  useEffect(() => { document.title = t("app_name"); }, [t]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/driver" element={<RequireRole role="driver"><DriverSection><DriverHome /></DriverSection></RequireRole>} />
        <Route path="/driver/requests/:id" element={<RequireRole role="driver"><DriverSection><ActPage /></DriverSection></RequireRole>} />
        <Route path="*" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}
