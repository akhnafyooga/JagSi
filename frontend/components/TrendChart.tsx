import type { TrendPoint } from '@/lib/types';

interface TrendChartProps {
  data: TrendPoint[];
  unit?: string;
  color?: string;
  height?: number;
  bar?: boolean;
}

export function TrendChart({
  data,
  unit = '',
  color = '#45608a',
  height = 120,
  bar = false,
}: TrendChartProps) {
  const width = 320;
  const pad = 8;
  const min = Math.min(...data.map((d) => d.value));
  const max = Math.max(...data.map((d) => d.value));
  const range = max - min || 1;

  const x = (i: number) => pad + (i * (width - pad * 2)) / (data.length - 1);
  const y = (v: number) => height - pad - ((v - min) / range) * (height - pad * 2);

  if (bar) {
    const barWidth = (width - pad * 2) / data.length - 6;
    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Bar chart">
        {data.map((d, i) => {
          const h = height - pad - y(d.value);
          return (
            <rect
              key={i}
              x={x(i) - barWidth / 2}
              y={height - pad - h}
              width={barWidth}
              height={h}
              rx={3}
              fill={color}
              opacity={0.85}
            />
          );
        })}
        {data.map((d, i) => (
          <text key={i} x={x(i)} y={height - 2} textAnchor="middle" className="fill-on-surface-variant" fontSize={9}>
            {d.label}
          </text>
        ))}
      </svg>
    );
  }

  const line = data.map((d, i) => `${x(i)},${y(d.value)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Line chart">
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polygon
        points={`${x(0)},${height - pad} ${line} ${x(data.length - 1)},${height - pad}`}
        fill={color}
        opacity={0.12}
      />
      {data.map((d, i) => (
        <circle key={i} cx={x(i)} cy={y(d.value)} r={2.5} fill={color} />
      ))}
      {data.map((d, i) => (
        <text key={i} x={x(i)} y={height - 2} textAnchor="middle" className="fill-on-surface-variant" fontSize={9}>
          {d.label}
        </text>
      ))}
    </svg>
  );
}
