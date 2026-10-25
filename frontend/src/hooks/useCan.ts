import { useCallback } from "react";
import { useAppSelector } from "@/store";

/** Ruxsat tekshiruvi (ekranda): admin — hammasi; boshqalar — /auth/me dagi ruxsatlar. Server baribir o'zi tekshiradi. */
export function useCan() {
  const user = useAppSelector((s) => s.auth.user);
  return useCallback((code: string) => !!user && (user.role === "admin" || (user.permissions ?? []).includes(code)), [user]);
}
