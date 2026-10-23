import { api } from "./client";
import type { AdminUser, AdminVehicle, CompleteResult, Coords, District, DriverTask, FailReason, FileKind, GpsDriver, Region, Role, Shift, User, Vehicle } from "@/types";

export const gpsApi = {
  drivers: () => api.get<GpsDriver[]>("/gps/drivers").then((r) => r.data),
  freeVehicles: () => api.get<Vehicle[]>("/gps/vehicles", { params: { free: true } }).then((r) => r.data),
  openShift: (driver_id: number, vehicle_id: number) => api.post<Shift>("/gps/shifts", { driver_id, vehicle_id }).then((r) => r.data),
  newRequests: () => api.get<DriverTask[]>("/gps/requests").then((r) => r.data),
  assign: (requestId: number, driver_id: number) => api.post<DriverTask>(`/gps/requests/${requestId}/assign`, { driver_id }).then((r) => r.data),
};

export const authApi = {
  login: (username: string, password: string) => api.post<User>("/auth/login", { username, password }).then((r) => r.data),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout"),
  changePassword: (current_password: string, new_password: string) =>
    api.post<User>("/auth/change-password", { current_password, new_password }).then((r) => r.data),
};

export type UserCreate = { username: string; full_name: string; phone?: string | null; role: Role; district_id?: number | null; language?: string; password: string };
export type UserPatch = Partial<Pick<AdminUser, "full_name" | "phone" | "role" | "district_id" | "language" | "is_active">>;

export const adminApi = {
  users: () => api.get<AdminUser[]>("/admin/users").then((r) => r.data),
  createUser: (body: UserCreate) => api.post<AdminUser>("/admin/users", body).then((r) => r.data),
  updateUser: (id: number, body: UserPatch) => api.patch<AdminUser>(`/admin/users/${id}`, body).then((r) => r.data),
  resetPassword: (id: number, password: string) => api.post<AdminUser>(`/admin/users/${id}/reset-password`, { password }).then((r) => r.data),
  regions: () => api.get<Region[]>("/admin/regions").then((r) => r.data),
  districts: () => api.get<District[]>("/admin/districts").then((r) => r.data),
  createDistrict: (name: string, region_id: number) => api.post<District>("/admin/districts", { name, region_id }).then((r) => r.data),
  updateDistrict: (id: number, body: Partial<Pick<District, "name" | "is_active">>) => api.patch<District>(`/admin/districts/${id}`, body).then((r) => r.data),
  vehicles: () => api.get<AdminVehicle[]>("/admin/vehicles").then((r) => r.data),
  createVehicle: (body: { plate: string; model?: string | null; district_id: number }) => api.post<AdminVehicle>("/admin/vehicles", body).then((r) => r.data),
  updateVehicle: (id: number, body: Partial<Omit<AdminVehicle, "id">>) => api.patch<AdminVehicle>(`/admin/vehicles/${id}`, body).then((r) => r.data),
  settings: () => api.get<{ gps_radius_m: number }>("/admin/settings").then((r) => r.data),
  saveSettings: (gps_radius_m: number) => api.put<{ gps_radius_m: number }>("/admin/settings", { gps_radius_m }).then((r) => r.data),
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
