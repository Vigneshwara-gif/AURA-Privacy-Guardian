import React from 'react';

export interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  label?: string;
  ariaLabel?: string;
  size?: 'sm' | 'md';
}

export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  checked,
  onChange,
  disabled = false,
  id,
  label,
  ariaLabel,
  size = 'md',
}) => {
  const isSm = size === 'sm';
  const width = isSm ? 36 : 44;
  const height = isSm ? 20 : 24;
  const thumbSize = isSm ? 14 : 18;
  const thumbOffset = 3;
  const translateDist = width - thumbSize - thumbOffset * 2;

  return (
    <label
      htmlFor={id}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '10px',
        cursor: disabled ? 'not-allowed' : 'pointer',
        userSelect: 'none',
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <div
        role="switch"
        aria-checked={checked}
        aria-label={ariaLabel || label}
        tabIndex={disabled ? -1 : 0}
        onClick={() => {
          if (!disabled) onChange(!checked);
        }}
        onKeyDown={(e) => {
          if (!disabled && (e.key === ' ' || e.key === 'Enter')) {
            e.preventDefault();
            onChange(!checked);
          }
        }}
        style={{
          width: `${width}px`,
          height: `${height}px`,
          borderRadius: `${height}px`,
          backgroundColor: checked ? 'var(--accent-primary)' : 'var(--bg-surface-subtle)',
          border: `1px solid ${checked ? 'var(--accent-primary-hover)' : 'var(--border-default)'}`,
          position: 'relative',
          transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
          boxShadow: checked ? '0 0 12px rgba(22, 119, 255, 0.35)' : 'none',
          outline: 'none',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: `${thumbSize}px`,
            height: `${thumbSize}px`,
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            position: 'absolute',
            top: `${thumbOffset - 1}px`,
            left: `${thumbOffset}px`,
            transform: checked ? `translateX(${translateDist}px)` : 'translateX(0)',
            transition: 'transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.4)',
          }}
        />
      </div>
      {label && (
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          {label}
        </span>
      )}
    </label>
  );
};
