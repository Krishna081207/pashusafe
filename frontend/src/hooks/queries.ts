import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { Geofence, InstallVisit, LiveTracking, TrackPoint } from '../types/models';

// ---------- auth ----------
export interface Me {
  id: number;
  full_name: string;
  email: string;
  role: 'farmer' | 'vet' | 'regulator' | 'admin';
  farm_id: number | null;
}

export const useMe = () =>
  useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/auth/me'), retry: false });

// ---------- farms / animals / drugs ----------
export const useFarm = (farmId?: number | null) =>
  useQuery({
    queryKey: ['farm', farmId],
    queryFn: () => api(`/farms/${farmId}`),
    enabled: farmId != null,
  });

export const useAnimals = () =>
  useQuery({ queryKey: ['animals'], queryFn: () => api<any[]>('/animals') });

export const useAnimalDossier = (animalId?: number) =>
  useQuery({
    queryKey: ['animal', animalId],
    queryFn: () => api(`/animals/${animalId}`),
    enabled: animalId != null,
    refetchInterval: 60_000,
  });

export const useCreateAnimal = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      tag_id: string;
      species: string;
      breed?: string | null;
      sex?: string;
      production_status?: string;
      weight_kg?: number | null;
      birth_date?: string | null;
    }) => api<{ id: number; tag_id: string; qr_code: string }>('/animals', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['animals'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      qc.invalidateQueries({ queryKey: ['tracking'] });
    },
  });
};

export const useDrugs = () =>
  useQuery({ queryKey: ['drugs'], queryFn: () => api<any[]>('/drugs'), staleTime: 5 * 60_000 });

// ---------- MRL / compliance ----------
export const useFarmStatus = (farmId?: number | null) =>
  useQuery({
    queryKey: ['mrl', 'farm', farmId],
    queryFn: () => api(`/mrl/status/farm/${farmId}`),
    enabled: farmId != null,
    refetchInterval: 60_000,
  });

export const useStatusOverview = () =>
  useQuery({
    queryKey: ['mrl', 'overview'],
    queryFn: () => api<any[]>('/mrl/status/overview'),
    refetchInterval: 60_000,
  });

export const useFarmComplianceTable = () =>
  useQuery({
    queryKey: ['analytics', 'by-farm'],
    queryFn: () => api<any[]>('/analytics/compliance/by-farm'),
  });

export const useModelInfo = () =>
  useQuery({
    queryKey: ['ml', 'model-info'],
    queryFn: () => api<any>('/ml/model/info'),
  });

export const useViolations = () =>
  useQuery({ queryKey: ['mrl', 'violations'], queryFn: () => api<any[]>('/mrl/violations') });

// ---------- alerts ----------
export const useAlerts = (refetchIntervalMs: number = 60_000) =>
  useQuery({
    queryKey: ['alerts'],
    queryFn: () => api<any[]>('/alerts'),
    refetchInterval: refetchIntervalMs,
  });

export const useResolveAlert = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/alerts/${id}/resolve`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
    },
  });
};

// ---------- administrations / sales / prescriptions / tests ----------
export const useAdministrations = () =>
  useQuery({ queryKey: ['administrations'], queryFn: () => api<any[]>('/administrations') });

export const useSales = () =>
  useQuery({ queryKey: ['sales'], queryFn: () => api<any[]>('/sale-events') });

export const usePrescriptions = () =>
  useQuery({ queryKey: ['prescriptions'], queryFn: () => api<any[]>('/prescriptions') });

export const useResidueTests = () =>
  useQuery({ queryKey: ['residue-tests'], queryFn: () => api<any[]>('/residue-tests') });

export const useRecordAdministration = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) =>
      api('/administrations', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mrl'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['administrations'] });
      qc.invalidateQueries({ queryKey: ['animal'] });
    },
  });
};

export const useRecordSale = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) => api('/sale-events', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mrl'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['sales'] });
    },
  });
};

export const useRecordPrescription = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) =>
      api('/prescriptions', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prescriptions'] }),
  });
};

export const useRecordResidueTest = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) =>
      api('/residue-tests', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['residue-tests'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['mrl'] });
    },
  });
};

// ---------- analytics / ledger / iot / ml ----------
export const useDashboard = () =>
  useQuery({ queryKey: ['dashboard'], queryFn: () => api('/analytics/dashboard') });

export const useAmuAnalytics = () =>
  useQuery({ queryKey: ['analytics', 'amu'], queryFn: () => api('/analytics/amu') });

export const useSalesAnalytics = () =>
  useQuery({ queryKey: ['analytics', 'sales'], queryFn: () => api('/analytics/sales') });

export const useLedgerEvents = () =>
  useQuery({ queryKey: ['ledger', 'events'], queryFn: () => api<any[]>('/ledger/events') });

export const useLedgerVerify = () =>
  useQuery({ queryKey: ['ledger', 'verify'], queryFn: () => api('/ledger/verify') });

export const useDemoTamper = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api('/ledger/demo-tamper', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ledger'] }),
  });
};

export const useIotReadings = (animalId?: number, hours: number = 48) =>
  useQuery({
    queryKey: ['iot', animalId, hours],
    queryFn: () => api(`/iot/readings?animal_id=${animalId}&hours=${hours}`),
    enabled: animalId != null,
    refetchInterval: 20_000,
  });

export const useHealthStatus = (animalId?: number) =>
  useQuery({
    queryKey: ['iot', 'status', animalId],
    queryFn: () => api(`/iot/status/${animalId}`),
    enabled: animalId != null,
    refetchInterval: 15_000,
  });

export const useSimulateFever = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (animalId: number) =>
      api(`/iot/simulate-fever/${animalId}`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['iot'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
};

export const useSimulateRecovery = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (animalId: number) =>
      api(`/iot/simulate-recovery/${animalId}`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['iot'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });};

export const useAnimalPrediction = (animalId?: number) =>
  useQuery({
    queryKey: ['ml', 'animal', animalId],
    queryFn: () => api(`/ml/predict/animal/${animalId}`),
    enabled: animalId != null,
  });

export const useFarmWatchlist = (farmId?: number | null) =>
  useQuery({
    queryKey: ['ml', 'farm', farmId],
    queryFn: () => api(`/ml/predict/farm/${farmId}`),
    enabled: farmId != null,
  });

// ---------- assistant ----------
export const useAssistantSuggestions = () =>
  useQuery({
    queryKey: ['assistant', 'suggestions'],
    queryFn: () => api<{ suggestions: string[]; mode: string }>('/assistant/suggestions'),
    staleTime: Infinity,
  });

export const useAssistantChat = () =>
  useMutation({
    mutationFn: (message: string) =>
      api('/assistant/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  });

// ---------- public trace (no auth) ----------
export const usePublicTrace = (qrCode?: string) =>
  useQuery({
    queryKey: ['trace', qrCode],
    queryFn: () => api(`/trace/public/${qrCode}`),
    enabled: qrCode != null,
  });

// ---------- sensor install visits ----------
export const useInstallVisits = () =>
  useQuery({
    queryKey: ['installs'],
    queryFn: () => api<InstallVisit[]>('/installs'),
    refetchInterval: 45_000,
  });

export const useRequestInstallVisit = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { preferred_date: string; preferred_slot: string; notes?: string }) =>
      api('/installs', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['installs'] }),
  });
};

export const useCancelInstallVisit = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      api(`/installs/${id}/cancel${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`, {
        method: 'POST',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['installs'] }),
  });
};

export const useUpdateInstallVisit = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: { id: number; status?: string; scheduled_at?: string; official_name?: string; official_phone?: string; cancel_reason?: string }) =>
      api(`/installs/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['installs'] });
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });
};

// ---------- live tracking / geofence ----------
export const useLiveTracking = () =>
  useQuery({
    queryKey: ['tracking', 'live'],
    queryFn: () => api<LiveTracking>('/tracking/live'),
    refetchInterval: 10_000,
  });

export const useGeofence = () =>
  useQuery({
    queryKey: ['tracking', 'geofence'],
    queryFn: () => api<Geofence>('/tracking/geofence'),
  });

export const useUpdateGeofence = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Geofence) =>
      api('/tracking/geofence', { method: 'PUT', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tracking'] }),
  });
};

export const useTrackingHistory = (animalId?: number, minutes: number = 120) =>
  useQuery({
    queryKey: ['tracking', 'history', animalId, minutes],
    queryFn: () => api<TrackPoint[]>(`/tracking/history?animal_id=${animalId}&minutes=${minutes}`),
    enabled: animalId != null,
    refetchInterval: 20_000,
  });
