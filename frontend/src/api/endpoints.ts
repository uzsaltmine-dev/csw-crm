import { api } from "./client";
import { clearTokens, saveTokens, type Tokens } from "@/lib/session";
import { closeSocket } from "@/lib/socket";
import type { Access, AdminUser, Appeal, ChatMessage, ChatThread, ChatThreadType, ChatUnread, RequestDetail, RequestItem, RequestSource, Stats, WasteType, AdminVehicle, DistrictRadius, CompleteResult, Coords, ContractType, CustomerDetail, CustomerListItem, District, DriverTask, FailReason, FileKind,
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

export type UserCreate = { username: string; full_name: string; phone?: string | null; role: Role; district_id?: number | null;
  district_ids?: number[]; language?: string; password: string };
export type UserPatch = Partial<Pick<AdminUser, "full_name" | "phone" | "role" | "district_id" | "district_ids" | "language" | "is_active">>;
type Settings = { gps_radius_m: number; districts: DistrictRadius[] };

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
  settings: () => api.get<Settings>("/admin/settings").then((r) => r.data),
  saveSettings: (gps_radius_m: number) => api.put<Settings>("/admin/settings", { gps_radius_m }).then((r) => r.data),
  saveDistrictRadius: (id: number, gps_radius_m: number | null) => api.put<Settings>(`/admin/districts/${id}/radius`, { gps_radius_m }).then((r) => r.data),
  approveUser: (id: number) => api.post<AdminUser>(`/admin/users/${id}/approve`).then((r) => r.data),
  rejectUser: (id: number) => api.post<AdminUser>(`/admin/users/${id}/reject`).then((r) => r.data),
  permissionCatalog: () => api.get<{ modules: Record<string, string[]> }>("/admin/permissions/catalog").then((r) => r.data),
  access: (id: number) => api.get<Access>(`/admin/users/${id}/access`).then((r) => r.data),
  saveAccess: (id: number, body: { permissions: string[]; district_ids?: number[] }) =>
    api.put<Access>(`/admin/users/${id}/access`, body).then((r) => r.data),
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

export type OrderFields = { waste_type: WasteType; volume_estimate?: number | null; preferred_time?: string | null; note?: string | null;
  caller_name?: string | null; caller_phone?: string | null; source: RequestSource };
export type AppealCreate = OrderFields & { district_id: number; org_name: string; stir?: string | null; address?: string | null; activity_type?: string | null };

export const requestsApi = {
  detail: (id: number) => api.get<RequestDetail>(`/requests/${id}`).then((r) => r.data),
  markSeen: (request_ids: number[]) => api.post("/requests/seen", { request_ids }),
  list: (params: { mine?: boolean; overdue?: boolean; repeat?: boolean; status?: string; district_id?: number; waste_type?: string;
    date_from?: string; date_to?: string; q?: string; limit?: number; offset?: number }) =>
    api.get<{ items: RequestItem[]; total: number }>("/requests", { params }).then((r) => r.data),
  openFor: (customer_id: number) => api.get<RequestItem[]>("/requests/open", { params: { customer_id } }).then((r) => r.data),
  create: (body: OrderFields & { customer_id: number; confirm_repeat?: boolean }) => api.post<RequestItem>("/requests", body).then((r) => r.data),
  cancel: (id: number, reason: string) => api.post<RequestItem>(`/requests/${id}/cancel`, { reason }).then((r) => r.data),
};

export const appealsApi = {
  list: (params: { status?: string; mine?: boolean }) => api.get<Appeal[]>("/appeals", { params }).then((r) => r.data),
  create: (body: AppealCreate) => api.post<Appeal>("/appeals", body).then((r) => r.data),
  accept: (id: number, body: { customer: CustomerFields; contract?: ContractCreate | null }) =>
    api.post<Appeal>(`/appeals/${id}/accept`, body).then((r) => r.data),
  reject: (id: number, reason: string) => api.post<Appeal>(`/appeals/${id}/reject`, { reason }).then((r) => r.data),
};

export type StatPeriod = "today" | "month" | "last10" | "last5";
export type StatMetric = "received" | "repeat" | "pending" | "overdue" | "done" | "not_done";
export interface StatDetail {
  period: StatPeriod; metric: StatMetric; since: string; value: number; granularity: "hour" | "day";
  series: { label: string; date?: string; value: number }[];
  composition: { key: string; value: number }[];
  histogram: { bucket: string; value: number }[];
  districts: { district_id: number; name: string; value: number }[];
}

export const statsApi = {
  summary: (period: StatPeriod) => api.get<Stats>("/stats/summary", { params: { period } }).then((r) => r.data),
  detail: (period: StatPeriod, metric: StatMetric) => api.get<StatDetail>("/stats/detail", { params: { period, metric } }).then((r) => r.data),
  /** Fayl sifatida yuklab olish (tab sessiyasida ham token bilan) */
  export: async (period: StatPeriod, metric: StatMetric, format: "xlsx" | "pdf") => {
    const r = await api.get<Blob>("/stats/export", { params: { period, metric, format }, responseType: "blob", timeout: 120_000 });
    const name = /filename="([^"]+)"/.exec(r.headers["content-disposition"] ?? "")?.[1] ?? `statistika.${format}`;
    const url = URL.createObjectURL(r.data);
    const a = document.createElement("a");
    a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  },
};

export const chatApi = {
  thread: (type: ChatThreadType, id: number, before_id?: number) =>
    api.get<ChatThread>(`/chat/${type}/${id}`, { params: { before_id } }).then((r) => r.data),
  sendText: (type: ChatThreadType, id: number, text: string) => api.post<ChatMessage>(`/chat/${type}/${id}/text`, { text }).then((r) => r.data),
  sendVoice: (type: ChatThreadType, id: number, blob: Blob, duration: number) => {
    const fd = new FormData();
    const ext = blob.type.includes("ogg") ? "ogg" : blob.type.includes("mp4") ? "m4a" : "webm";
    fd.append("audio", blob, `voice.${ext}`);
    fd.append("duration", String(duration));
    return api.post<ChatMessage>(`/chat/${type}/${id}/voice`, fd, { timeout: 60_000 }).then((r) => r.data);
  },
  read: (type: ChatThreadType, id: number) => api.post(`/chat/${type}/${id}/read`),
  unread: () => api.get<ChatUnread>("/chat/unread").then((r) => r.data),
  /** Audio tab rejimida ham (Bearer) ishlashi uchun axios orqali blob bo'lib olinadi */
  audio: (messageId: number) => api.get<Blob>(`/chat/audio/${messageId}`, { responseType: "blob" }).then((r) => r.data),
};
