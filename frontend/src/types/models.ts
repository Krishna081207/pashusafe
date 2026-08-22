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
