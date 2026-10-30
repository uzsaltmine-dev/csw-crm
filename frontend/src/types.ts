export type Role = "admin" | "manager" | "operator" | "gps" | "legal" | "driver" | "accountant";
export type ShiftStatus = "opened" | "active" | "closed";
export type RequestStatus = "new" | "assigned" | "enroute" | "onsite" | "done" | "suspect" | "failed" | "cancelled";
export type FileKind = "before" | "after" | "face" | "sign";
export type FailReason = "no_waste" | "no_recipient" | "no_access";

export interface User {
  id: number;
  username: string;
  full_name: string;
  phone: string | null;
  role: Role;
  district_id: number | null;
  language: string;
  must_change_password: boolean;
  /** Ruxsat kodlari ("customers.edit" ...); admin — hammasi */
  permissions?: string[];
  /** Ishlash doirasi (tumanlar) */
  district_ids?: number[];
}

export interface AdminUser extends User {
  is_active: boolean;
  locked_until: string | null;
  created_at: string;
  district_ids: number[];
  permissions: string[];
  approval_status: "approved" | "pending" | "rejected";
  created_by_id: number | null;
}

export interface Access {
  user_id: number;
  role: Role;
  permissions: string[];
  district_ids: number[];
  multi_district: boolean;
  grantable: string[];
  assignable_district_ids: number[] | null;
}

export interface DistrictRadius { id: number; name: string; gps_radius_m: number | null; effective_m: number }

export interface Region { id: number; name: string }
export interface District { id: number; name: string; region_id: number; is_active: boolean; gps_radius_m?: number | null }
export interface AdminVehicle { id: number; plate: string; model: string | null; district_id: number; is_active: boolean }

export interface Vehicle {
  id: number;
  plate: string;
  model: string | null;
  district_id: number;
}

export interface Shift {
  id: number;
  status: ShiftStatus;
  driver_id: number;
  district_id: number;
  vehicle: Vehicle;
  started_at: string | null;
  ended_at: string | null;
  odometer_start: number | null;
  odometer_end: number | null;
  fuel_start: string | null;
  fuel_end: string | null;
  distance_km: number | null;
  fuel_used: string | null;
}

export interface GpsDriver {
  id: number;
  full_name: string;
  phone: string | null;
  shift: Shift | null;
}

export type LocationStatus = "none" | "pending" | "confirmed";

export interface Customer {
  id: number;
  fixed_no: string;
  /** Korxona maxsus raqami (3 harf + 2 raqam, masalan KTR47) — STIR o'rniga */
  code: string | null;
  stir: string | null;
  name: string;
  director: string | null;
  phone: string | null;
  address: string | null;
  district_id: number;
  lat: number | null;
  lng: number | null;
  location_status: LocationStatus;
  /** "stir" | "contract" — bo'lsa haydovchi biriktirilmaydi */
  missing_fields: string[];
}

export interface CustomerListItem extends Customer {
  activity_type: string | null;
  source: "excel" | "manual" | string;
  contacts_count: number;
}

export interface Contact { id: number; name: string | null; phone: string }

export type ContractType = "per_trip" | "by_volume" | "monthly" | "one_off";

export interface ContractFull {
  id: number;
  number: string;
  signed_on: string | null;
  type: ContractType;
  price: string | null;
  valid_from: string;
  valid_to: string;
  is_active: boolean;
}

export interface CustomerDetail extends CustomerListItem {
  contacts: Contact[];
  contracts: ContractFull[];
  created_at: string;
}

export interface ImportResult {
  sheet: string;
  file_kind: string;
  rows_total: number;
  rows_ok: number;
  rows_skipped: number;
  septic_rows: number;
  customers_new: number;
  customers_existing: number;
  contacts_added: number;
  by_district: Record<string, number>;
  errors: { row: number; message: string }[];
  batch_id: number | null;
  dry_run: boolean;
}

export interface ImportBatch {
  id: number;
  file_name: string;
  uploaded_by_id: number;
  rows_total: number;
  customers_created: number;
  customers_merged: number;
  rows_skipped: number;
  created_at: string;
}

export interface Contract {
  id: number;
  number: string;
  signed_on: string | null;
  type: string;
}

export interface DriverTask {
  id: number;
  number: string | null;
  status: RequestStatus;
  waste_type: string;
  volume_estimate: string | null;
  preferred_time: string | null;
  note: string | null;
  naryad_no: string | null;
  district_id: number;
  driver_id: number | null;
  created_at: string;
  assigned_at: string | null;
  customer: Customer;
  contract: Contract | null;
  files: FileKind[];
  source?: RequestSource;
  due_at?: string | null;
  overdue?: boolean;
  is_repeat?: boolean;
  seen?: boolean | null;
  stage?: Stage;
  vehicle?: Vehicle | null;
  driver_name?: string | null;
  finished_at?: string | null;
  order_form?: OrderFormBrief | null;
}

/** Uch bosqich: qizil — mashina biriktirilmagan, sariq — chiqindi olinishi kutilmoqda, yashil — bajarilgan */
export type Stage = "red" | "black" | "yellow" | "green" | "cancelled";
export interface OrderFormBrief {
  id: number;
  number: string;
  printed: boolean;
  print_count: number;
  printed_at: string | null;
  reprint_allowed: boolean;
  locked: boolean;
  attempts_left: number;
  has_scan: boolean;
  verified: boolean;
  closed_at: string | null;
  closed_via: "form" | "act" | null;
  volume_m3: number | null;
  waste_kind: "solid" | "liquid" | null;
}
/** Varaqaning qog'oz ko'rinishi (maxfiy kodsiz) */
export interface OrderPaper {
  form: OrderFormBrief;
  request_number: string | null;
  provider: string;
  customer: { name: string; code: string | null; address: string | null };
  vehicle: { plate: string; model: string | null } | null;
  driver_name: string | null;
  assigned_at: string | null;
  waste_type: string;
}
export type Service = "legal" | "individual";
export interface ScheduleRow { id?: number; vehicle_id: number; plate?: string; model?: string | null; driver_id: number | null;
  driver_name?: string | null; service: Service; mahallas: string | null }
export interface ScheduleDay { day: string; district_id: number; rows: ScheduleRow[];
  vehicles: { id: number; plate: string; model: string | null }[]; drivers: { id: number; full_name: string; phone: string | null }[] }
export interface VehicleOption { vehicle_id: number; plate: string; model: string | null; service: Service | null; driver_id: number | null;
  driver_name: string | null; distance_m: number | null; position_at: string | null; position_source: string | null; available: boolean }

export type RequestSource = "phone" | "telegram" | "excel" | "walk_in";
export type WasteType = "household" | "construction" | "bulky" | "green" | "septic";

export interface RequestItem extends Omit<DriverTask, "files"> {
  caller_name: string | null;
  caller_phone: string | null;
  repeat_of_id: number | null;
  created_by_id: number | null;
  finished_at: string | null;
  cancel_reason: string | null;
}

export interface RequestDetail extends RequestItem {
  driver_name: string | null;
  created_by_name: string | null;
  events: { status: RequestStatus; note: string | null; actor_name: string | null; created_at: string }[];
}

export interface Appeal {
  id: number;
  number: string | null;
  status: "new" | "accepted" | "rejected";
  district_id: number;
  org_name: string;
  stir: string | null;
  address: string | null;
  activity_type: string | null;
  caller_name: string | null;
  caller_phone: string | null;
  source: RequestSource;
  waste_type: WasteType;
  volume_estimate: string | null;
  preferred_time: string | null;
  note: string | null;
  created_by_id: number | null;
  reviewed_at: string | null;
  reject_reason: string | null;
  customer_id: number | null;
  request_id: number | null;
  created_at: string;
}

export interface StatMetrics {
  received: number; repeat: number; pending: number; overdue: number; done: number; not_done: number;
  done_share: number; not_done_share: number;
}
export interface Stats { period: string; since: string; total: StatMetrics; districts: (StatMetrics & { district_id: number; name: string })[] }

export interface CompleteResult {
  request: DriverTask;
  act: { containers: number; volume_m3: string; distance_m: number | null; radius_m: number; in_radius: boolean | null; vehicle_plate: string; completed_at: string };
}

export interface ApiErrorBody {
  error?: { code: string; message: string };
  detail?: unknown;
}

export interface Coords {
  lat: number;
  lng: number;
  accuracy?: number;
}

export type SituationLevel = "info" | "warning" | "error";

export interface SituationEvent {
  id: number;
  level: SituationLevel;
  kind: string;
  message: string;
  params: Record<string, unknown>;
  district_id: number | null;
  actor_id: number | null;
  actor_name?: string | null;
  ref_type: string | null;
  ref_id: number | null;
  created_at: string;
  resolved?: boolean;
}

export type ChatThreadType = "request" | "appeal";
export interface ChatMessage {
  id: number;
  thread_type: ChatThreadType;
  thread_id: number;
  author_id: number;
  author_name: string;
  author_role: Role | null;
  kind: "text" | "voice";
  text: string | null;
  duration_s: number | null;
  expired: boolean;
  has_audio: boolean;
  created_at: string;
}
export interface ChatThread {
  thread_type: ChatThreadType;
  thread_id: number;
  number: string | null;
  title: string;
  closed: boolean;
  can_write: boolean;
  appeal_id: number | null;
  has_more: boolean;
  items: ChatMessage[];
}
export interface ChatUnreadThread { thread_type: ChatThreadType; thread_id: number; number: string | null; title: string; district_id: number; count: number; last_id: number }
export interface ChatUnread { total: number; threads: ChatUnreadThread[] }
/** Socket "chat:message": xabar + yozishma haqida qisqa ma'lumot */
export interface ChatEvent extends ChatMessage {
  thread: { type: ChatThreadType; id: number; number: string | null; title: string; district_id: number; request_id: number | null };
}

export interface CompanyRow { customer_id: number; name: string; code: string | null; district_id: number; debit: number; credit: number;
  balance: number; volume_m3: number; green_count: number }
export interface CompanyPeriod { from: string; to: string; opening: number; charged: number; paid: number; closing: number; debit: number; credit: number }
export interface CompanyCompare { customer: { id: number; name: string; code: string | null; stir: string | null }; periods: CompanyPeriod[];
  months: { month: string; charged: number; paid: number; closing: number }[]; now: CompanyRow }
export interface GreenItem { id: number; number: string | null; day: string; volume_m3: number; waste_type: string; plate: string | null;
  driver_name: string | null; closed_via: "form" | "act" | null; status: string; contract: string | null; amount: number }
export interface PaymentItem { id: number; customer_id: number; customer_name: string | null; code: string | null; paid_on: string; amount: number;
  doc_no: string | null; note: string | null; source: "manual" | "import"; created_at: string; cancelled: boolean; cancel_reason: string | null }
