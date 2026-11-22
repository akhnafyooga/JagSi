export type VitalTone = 'normal' | 'warning' | 'critical';

export interface Vital {
  id: string;
  label: string;
  /** null when the sensor returned no reading; the card then shows a dash. */
  value: number | null;
  unit: string;
  icon: string;
  tone: VitalTone;
  statusLabel: string;
  note: string;
  /**
   * True when the reading comes from a Wokwi potentiometer rather than a real
   * sensor. See docs/hardware-bom.md. The card badges these so a caregiver is
   * never shown a simulated number as if it were a measurement.
   */
  simulated?: boolean;
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
