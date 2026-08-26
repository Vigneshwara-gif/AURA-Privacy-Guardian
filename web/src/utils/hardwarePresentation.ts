export interface HardwarePresentation {
  primaryTitle: 'IN USE' | 'NOT IN USE' | 'HARDWARE MUTED' | 'DEVICE UNAVAILABLE' | 'PERMISSION LIMITED' | 'STATUS UNAVAILABLE';
  badgeText: string;
  severity: 'HIGH' | 'LOW' | 'MEDIUM' | 'INFO';
  description: string;
}

export const getHardwarePresentation = (
  deviceType: 'camera' | 'microphone',
  status?: string
): HardwarePresentation => {
  const isCam = deviceType === 'camera';
  const name = isCam ? 'camera' : 'microphone';

  switch (status) {
    case 'ACTIVE':
      return {
        primaryTitle: 'IN USE',
        badgeText: 'IN USE (ACTIVE CAPTURE DETECTED)',
        severity: 'HIGH',
        description: `Active ${name} capture session detected.`,
      };
    case 'INACTIVE':
      return {
        primaryTitle: 'NOT IN USE',
        badgeText: 'NOT IN USE (DEVICE IDLE)',
        severity: 'LOW',
        description: `No active ${name} capture session detected.`,
      };
    case 'MUTED':
      return {
        primaryTitle: 'HARDWARE MUTED',
        badgeText: 'HARDWARE MUTED',
        severity: 'LOW',
        description: `The ${name} device is currently hardware-muted.`,
      };
    case 'UNAVAILABLE':
      return {
        primaryTitle: 'DEVICE UNAVAILABLE',
        badgeText: 'DEVICE UNAVAILABLE',
        severity: 'MEDIUM',
        description: `Windows did not report an available ${name} device.`,
      };
    case 'PERMISSION_LIMITED':
      return {
        primaryTitle: 'PERMISSION LIMITED',
        badgeText: 'PERMISSION LIMITED',
        severity: 'MEDIUM',
        description: `Access to ${name} descriptor was restricted by OS permission policy.`,
      };
    case 'NOT_PROBED':
    case 'UNKNOWN':
    default:
      return {
        primaryTitle: 'STATUS UNAVAILABLE',
        badgeText: 'STATUS UNAVAILABLE (DESCRIPTOR MONITORING ONLY)',
        severity: 'INFO',
        description: `Descriptor monitoring only — current ${name} usage could not be determined.`,
      };
  }
};
