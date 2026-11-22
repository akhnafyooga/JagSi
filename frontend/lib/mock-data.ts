import type {
  AlertItem,
  ElderProfile,
  Medication,
  TrendPoint,
  Vital,
} from './types';

// Static demo data. Replace with live telemetry from the FastAPI backend
// (WebSocket / REST) once Sprint 5 integration lands.
export const elder: ElderProfile = {
  name: 'Ibu Sari',
  fullName: 'Ibu Sari Rahayu',
  age: 72,
  gender: 'Perempuan',
  condition: 'Hipertensi ringan',
  address: 'Jalan Melati No. 12, Yogyakarta',
  caregiver: 'Rafi (Anak)',
};

export const vitals: Vital[] = [
  {
    id: 'heart-rate',
    label: 'Detak Jantung',
    value: 78,
    unit: 'bpm',
    icon: 'favorite',
    tone: 'normal',
    statusLabel: 'Normal',
    note: 'Rentang normal 60–100 bpm',
  },
  {
    id: 'spo2',
    label: 'Saturasi Oksigen',
    value: 98,
    unit: '%',
    icon: 'water_drop',
    tone: 'normal',
    statusLabel: 'Normal',
    note: 'Di atas 95%',
  },
  {
    id: 'temperature',
    label: 'Suhu Tubuh',
    value: 36.5,
    unit: '°C',
    icon: 'thermostat',
    tone: 'normal',
    statusLabel: 'Normal',
    note: 'Rentang normal 36.5–37.5°C',
  },
  {
    id: 'battery',
    label: 'Baterai Smartwear',
    value: 86,
    unit: '%',
    icon: 'battery_full',
    tone: 'normal',
    statusLabel: 'Terisi',
    note: 'Cukup untuk 3 hari',
  },
];

export const fallStatus = {
  status: 'Aman',
  tone: 'normal' as const,
  label: 'Status Gerak / Jatuh',
  note: 'Aman & terdeteksi aktif',
};

export const aiSummary = {
  text: 'Kondisi kesehatan Ibu Sari stabil hari ini. Detak jantung dan saturasi oksigen berada dalam rentang normal. Tidak ada indikasi risiko jatuh.',
  updatedAt: 'Analisis 1 jam lalu',
  model: 'JagSi AI',
};

export const alerts: AlertItem[] = [
  {
    id: 'a1',
    title: 'Peringatan Gerakan Tiba-tiba',
    description: 'Akselerasi tidak wajar terdeteksi pukul 06.12 WIB.',
    time: '06.12 WIB',
    tone: 'warning',
    icon: 'directions_run',
  },
  {
    id: 'a2',
    title: 'Jadwal Obat Diminum',
    description: 'Amlodipine 5mg belum dikonfirmasi diminum.',
    time: '07.00 WIB',
    tone: 'info',
    icon: 'medication',
  },
  {
    id: 'a3',
    title: 'Baterai Smartwear 20%',
    description: 'Segera isi daya perangkat wearable.',
    time: 'Kemarin',
    tone: 'critical',
    icon: 'battery_alert',
  },
  {
    id: 'a4',
    title: 'Detak Jantung Rendah Saat Tidur',
    description: 'Terpantau 48 bpm selama 4 menit pukul 02.30 WIB.',
    time: '02.30 WIB',
    tone: 'warning',
    icon: 'monitor_heart',
  },
];

export const medications: Medication[] = [
  {
    id: 'm1',
    name: 'Amlodipine 5mg',
    dose: '1 tablet',
    schedule: '07.00 — setelah sarapan',
    taken: true,
  },
  {
    id: 'm2',
    name: 'Losartan 50mg',
    dose: '1 tablet',
    schedule: '12.00 — siang hari',
    taken: false,
  },
  {
    id: 'm3',
    name: 'Simvastatin 20mg',
    dose: '1 tablet',
    schedule: '20.00 — malam hari',
    taken: false,
  },
];

export const heartRateTrend: TrendPoint[] = [
  { label: 'Sen', value: 74 },
  { label: 'Sel', value: 80 },
  { label: 'Rab', value: 76 },
  { label: 'Kam', value: 82 },
  { label: 'Jum', value: 77 },
  { label: 'Sab', value: 79 },
  { label: 'Min', value: 78 },
];

export const spo2Trend: TrendPoint[] = [
  { label: 'Sen', value: 97 },
  { label: 'Sel', value: 98 },
  { label: 'Rab', value: 96 },
  { label: 'Kam', value: 98 },
  { label: 'Jum', value: 97 },
  { label: 'Sab', value: 99 },
  { label: 'Min', value: 98 },
];

export const stepsTrend: TrendPoint[] = [
  { label: 'Sen', value: 4200 },
  { label: 'Sel', value: 5100 },
  { label: 'Rab', value: 3800 },
  { label: 'Kam', value: 4600 },
  { label: 'Jum', value: 5200 },
  { label: 'Sab', value: 3300 },
  { label: 'Min', value: 4700 },
];

export const emergencyContacts = [
  { id: 'c1', name: 'Rafi (Anak)', relation: 'Keluarga', phone: '+62 812-3456-7890' },
  { id: 'c2', name: 'Klinik Sehat', relation: 'Puskesmas', phone: '(0274) 512-345' },
  { id: 'c3', name: 'Ambulans', relation: 'Darurat', phone: '118 / 119' },
];
