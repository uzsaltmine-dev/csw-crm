import { io, type Socket } from "socket.io-client";
import { getTokens } from "@/lib/session";

let socket: Socket | null = null;

/** Cookie (access_token) orqali autentifikatsiya; Nginx/Vite /socket.io ni backend'ga uzatadi. */
export function getSocket(): Socket {
  // Tab rejimida token auth orqali (har qayta ulanishda yangisi olinadi); oddiy rejimda cookie
  socket ??= io({ path: "/socket.io", withCredentials: true, transports: ["websocket", "polling"],
    auth: (cb) => { const tk = getTokens(); cb(tk ? { token: tk.access_token } : {}); } });
  return socket;
}

export function closeSocket(): void {
  socket?.disconnect();
  socket = null;
}
