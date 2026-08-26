export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  badge?: string | number;
}

export interface SegmentedControlProps<T extends string> {
  options: Array<SegmentOption<T>>;
  value: T;
  onChange: (value: T) => void;
  size?: 'sm' | 'md';
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  size = 'md',
}: SegmentedControlProps<T>) {
  const isSm = size === 'sm';

  return (
    <div
      role="tablist"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '3px',
        backgroundColor: 'var(--bg-surface-inset)',
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--border-subtle)',
        gap: '2px',
      }}
    >
      {options.map((opt) => {
        const isSelected = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={isSelected}
            onClick={() => onChange(opt.value)}
            style={{
              padding: isSm ? '4px 10px' : '6px 14px',
              fontSize: isSm ? '0.74rem' : '0.8rem',
              fontWeight: isSelected ? 700 : 500,
              color: isSelected ? '#ffffff' : 'var(--text-secondary)',
              backgroundColor: isSelected ? 'var(--accent-primary)' : 'transparent',
              border: isSelected ? '1px solid var(--accent-primary-hover)' : '1px solid transparent',
              borderRadius: 'var(--radius-sm)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all var(--transition-fast)',
              outline: 'none',
              boxShadow: isSelected ? '0 1px 4px rgba(0, 0, 0, 0.3)' : 'none',
            }}
          >
            <span>{opt.label}</span>
            {opt.badge !== undefined && (
              <span
                style={{
                  fontSize: '0.68rem',
                  padding: '1px 5px',
                  borderRadius: 'var(--radius-full)',
                  backgroundColor: isSelected ? 'rgba(255, 255, 255, 0.25)' : 'var(--bg-surface-subtle)',
                  color: isSelected ? '#ffffff' : 'var(--text-muted)',
                }}
              >
                {opt.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
