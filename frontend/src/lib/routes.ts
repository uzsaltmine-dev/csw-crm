import type { User } from "@/types";

/** Har bir rolning bosh sahifasi. Hali ekrani yo'q rollar "/" da qoladi. */
export function homePath(user: User): string {
  if (user.must_change_password) return "/change-password";
  switch (user.role) {
    case "driver": return "/driver";
    case "gps": return "/gps";
    case "admin":
    case "manager": return "/admin";
    default: return "/";
  }
}
