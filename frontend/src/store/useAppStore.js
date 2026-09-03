import { create } from 'zustand';
import axiosClient from '../api/axiosClient';

const useAppStore = create((set) => ({
  provincias: [],
  empleadores: [],
  socios: [],
  operadores: [],
  tasasYComisiones: [],
  relaciones: [],
  comercializadores: [],
  bancos: [],
  cuentas: [],
  conceptos: [],
  clasificaciones: [],
  
  isLoadingAuxiliares: false,
  error: null,

  editingCompra: null,
  setEditingCompra: (compra) => set({ editingCompra: compra }),

  fetchAuxiliares: async () => {
    set({ isLoadingAuxiliares: true, error: null });
    try {
      const [provRes, empRes, sociosRes, operadoresRes, tasasRes, relacionesRes, comerRes, bancosRes, cuentasRes, conceptosRes, subRes] = await Promise.all([
        axiosClient.get('/api/v1/auxiliares/provincias').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/empleadores').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/socios').catch(() => ({ data: [] })),
        axiosClient.get('/api/cheques/operadores').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/tasas_y_comisiones').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/relaciones').catch(() => ({ data: [] })),
        axiosClient.get('/api/v1/auxiliares/comercializadores').catch(() => ({ data: [] })),
        axiosClient.get('/api/finanzas/bancos').catch(() => ({ data: [] })),
        axiosClient.get('/api/finanzas/cuentas').catch(() => ({ data: [] })),
        axiosClient.get('/api/finanzas/conceptos').catch(() => ({ data: [] })),
        axiosClient.get('/api/finanzas/clasificaciones').catch(() => ({ data: [] }))
      ]);

      set({
        provincias: provRes.data,
        empleadores: empRes.data,
        socios: sociosRes.data,
        operadores: operadoresRes.data,
        tasasYComisiones: tasasRes.data,
        relaciones: relacionesRes.data,
        comercializadores: comerRes.data,
        bancos: bancosRes.data,
        cuentas: cuentasRes.data,
        conceptos: conceptosRes.data,
        clasificaciones: subRes.data,
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
  },

  // State to hold system modules activation status
  systemModules: {
    creditos: true,
    cheques: true,
    inversores: true,
    finanzas: true,
  },
  isLoadingModules: false,

  fetchSystemModules: async () => {
    try {
      const res = await axiosClient.get('/api/v1/system/modules');
      if (res.data && res.data.modulos) {
        set({ systemModules: res.data.modulos });
      }
    } catch (error) {
      console.error("Error fetching system modules:", error);
    }
  },

  updateSystemModules: async (newModules) => {
    set({ isLoadingModules: true });
    try {
      const res = await axiosClient.put('/api/v1/system/modules', { modulos: newModules });
      if (res.data && res.data.modulos) {
        set({ systemModules: res.data.modulos, isLoadingModules: false });
        return { success: true, modulos: res.data.modulos };
      }
      set({ isLoadingModules: false });
      return { success: true };
    } catch (error) {
      set({ isLoadingModules: false });
      throw error;
    }
  }
}));

export default useAppStore;
