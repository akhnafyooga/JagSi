export type VitalTone = 'normal' | 'warning' | 'critical';

export interface Vital {
  id: string;
  label: string;
  value: number;
  unit: string;
  icon: string;
  tone: VitalTone;
  statusLabel: string;
  note: string;
}

export interface ElderProfile {
  name: string;
  fullName: string;
  age: number;
  gender: string;
  condition: string;
  address: string;
  caregiver: string;
}

export interface AlertItem {
  id: string;
  title: string;
  description: string;
  time: string;
  tone: 'warning' | 'critical' | 'info';
  icon: string;
}

export interface Medication {
  id: string;
  name: string;
  dose: string;
  schedule: string;
  taken: boolean;
}

export interface TrendPoint {
  label: string;
  value: number;
}
