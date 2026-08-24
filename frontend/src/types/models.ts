export type Role = 'farmer' | 'vet' | 'regulator' | 'admin';

export interface User {
  id: number;
  full_name: string;
  email: string;
  role: Role;
  farm_id: number | null;
  phone?: string | null;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  role: Role;
  farm_id: number | null;
  full_name: string;
}

export interface TissueStatus {
  tissue: string;
  clears_at: string;
  clears_at_display: string;
  countdown: string;
  drug_name: string | null;
  administration_id: number;
}

export interface ComplianceRow {
  animal_id: number;
  tag_id: string;
  species: string;
  breed?: string | null;
  production_status: string;
  overall: 'WITHDRAWAL_ACTIVE' | 'CLEAR_TODAY' | 'CLEAR';
  under_withdrawal: boolean;
  tissues: TissueStatus[];
  next_clearance: string | null;
}

export interface Animal {
  id: number;
  farm_id: number;
  tag_id: string;
  species: string;
  breed: string | null;
  sex: string;
  production_status: string;
  weight_kg: number | null;
  status: string;
  qr_code: string;
}

export interface DrugRule {
  id: number;
  drug_id: number;
  species: string;
  withdrawal_milk_days: number | null;
  withdrawal_meat_days: number | null;
  withdrawal_eggs_days: number | null;
  mrl_milk_ug_kg: number | null;
  mrl_meat_ug_kg: number | null;
  mrl_eggs_ug_kg: number | null;
  source: string;
}

export interface Drug {
  id: number;
  generic_name: string;
  active_ingredient: string | null;
  drug_class: string;
  aware_class: 'Access' | 'Watch' | 'Reserve';
  prohibited_in_food_animals: boolean;
  prohibited_in_lactating_animals: boolean;
  notes: string | null;
  rules: DrugRule[];
}

export interface Alert {
  id: number;
  farm_id: number;
  animal_id: number | null;
  type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  is_read: boolean;
  resolved: boolean;
  created_at: string | null;
}

export interface SaleEvent {
  id: number;
  farm_id: number;
  animal_tag: string | null;
  product_type: string;
  quantity: number;
  unit: string;
  buyer_name: string | null;
  was_under_withdrawal: boolean;
  is_violation: boolean;
  occurred_at: string | null;
}

export interface LedgerEvent {
  seq: number;
  event_type: string;
  entity_id: number;
  payload: string;
  prev_hash: string;
  hash: string;
  recorded_at: string | null;
}

export interface LedgerVerify {
  valid: boolean;
  length: number;
  first_invalid_seq: number | null;
  algorithm: string;
}

export interface RiskFactor {
  factor: string;
  weight: number;
}

export interface MrlPrediction {
  risk: number;
  band: 'low' | 'medium' | 'high';
  top_factors: RiskFactor[];
}

export interface AnimalPrediction {
  animal_id: number;
  tag_id: string;
  mrl_violation_risk: MrlPrediction | null;
  outbreak_risk: (MrlPrediction & { risk: number }) | null;
  trained_on: string;
}

export interface SensorReading {
  recorded_at: string | null;
  device_id: string;
  body_temp_c: number;
  activity_index: number;
  rumination_min: number | null;
}

export interface ChatResponse {
  answer: string;
  mode: 'claude' | 'offline';
  sources: string[];
}

/* ---------------- installs / tracking ---------------- */

export type VisitStatus = 'requested' | 'scheduled' | 'completed' | 'cancelled';

export interface InstallVisit {
  id: number;
  farm_id: number;
  farm_name: string | null;
  status: VisitStatus;
  preferred_date: string;
  preferred_date_display: string;
  preferred_slot: 'morning' | 'afternoon' | 'evening';
  notes: string | null;
  scheduled_at: string | null;
  scheduled_at_display: string | null;
  official_name: string | null;
  official_phone: string | null;
  completed_at_display: string | null;
  cancel_reason: string | null;
  created_at: string;
  applied?: string[];
}

export interface Geofence {
  center_lat: number;
  center_lng: number;
  radius_m: number;
  enabled: boolean;
  updated_at?: string;
}

export interface LiveAnimal {
  animal_id: number;
  tag_id: string;
  species: string;
  breed: string | null;
  lat: number;
  lng: number;
  recorded_at: string;
  recorded_at_display: string;
  speed_kmh: number;
  distance_from_center_m: number;
  inside_geofence: boolean;
  breach: boolean;
}

export interface LiveTracking {
  farm_id: number;
  geofence: Geofence;
  animals: LiveAnimal[];
}

export interface TrackPoint {
  lat: number;
  lng: number;
  recorded_at: string;
  inside_geofence: boolean;
}
