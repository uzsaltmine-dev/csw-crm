export type Role = "admin" | "manager" | "operator" | "gps" | "legal" | "driver";
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
}

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

export interface Customer {
  id: number;
  fixed_no: string;
  stir: string;
  name: string;
  director: string | null;
  phone: string | null;
  address: string | null;
  district_id: number;
  lat: number;
  lng: number;
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
}

export interface CompleteResult {
  request: DriverTask;
  act: { containers: number; volume_m3: string; distance_m: number; radius_m: number; in_radius: boolean; vehicle_plate: string; completed_at: string };
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
