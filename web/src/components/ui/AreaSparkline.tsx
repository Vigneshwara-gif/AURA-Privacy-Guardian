import React from 'react';

export interface AreaSparklineProps {
  data: number[];
  height?: number;
  color?: string;
  fill?: boolean;
}

export const AreaSparkline: React.FC<AreaSparklineProps> = ({
  data,
  height = 40,
  color = 'var(--accent-primary)',
  fill = true,
}) => {
  if (!data || data.length < 2) {
    return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>—</div>;
  }

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min === 0 ? 1 : max - min;
  const width = 100;

  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * width;
    const y = height - ((val - min) / range) * (height - 6) - 3;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  const pathD = `M ${points.join(' L ')}`;
  const areaD = `${pathD} L ${width},${height} L 0,${height} Z`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height, overflow: 'visible' }}>
      {fill && <path d={areaD} fill={color} fillOpacity={0.15} />}
      <path d={pathD} fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
};
