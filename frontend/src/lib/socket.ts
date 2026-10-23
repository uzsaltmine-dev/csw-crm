import { io, type Socket } from "socket.io-client";

let socket: Socket | null = null;

/** Cookie (access_token) orqali autentifikatsiya; Nginx/Vite /socket.io ni backend'ga uzatadi. */
export function getSocket(): Socket {
  socket ??= io({ path: "/socket.io", withCredentials: true, transports: ["websocket", "polling"] });
  return socket;
}

export function closeSocket(): void {
  socket?.disconnect();
  socket = null;
}
