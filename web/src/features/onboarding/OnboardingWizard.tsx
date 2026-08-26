import React, { useState } from 'react';
import { setOnboardingCompleted } from './onboardingState';
import { CapabilityCheckStep } from './CapabilityCheckStep';
import { DeviceSetupStep } from './DeviceSetupStep';
import { InitialScanStep } from './InitialScanStep';
import { PrivacyPromiseStep } from './PrivacyPromiseStep';
import { ProtectionPreferencesStep } from './ProtectionPreferencesStep';
import { WelcomeStep } from './WelcomeStep';

interface OnboardingWizardProps {
  onFinish: () => void;
}

export const OnboardingWizard: React.FC<OnboardingWizardProps> = ({ onFinish }) => {
  const [step, setStep] = useState(1);

  const steps = [
    { number: 1, title: 'Welcome' },
    { number: 2, title: 'Privacy Promise' },
    { number: 3, title: 'Device Setup' },
    { number: 4, title: 'Capability Check' },
    { number: 5, title: 'Preferences' },
    { number: 6, title: 'Protection Scan' },
  ];

  const handleComplete = () => {
    setOnboardingCompleted(true);
    onFinish();
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: 'var(--bg-app)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-6)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '780px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-xl)',
          padding: 'var(--space-6)',
          boxShadow: 'var(--shadow-modal)',
        }}
      >
        {/* Step Progress Bar */}
        {step > 1 && step < 6 && (
          <div style={{ marginBottom: 'var(--space-6)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                Step {step} of 6: {steps[step - 1].title}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--accent-primary-hover)', fontFamily: 'var(--font-mono)' }}>
                {Math.round(((step - 1) / 5) * 100)}%
              </span>
            </div>
            <div style={{ height: '4px', backgroundColor: 'var(--bg-surface-subtle)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${((step - 1) / 5) * 100}%`,
                  backgroundColor: 'var(--accent-primary)',
                  transition: 'width var(--transition-normal)',
                }}
              />
            </div>
          </div>
        )}

        {/* Wizard Steps */}
        {step === 1 && <WelcomeStep onNext={() => setStep(2)} />}
        {step === 2 && <PrivacyPromiseStep onNext={() => setStep(3)} onBack={() => setStep(1)} />}
        {step === 3 && <DeviceSetupStep onNext={() => setStep(4)} onBack={() => setStep(2)} />}
        {step === 4 && <CapabilityCheckStep onNext={() => setStep(5)} onBack={() => setStep(3)} />}
        {step === 5 && <ProtectionPreferencesStep onNext={() => setStep(6)} onBack={() => setStep(4)} />}
        {step === 6 && <InitialScanStep onComplete={handleComplete} />}
      </div>
    </div>
  );
};
