import { create } from 'zustand';
import axiosClient from '../api/axiosClient';

const useAppStore = create((set) => ({
  provincias: [],
  empleadores: [],
  socios: [],
  tasasYComisiones: [],
  relaciones: [],
  comercializadores: [],
  
  isLoadingAuxiliares: false,
  error: null,

  editingCompra: null,
  setEditingCompra: (compra) => set({ editingCompra: compra }),

  fetchAuxiliares: async () => {
    set({ isLoadingAuxiliares: true, error: null });
    try {
      const [provRes, empRes, sociosRes, tasasRes, relacionesRes, comerRes] = await Promise.all([
        axiosClient.get('/api/v1/auxiliares/provincias').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/empleadores').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/socios').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/tasas_y_comisiones').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/relaciones').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/comercializadores').catch(() => ({ data: [] }))
      ]);

      set({
        provincias: provRes.data,
        empleadores: empRes.data,
        socios: sociosRes.data,
        tasasYComisiones: tasasRes.data,
        relaciones: relacionesRes.data,
        comercializadores: comerRes.data,
        isLoadingAuxiliares: false,
      });
    } catch (error) {
      set({ error: error.message, isLoadingAuxiliares: false });
    }
  },

  // State to hold global API connection status
  apiStatus: 'Conectando...',
  checkApiStatus: async () => {
    try {
      await axiosClient.get('/'); // Simple ping
      set({ apiStatus: 'Conectado (API Local)' });
    } catch (e) {
      set({ apiStatus: 'Desconectado' });
    }
  }
}));

export default useAppStore;
