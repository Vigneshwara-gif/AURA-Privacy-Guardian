import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  disabled,
  style,
  ...props
}) => {
  const getVariantStyles = (): React.CSSProperties => {
    switch (variant) {
      case 'secondary':
        return {
          backgroundColor: 'var(--bg-surface-elevated)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-default)',
        };
      case 'outline':
        return {
          backgroundColor: 'transparent',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-default)',
        };
      case 'danger':
        return {
          backgroundColor: 'var(--severity-critical)',
          color: '#ffffff',
          border: 'none',
        };
      case 'ghost':
        return {
          backgroundColor: 'transparent',
          color: 'var(--text-secondary)',
          border: 'none',
        };
      case 'primary':
      default:
        return {
          backgroundColor: 'var(--accent-primary)',
          color: '#ffffff',
          fontWeight: 600,
          border: 'none',
        };
    }
  };

  const getSizeStyles = (): React.CSSProperties => {
    switch (size) {
      case 'sm':
        return { padding: '4px 10px', fontSize: '0.8125rem' };
      case 'lg':
        return { padding: '10px 20px', fontSize: '1rem' };
      case 'md':
      default:
        return { padding: '7px 14px', fontSize: '0.875rem' };
    }
  };

  return (
    <button
      disabled={disabled || loading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '6px',
        fontWeight: 500,
        borderRadius: 'var(--radius-md)',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.6 : 1,
        transition: 'var(--transition-fast)',
        fontFamily: 'inherit',
        ...getVariantStyles(),
        ...getSizeStyles(),
        ...style,
      }}
      {...props}
    >
      {loading ? <span style={{ display: 'inline-block', animation: 'spin 1s linear infinite' }}>⏳</span> : icon}
      {children}
    </button>
  );
};
