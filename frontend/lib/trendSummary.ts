type Channel = 'heart_rate' | 'spo2' | 'body_temperature';
type Means = Record<Channel, number>;

interface Prediction {
  state: 'ready' | 'uncertain';
  label: 'stable' | 'rising_hr' | 'falling_spo2' | 'rising_temperature';
  stats: { first_10_mean: Means; last_10_mean: Means };
  model_version: string;
  span_seconds: number;
  to: string;
}

type Progress = { simulated: boolean } & (
  | Prediction
  | { state: 'insufficient_data'; count: number; required: number }
  | { state: 'stale' | 'irregular_sampling' | 'missing_values' }
);

const channels: Record<Exclude<Prediction['label'], 'stable'>, [Channel, string, string]> = {
  rising_hr: ['heart_rate', 'Detak jantung meningkat', 'bpm'],
  falling_spo2: ['spo2', 'SpO₂ menurun', '%'],
  rising_temperature: ['body_temperature', 'Suhu meningkat', '°C'],
};

export function trendSummary(result: Progress) {
  const status = { badge: 'Status pembacaan', simulated: result.simulated, observedAt: '' };
  switch (result.state) {
    case 'insufficient_data':
      return { ...status, text: `Mengumpulkan data: ${result.count} dari ${result.required} pembacaan.` };
    case 'stale':
      return { ...status, text: 'Pembacaan sudah kedaluwarsa. Menunggu data terbaru.' };
    case 'missing_values':
    case 'irregular_sampling':
      return { ...status, text: 'Data belum lengkap atau interval tidak teratur. Periksa aliran sensor.' };
    case 'uncertain':
    case 'ready': {
      const model = { ...status, badge: `JagSi · ${result.model_version}`, observedAt: result.to };
      if (result.state === 'uncertain') return { ...model, text: 'Model belum dapat menentukan pola.' };
      const window = `Dalam ${Math.round(result.span_seconds)} detik terakhir`;
      if (result.label === 'stable') return { ...model, text: `${window}, pola pembacaan relatif stabil.` };
      const [channel, description, unit] = channels[result.label];
      const first = result.stats.first_10_mean[channel];
      const last = result.stats.last_10_mean[channel];
      return { ...model, text: `${description}. ${window}, rata-rata 10 pembacaan awal adalah ${first} ${unit} dan 10 pembacaan terakhir ${last} ${unit}. Periksa kembali pembacaan.` };
    }
  }
}

export type { Progress };
