import { api } from "./client";
import type { CompleteResult, Coords, DriverTask, FailReason, FileKind, Shift, User } from "@/types";

export const authApi = {
  login: (username: string, password: string) => api.post<User>("/auth/login", { username, password }).then((r) => r.data),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout"),
};

export const driverApi = {
  currentShift: () => api.get<Shift | null>("/driver/shift/current").then((r) => r.data),
  startShift: (id: number, odometer: number, fuel: number, photo: Blob) => {
    const fd = new FormData();
    fd.append("odometer", String(odometer));
    fd.append("fuel", String(fuel));
    fd.append("photo", photo, "vehicle.jpg");
    return api.post<Shift>(`/driver/shift/${id}/start`, fd).then((r) => r.data);
  },
  endShift: (id: number, odometer: number, fuel: number) =>
    api.post<Shift>(`/driver/shift/${id}/end`, { odometer, fuel }).then((r) => r.data),
  tasks: () => api.get<DriverTask[]>("/driver/tasks").then((r) => r.data),
  enroute: (id: number) => api.post<DriverTask>(`/driver/requests/${id}/enroute`).then((r) => r.data),
  upload: (id: number, kind: FileKind, file: Blob, coords?: Coords | null) => {
    const fd = new FormData();
    fd.append("kind", kind);
    fd.append("file", file, `${kind}.${file.type === "image/png" ? "png" : "jpg"}`);
    if (coords) {
      fd.append("lat", String(coords.lat));
      fd.append("lng", String(coords.lng));
    }
    return api.post(`/driver/requests/${id}/files`, fd).then((r) => r.data);
  },
  location: (c: Coords) => api.post("/driver/location", { lat: c.lat, lng: c.lng, accuracy_m: c.accuracy }),
  complete: (id: number, body: { containers: number; volume_m3: number; note: string; lat: number; lng: number }) =>
    api.post<CompleteResult>(`/driver/requests/${id}/complete`, body).then((r) => r.data),
  fail: (id: number, reason: FailReason, note?: string) =>
    api.post<DriverTask>(`/driver/requests/${id}/fail`, { reason, note }).then((r) => r.data),
};
