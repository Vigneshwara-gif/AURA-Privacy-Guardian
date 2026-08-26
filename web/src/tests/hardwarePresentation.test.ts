import { describe, expect, it } from 'vitest';
import { getHardwarePresentation } from '../utils/hardwarePresentation';

describe('Privacy Sentinel Hardware Presentation Mapping', () => {
  it('maps ACTIVE capture state correctly', () => {
    const cam = getHardwarePresentation('camera', 'ACTIVE');
    expect(cam.primaryTitle).toBe('IN USE');
    expect(cam.badgeText).toBe('IN USE (ACTIVE CAPTURE DETECTED)');
    expect(cam.severity).toBe('HIGH');
    expect(cam.description).toBe('Active camera capture session detected.');

    const mic = getHardwarePresentation('microphone', 'ACTIVE');
    expect(mic.primaryTitle).toBe('IN USE');
    expect(mic.badgeText).toBe('IN USE (ACTIVE CAPTURE DETECTED)');
    expect(mic.severity).toBe('HIGH');
    expect(mic.description).toBe('Active microphone capture session detected.');
  });

  it('maps INACTIVE idle state correctly without fabricating active state', () => {
    const cam = getHardwarePresentation('camera', 'INACTIVE');
    expect(cam.primaryTitle).toBe('NOT IN USE');
    expect(cam.badgeText).toBe('NOT IN USE (DEVICE IDLE)');
    expect(cam.severity).toBe('LOW');
    expect(cam.description).toBe('No active camera capture session detected.');
  });

  it('maps MUTED state correctly', () => {
    const cam = getHardwarePresentation('camera', 'MUTED');
    expect(cam.primaryTitle).toBe('HARDWARE MUTED');
    expect(cam.badgeText).toBe('HARDWARE MUTED');
    expect(cam.severity).toBe('LOW');
    expect(cam.description).toBe('The camera device is currently hardware-muted.');
  });

  it('maps UNAVAILABLE state correctly', () => {
    const mic = getHardwarePresentation('microphone', 'UNAVAILABLE');
    expect(mic.primaryTitle).toBe('DEVICE UNAVAILABLE');
    expect(mic.badgeText).toBe('DEVICE UNAVAILABLE');
    expect(mic.severity).toBe('MEDIUM');
    expect(mic.description).toBe('Windows did not report an available microphone device.');
  });

  it('maps PERMISSION_LIMITED state correctly', () => {
    const cam = getHardwarePresentation('camera', 'PERMISSION_LIMITED');
    expect(cam.primaryTitle).toBe('PERMISSION LIMITED');
    expect(cam.badgeText).toBe('PERMISSION LIMITED');
    expect(cam.severity).toBe('MEDIUM');
  });

  it('CRITICAL: NEVER exposes NOT_PROBED or UNKNOWN as primary title, maps to STATUS UNAVAILABLE', () => {
    const unprobedCam = getHardwarePresentation('camera', 'NOT_PROBED');
    expect(unprobedCam.primaryTitle).toBe('STATUS UNAVAILABLE');
    expect(unprobedCam.badgeText).toBe('STATUS UNAVAILABLE (DESCRIPTOR MONITORING ONLY)');
    expect(unprobedCam.severity).toBe('INFO');
    expect(unprobedCam.description).toBe('Descriptor monitoring only — current camera usage could not be determined.');

    const unknownMic = getHardwarePresentation('microphone', 'UNKNOWN');
    expect(unknownMic.primaryTitle).toBe('STATUS UNAVAILABLE');
    expect(unknownMic.badgeText).toBe('STATUS UNAVAILABLE (DESCRIPTOR MONITORING ONLY)');
    expect(unknownMic.severity).toBe('INFO');
    expect(unknownMic.description).toBe('Descriptor monitoring only — current microphone usage could not be determined.');

    const undefinedCam = getHardwarePresentation('camera', undefined);
    expect(undefinedCam.primaryTitle).toBe('STATUS UNAVAILABLE');
  });
});
