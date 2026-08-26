import React, { createContext, useContext, useEffect, useRef, useState } from 'react';
import type { AgentStatus, SensorHealthItem } from '../contracts/agent';
import type { RiskResponse, SecurityEventResponse, TelemetryResponse } from '../contracts/api';
import type { LiveStreamMessage } from '../contracts/stream';
import { ApiClient } from '../services/apiClient';
import { StreamClient, type StreamConnectionState } from '../services/streamClient';
import { useAuth } from './AuthContext';
import { useNavigation } from './NavigationContext';
import { useToast } from './ToastContext';
import { NotificationManager } from '../services/notificationManager';

interface StreamContextType {
  connectionState: StreamConnectionState;
  telemetryHistory: TelemetryResponse[];
  latestTelemetry: TelemetryResponse | null;
  currentRisk: RiskResponse | null;
  agentStatus: AgentStatus | null;
  sensors: SensorHealthItem[];
  recentEvents: SecurityEventResponse[];
  isScanning: boolean;
  triggerScan: (probeCam?: boolean, probeMic?: boolean, isDemo?: boolean) => Promise<void>;
  refreshState: () => Promise<void>;
}

const StreamContext = createContext<StreamContextType | undefined>(undefined);

export const StreamProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { status: authStatus, token } = useAuth();
  const { addToast } = useToast();
  const { navigateToEvent } = useNavigation();

  const [connectionState, setConnectionState] = useState<StreamConnectionState>('DISCONNECTED');
  const [telemetryHistory, setTelemetryHistory] = useState<TelemetryResponse[]>([]);
  const [latestTelemetry, setLatestTelemetry] = useState<TelemetryResponse | null>(null);
  const [currentRisk, setCurrentRisk] = useState<RiskResponse | null>(null);
  const [agentStatus, setAgentStatus] = useState<AgentStatus | null>(null);
  const [sensors, setSensors] = useState<SensorHealthItem[]>([]);
  const [recentEvents, setRecentEvents] = useState<SecurityEventResponse[]>([]);
  const [isScanning, setIsScanning] = useState<boolean>(false);

  const streamClientRef = useRef<StreamClient>(StreamClient.getInstance());

  const refreshState = async () => {
    try {
      const [statusRes, riskRes, sensorsRes, eventsRes, liveTel] = await Promise.allSettled([
        ApiClient.getStatus(),
        ApiClient.getCurrentRisk(),
        ApiClient.getSensors(),
        ApiClient.getEvents(20),
        ApiClient.getLiveTelemetry(),
      ]);

      if (statusRes.status === 'fulfilled') setAgentStatus(statusRes.value);
      if (riskRes.status === 'fulfilled') setCurrentRisk(riskRes.value);
      if (sensorsRes.status === 'fulfilled') setSensors(sensorsRes.value);
      if (eventsRes.status === 'fulfilled') setRecentEvents(eventsRes.value.items);
      if (liveTel.status === 'fulfilled') {
        setLatestTelemetry(liveTel.value);
        setTelemetryHistory((prev) => [...prev.slice(-59), liveTel.value]);
      }
    } catch {
      // Backend not yet ready
    }
  };

  useEffect(() => {
    refreshState();
  }, [authStatus]);

  useEffect(() => {
    const client = streamClientRef.current;
    const unsubState = client.onStateChange((s) => setConnectionState(s));

    const unsubMsg = client.onMessage((msg: LiveStreamMessage) => {
      switch (msg.type) {
        case 'telemetry_tick':
          setLatestTelemetry(msg.payload);
          setTelemetryHistory((prev) => {
            const next = [...prev, msg.payload];
            return next.length > 60 ? next.slice(next.length - 60) : next;
          });
          break;

        case 'security_event':
          setRecentEvents((prev) => [msg.payload, ...prev.slice(0, 99)]);
          const decision = NotificationManager.evaluateEvent(msg.payload);
          if (decision.type === 'NEW_INCIDENT' || decision.type === 'ESCALATION') {
            const title =
              decision.type === 'ESCALATION'
                ? `Escalation [${decision.previousSeverity} → ${decision.severity}]: ${msg.payload.event_type}`
                : `Security Alert: ${msg.payload.event_type}`;
            addToast({
              title,
              message: NotificationManager.sanitizeSummary(msg.payload.summary),
              severity: decision.severity,
              riskScore: msg.payload.risk_score,
              eventId: msg.payload.event_id,
              incidentId: msg.payload.incident_id,
              onInvestigate: (id) => navigateToEvent(id),
            });
          }
          break;

        case 'sensor_health_change':
          setSensors(msg.payload);
          break;

        case 'agent_status_change':
          setAgentStatus(msg.payload);
          break;

        case 'scan_progress':
          if (msg.payload.state === 'RUNNING') {
            setIsScanning(true);
          } else {
            setIsScanning(false);
            refreshState();
          }
          break;
      }
    });

    client.connect();

    return () => {
      unsubState();
      unsubMsg();
      client.disconnect();
    };
  }, [token]);

  const triggerScan = async (probeCam = false, probeMic = false, isDemo = false) => {
    if (isScanning) return;
    setIsScanning(true);
    try {
      await ApiClient.triggerScan({ probe_camera: probeCam, probe_microphone: probeMic, is_demo: isDemo });
      await refreshState();
      addToast({
        title: 'Scan Completed',
        message: 'Security baseline assessment complete.',
        severity: 'INFO',
      });
    } catch (err: unknown) {
      addToast({
        title: 'Scan Failed',
        message: err instanceof Error ? err.message : 'Could not trigger scan',
        severity: 'HIGH',
      });
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <StreamContext.Provider
      value={{
        connectionState,
        telemetryHistory,
        latestTelemetry,
        currentRisk,
        agentStatus,
        sensors,
        recentEvents,
        isScanning,
        triggerScan,
        refreshState,
      }}
    >
      {children}
    </StreamContext.Provider>
  );
};

export const useStream = (): StreamContextType => {
  const context = useContext(StreamContext);
  if (!context) throw new Error('useStream must be used within StreamProvider');
  return context;
};
