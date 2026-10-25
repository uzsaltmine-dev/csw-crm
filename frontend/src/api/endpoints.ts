import { api } from "./client";
import { clearTokens, saveTokens, type Tokens } from "@/lib/session";
import { closeSocket } from "@/lib/socket";
import type { AdminUser, AdminVehicle, CompleteResult, Coords, ContractType, CustomerDetail, CustomerListItem, District, DriverTask, FailReason, FileKind,
  GpsDriver, ImportBatch, ImportResult, LocationStatus, Region, Role, Shift, SituationEvent, SituationLevel, User, Vehicle } from "@/types";

export const gpsApi = {
  drivers: () => api.get<GpsDriver[]>("/gps/drivers").then((r) => r.data),
  freeVehicles: () => api.get<Vehicle[]>("/gps/vehicles", { params: { free: true } }).then((r) => r.data),
  openShift: (driver_id: number, vehicle_id: number) => api.post<Shift>("/gps/shifts", { driver_id, vehicle_id }).then((r) => r.data),
  newRequests: () => api.get<DriverTask[]>("/gps/requests").then((r) => r.data),
  assign: (requestId: number, driver_id: number) => api.post<DriverTask>(`/gps/requests/${requestId}/assign`, { driver_id }).then((r) => r.data),
};

export const authApi = {
  login: (username: string, password: string) => api.post<User & Partial<Tokens>>("/auth/login", { username, password }).then((r) => {
    saveTokens(r.data);
    const { access_token: _a, refresh_token: _r, ...user } = r.data;
    return user as User;
  }),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout").finally(() => { clearTokens(); closeSocket(); }),
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
      if (coords.accuracy != null) fd.append("accuracy", String(coords.accuracy));
    }
    return api.post(`/driver/requests/${id}/files`, fd).then((r) => r.data);
  },
  location: (c: Coords) => api.post("/driver/location", { lat: c.lat, lng: c.lng, accuracy_m: c.accuracy }),
  complete: (id: number, body: { containers: number; volume_m3: number; note: string; lat: number; lng: number }) =>
    api.post<CompleteResult>(`/driver/requests/${id}/complete`, body).then((r) => r.data),
  fail: (id: number, reason: FailReason, note?: string) =>
    api.post<DriverTask>(`/driver/requests/${id}/fail`, { reason, note }).then((r) => r.data),
};

export type CustomerQuery = { district_id?: number; q?: string; incomplete?: boolean; location?: LocationStatus; limit?: number; offset?: number };
export type CustomerFields = { name: string; district_id: number; stir?: string | null; director?: string | null; phone?: string | null; address?: string | null; activity_type?: string | null };
export type ContractCreate = { number: string; type: ContractType; signed_on?: string | null; price?: number | null; valid_from: string; valid_to: string };

export const customersApi = {
  search: (params: CustomerQuery) => api.get<{ items: CustomerListItem[]; total: number }>("/customers", { params }).then((r) => r.data),
  get: (id: number) => api.get<CustomerDetail>(`/customers/${id}`).then((r) => r.data),
  create: (body: CustomerFields) => api.post<CustomerDetail>("/customers", body).then((r) => r.data),
  update: (id: number, body: Partial<Omit<CustomerFields, "district_id">>) => api.patch<CustomerDetail>(`/customers/${id}`, body).then((r) => r.data),
  addContact: (id: number, body: { name?: string | null; phone: string }) => api.post<CustomerDetail>(`/customers/${id}/contacts`, body).then((r) => r.data),
  addContract: (id: number, body: ContractCreate) => api.post<CustomerDetail>(`/customers/${id}/contracts`, body).then((r) => r.data),
  confirmLocation: (id: number, coords?: { lat: number; lng: number }) =>
    api.post<CustomerDetail>(`/customers/${id}/location/confirm`, coords ?? {}).then((r) => r.data),
  importFile: (file: File, dryRun: boolean) => {
    const fd = new FormData();
    fd.append("file", file, file.name);
    return api.post<ImportResult>("/admin/import/customers", fd, { params: { dry_run: dryRun }, timeout: 180_000 }).then((r) => r.data);
  },
  batches: () => api.get<ImportBatch[]>("/admin/import/batches").then((r) => r.data),
};

export type SituationQuery = { level?: SituationLevel; kind?: string; district_id?: number; date_from?: string; date_to?: string;
  unread?: boolean; limit?: number; offset?: number };

export const situationApi = {
  list: (params: SituationQuery) =>
    api.get<{ items: SituationEvent[]; total: number; unread: number; last_read_id: number }>("/situation", { params }).then((r) => r.data),
  unread: () => api.get<{ unread: number }>("/situation/unread").then((r) => r.data),
  markRead: (up_to_id?: number) => api.post<{ unread: number; last_read_id: number }>("/situation/read", { up_to_id }).then((r) => r.data),
};
