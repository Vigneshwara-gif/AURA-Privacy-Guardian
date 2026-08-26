import React from 'react';

interface AuraLogoProps {
  size?: number;
  variant?: 'icon' | 'full' | 'monochrome' | 'white';
  showWordmark?: boolean;
  glow?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * Distinctive Geometric SVG Shield for AURA Privacy Guardian.
 * Faceted outer shield geometry with letter-A apex and internal sentinel core.
 */
export const AuraLogo: React.FC<AuraLogoProps> = ({
  size = 28,
  variant = 'icon',
  showWordmark = false,
  glow = false,
  className = '',
  style = {},
}) => {
  const primaryColor = variant === 'monochrome' ? 'currentColor' : variant === 'white' ? '#FFFFFF' : '#1677FF';
  const secondaryColor = variant === 'monochrome' ? 'currentColor' : variant === 'white' ? 'rgba(255,255,255,0.85)' : '#38A8FF';
  const deepColor = variant === 'monochrome' ? 'currentColor' : variant === 'white' ? 'rgba(255,255,255,0.4)' : '#0B3A78';

  const gradId = React.useId ? React.useId() : 'aura-shield-grad';

  return (
    <div
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: size > 24 ? '10px' : '8px',
        userSelect: 'none',
        ...style,
      }}
    >
      <svg
        width={size}
        height={Math.round(size * 1.18)}
        viewBox="0 0 32 38"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{
          filter: glow ? 'drop-shadow(0 0 10px rgba(22, 119, 255, 0.5))' : undefined,
          flexShrink: 0,
        }}
      >
        <defs>
          <linearGradient id={`${gradId}-shield`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={secondaryColor} />
            <stop offset="55%" stopColor={primaryColor} />
            <stop offset="100%" stopColor={deepColor} />
          </linearGradient>
          <linearGradient id={`${gradId}-core`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.95" />
            <stop offset="100%" stopColor={secondaryColor} stopOpacity="0.7" />
          </linearGradient>
        </defs>

        {/* Outer Shield Frame */}
        <path
          d="M16 2 L30 7.5 L30 19 C30 28.5 16 36 16 36 C16 36 2 28.5 2 19 L2 7.5 Z"
          fill={`url(#${gradId}-shield)`}
          stroke={secondaryColor}
          strokeWidth="1.2"
          strokeLinejoin="round"
        />

        {/* Internal Facet Left Highlight */}
        <path
          d="M16 4.5 L4.5 9 L4.5 18.5 C4.5 26.2 16 33.2 16 33.2 Z"
          fill="rgba(255, 255, 255, 0.08)"
        />

        {/* Geometric Letter-A Apex Core */}
        <path
          d="M16 9.5 L22.5 19.5 H19.2 L16 14.5 L12.8 19.5 H9.5 Z"
          fill={`url(#${gradId}-core)`}
        />

        {/* Central Sentinel Diamond Crossbar */}
        <path
          d="M16 17.5 L19.5 23 L16 27.5 L12.5 23 Z"
          fill="#FFFFFF"
          fillOpacity="0.95"
        />
      </svg>

      {showWordmark && (
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: size > 24 ? '1.15rem' : '1.0rem',
                fontWeight: 800,
                letterSpacing: '0.08em',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-sans)',
              }}
            >
              AURA
            </span>
            <span
              style={{
                fontSize: '0.62rem',
                fontWeight: 700,
                letterSpacing: '0.06em',
                padding: '2px 5px',
                borderRadius: 'var(--radius-xs)',
                backgroundColor: 'var(--accent-primary-subtle)',
                color: 'var(--accent-primary-hover)',
                textTransform: 'uppercase',
              }}
            >
              GUARDIAN
            </span>
          </div>
          <span
            style={{
              fontSize: '0.68rem',
              fontWeight: 500,
              letterSpacing: '0.02em',
              color: 'var(--text-muted)',
              marginTop: '2px',
            }}
          >
            Autonomous Privacy & Security
          </span>
        </div>
      )}
    </div>
  );
};
