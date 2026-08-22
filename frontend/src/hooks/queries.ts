import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';

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

export const useCreateAnimal = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: any) => api('/animals', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['animals'] }),
  });
};

export const useAnimalDossier = (animalId?: number) =>
  useQuery({
    queryKey: ['animal', animalId],
    queryFn: () => api(`/animals/${animalId}`),
    enabled: animalId != null,
    refetchInterval: 60_000,
  });

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
export const useAlerts = () =>
  useQuery({ queryKey: ['alerts'], queryFn: () => api<any[]>('/alerts'), refetchInterval: 60_000 });

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