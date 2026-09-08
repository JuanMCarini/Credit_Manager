import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X, Eye, Edit, Trash2, PlusCircle, MinusCircle } from 'lucide-react';
import ExportExcelButton from '../components/ExportExcelButton';
import ExcelListFilter from '../components/ExcelListFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';
import ExcelDateFilter from '../components/ExcelDateFilter';
import { useAuthStore } from '../store/useAuthStore';
import useAppStore from '../store/useAppStore';

const SeriesPage = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { comisionesDeuda } = useAppStore();
  const isAuditor = user?.rol === 'Auditor / Solo Lectura';
  const [showAddModal, setShowAddModal] = useState(false);
  const [editSerieData, setEditSerieData] = useState(null);
  const [fechaCorte, setFechaCorte] = useState(new Date().toISOString().split('T')[0]);
  const [tableFilters, setTableFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: 'id', direction: 'desc' });

  const handleTableFilterChange = (key, value) => {
    setTableFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const [showRenovacionModal, setShowRenovacionModal] = useState(false);
  const [selectedSerieVieja, setSelectedSerieVieja] = useState(null);
  const [renovacionResults, setRenovacionResults] = useState(null);
  const [resumenData, setResumenData] = useState(null);

  // Fetch Series
  const { data, isLoading: isLoadingSeries } = useQuery({
    queryKey: ['series-deuda'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/series');
      return res.data;
    }
  });

  const { data: movimientosData, isLoading: isLoadingMovimientos } = useQuery({
    queryKey: ['movimientos-deuda'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/movimientos', { params: { limit: 10000 } });
      return res.data;
    }
  });

  const isLoading = isLoadingSeries || isLoadingMovimientos;

  const series = data?.items || [];
  const movimientos = movimientosData?.items || [];
  const formatCurrency = (val) => new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(val);
  const formatDate = (dateObj) => dateObj.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });

  const computedSeries = useMemo(() => {
    return series.map(s => {
      let calculatedCapital = 0;
      const fCorte = new Date(fechaCorte + 'T23:59:59');
      
      if (movimientos.length > 0) {
        movimientos.forEach(m => {
          if (m.id_serie === s.id) {
            const fMov = new Date(m.fecha);
            if (fMov <= fCorte) {
              const tipo = m.tipo_movimiento;
              let multiplier = 1;
              if (['Rescate', 'Renovación rescate', 'Vencimiento', 'Retiro de intereses'].includes(tipo)) {
                multiplier = -1;
              }
              const mov = m.monto * multiplier;
              let cap = 0;
              if (['Suscripción', 'Renovación suscripción'].includes(tipo)) {
                cap = mov;
              } else {
                cap = mov / (1 + s.tna * (s.plazo / 365));
              }
              calculatedCapital += cap;
            }
          }
        });
      } else {
        calculatedCapital = s.capital || 0;
      }
      return { ...s, computedCapital: calculatedCapital };
    });
  }, [series, movimientos, fechaCorte]);

  const filteredSeries = computedSeries.filter(s => {
    return Object.entries(tableFilters).every(([key, filterValue]) => {
      if (!filterValue || (Array.isArray(filterValue) && filterValue.length === 0)) return true;
      
      const isMonetaryCol = ["capital", "interes", "total", "interesMensual", "interesDevengado", "interesADevengar", "tna", "plazo", "capitalMasDevengado"].includes(key);
      if (isMonetaryCol) {
        if (filterValue.min === undefined && filterValue.max === undefined) return true;
        
        const capital = s.computedCapital || 0;
        const interes = capital * s.tna * (s.plazo / 365);
        const total = capital + interes;
        const fSuscripcion = new Date(s.fecha_suscripcion + 'T00:00:00');
        const fVencimiento = new Date(s.fecha_vencimiento + 'T00:00:00');
        const fCorte = new Date(fechaCorte + 'T23:59:59');
        
        let interesDevengado = 0;
        if (fCorte <= fSuscripcion) interesDevengado = 0;
        else if (fCorte >= fVencimiento) interesDevengado = interes;
        else interesDevengado = capital * s.tna * (((fCorte - fSuscripcion) / 86400000) / 365);
        
        const interesADevengar = Math.max(0, interes - interesDevengado);
        
        const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
        const fechaInicioMensual = fSuscripcion > primerDiaMes ? fSuscripcion : primerDiaMes;
        const fechaFinMensual = fCorte < fVencimiento ? fCorte : fVencimiento;
        let diasMensuales = (fechaFinMensual - fechaInicioMensual) / 86400000;
        if (diasMensuales < 0) diasMensuales = 0;
        const interesMensual = capital * s.tna * (diasMensuales / 365);

        let val = 0;
        if (key === 'capital') val = capital;
        if (key === 'interes') val = interes;
        if (key === 'total') val = total;
        if (key === 'interesMensual') val = interesMensual;
        if (key === 'interesDevengado') val = interesDevengado;
        if (key === 'interesADevengar') val = interesADevengar;
        if (key === 'capitalMasDevengado') val = capital + interesDevengado;
        if (key === 'tna') val = s.tna * 100;
        if (key === 'plazo') val = s.plazo;

        if (filterValue.min !== undefined && val < filterValue.min) return false;
        if (filterValue.max !== undefined && val > filterValue.max) return false;
        return true;
      }
      
      let valStr = '';
      if (key === 'id') valStr = String(s.id);
      if (key === 'name') valStr = s.name;
      if (key === 'comision') valStr = s.comision ? 'Sí' : 'No';
      if (key === 'fecha_suscripcion') valStr = formatDate(new Date(s.fecha_suscripcion + 'T00:00:00'));
      if (key === 'fecha_vencimiento') valStr = formatDate(new Date(s.fecha_vencimiento + 'T00:00:00'));
      
      return filterValue.includes(valStr);
    });
  });

  const filteredAndSortedSeries = useMemo(() => {
    let result = [...filteredSeries];
    if (sortConfig.key) {
      result.sort((a, b) => {
        let valA = a[sortConfig.key];
        let valB = b[sortConfig.key];
        
        // Handle computed values for sorting
        if (["capital", "interes", "total", "interesMensual", "interesDevengado", "interesADevengar", "capitalMasDevengado"].includes(sortConfig.key)) {
          const getComputedValues = (s) => {
            const cap = s.computedCapital || 0;
            const int = cap * s.tna * (s.plazo / 365);
            const fSusc = new Date(s.fecha_suscripcion + 'T00:00:00');
            const fVenc = new Date(s.fecha_vencimiento + 'T00:00:00');
            const fCorte = new Date(fechaCorte + 'T23:59:59');
            let intDev = 0;
            if (fCorte <= fSusc) intDev = 0;
            else if (fCorte >= fVenc) intDev = int;
            else intDev = cap * s.tna * (((fCorte - fSusc) / 86400000) / 365);
            
            const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
            const fechaInicioMensual = fSusc > primerDiaMes ? fSusc : primerDiaMes;
            const fechaFinMensual = fCorte < fVenc ? fCorte : fVenc;
            let diasMensuales = (fechaFinMensual - fechaInicioMensual) / 86400000;
            if (diasMensuales < 0) diasMensuales = 0;
            
            return {
              capital: cap,
              interes: int,
              total: cap + int,
              interesDevengado: intDev,
              interesADevengar: Math.max(0, int - intDev),
              interesMensual: cap * s.tna * (diasMensuales / 365),
              capitalMasDevengado: cap + intDev
            };
          };
          const compA = getComputedValues(a);
          const compB = getComputedValues(b);
          valA = compA[sortConfig.key];
          valB = compB[sortConfig.key];
        }
        if (sortConfig.key === 'comision') { valA = a.comision ? 1 : 0; valB = b.comision ? 1 : 0; }
        if (sortConfig.key === 'fecha_suscripcion' || sortConfig.key === 'fecha_vencimiento') {
          valA = new Date(valA + 'T00:00:00').getTime();
          valB = new Date(valB + 'T00:00:00').getTime();
        }

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [filteredSeries, sortConfig]);

  const getAvailableOptions = (key) => {
    if (!series) return [];
    
    const validRows = computedSeries.filter(s => {
      return Object.entries(tableFilters).every(([filterKey, filterValue]) => {
        if (filterKey === key) return true;
        if (!filterValue || (Array.isArray(filterValue) && filterValue.length === 0)) return true;
        
        const isMonetaryCol = ["capital", "interes", "total", "interesMensual", "interesDevengado", "interesADevengar", "tna", "plazo", "capitalMasDevengado"].includes(filterKey);
        if (isMonetaryCol) {
          if (filterValue.min === undefined && filterValue.max === undefined) return true;
          
          const capital = s.computedCapital || 0;
          const interes = capital * s.tna * (s.plazo / 365);
          const total = capital + interes;
          const fSuscripcion = new Date(s.fecha_suscripcion + 'T00:00:00');
          const fVencimiento = new Date(s.fecha_vencimiento + 'T00:00:00');
          const fCorte = new Date(fechaCorte + 'T23:59:59');
          
          let interesDevengado = 0;
          if (fCorte <= fSuscripcion) interesDevengado = 0;
          else if (fCorte >= fVencimiento) interesDevengado = interes;
          else interesDevengado = capital * s.tna * (((fCorte - fSuscripcion) / 86400000) / 365);
          
          const interesADevengar = Math.max(0, interes - interesDevengado);
          
          const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
          const fechaInicioMensual = fSuscripcion > primerDiaMes ? fSuscripcion : primerDiaMes;
          const fechaFinMensual = fCorte < fVencimiento ? fCorte : fVencimiento;
          let diasMensuales = (fechaFinMensual - fechaInicioMensual) / 86400000;
          if (diasMensuales < 0) diasMensuales = 0;
          const interesMensual = capital * s.tna * (diasMensuales / 365);

          let val = 0;
          if (filterKey === 'capital') val = capital;
          if (filterKey === 'interes') val = interes;
          if (filterKey === 'total') val = total;
          if (filterKey === 'interesMensual') val = interesMensual;
          if (filterKey === 'interesDevengado') val = interesDevengado;
          if (filterKey === 'interesADevengar') val = interesADevengar;
          if (filterKey === 'capitalMasDevengado') val = capital + interesDevengado;
          if (filterKey === 'tna') val = s.tna * 100;
          if (filterKey === 'plazo') val = s.plazo;

          if (filterValue.min !== undefined && val < filterValue.min) return false;
          if (filterValue.max !== undefined && val > filterValue.max) return false;
          return true;
        }
        
        let valStr = '';
        if (filterKey === 'id') valStr = String(s.id);
        if (filterKey === 'name') valStr = s.name;
        if (filterKey === 'comision') valStr = s.comision ? 'Sí' : 'No';
        if (filterKey === 'fecha_suscripcion') valStr = formatDate(new Date(s.fecha_suscripcion + 'T00:00:00'));
        if (filterKey === 'fecha_vencimiento') valStr = formatDate(new Date(s.fecha_vencimiento + 'T00:00:00'));
        
        return filterValue.includes(valStr);
      });
    });

    const options = new Set();
    validRows.forEach(s => {
      let valStr = '';
      if (key === 'id') valStr = String(s.id);
      if (key === 'name') valStr = s.name;
      if (key === 'comision') valStr = s.comision ? 'Sí' : 'No';
      if (key === 'fecha_suscripcion') valStr = formatDate(new Date(s.fecha_suscripcion + 'T00:00:00'));
      if (key === 'fecha_vencimiento') valStr = formatDate(new Date(s.fecha_vencimiento + 'T00:00:00'));
      if (valStr) options.add(valStr);
    });
    return Array.from(options).sort();
  };

  const totals = filteredAndSortedSeries.reduce((acc, s) => {
    const capital = s.computedCapital || 0;
    const interes = capital * s.tna * (s.plazo / 365);
    const total = capital + interes;

    const fSuscripcion = new Date(s.fecha_suscripcion + 'T00:00:00');
    const fVencimiento = new Date(s.fecha_vencimiento + 'T00:00:00');
    const fCorte = new Date(fechaCorte + 'T23:59:59');

    let interesDevengado = 0;
    if (fCorte <= fSuscripcion) interesDevengado = 0;
    else if (fCorte >= fVencimiento) interesDevengado = interes;
    else interesDevengado = capital * s.tna * (((fCorte - fSuscripcion) / 86400000) / 365);

    const interesADevengar = Math.max(0, interes - interesDevengado);

    const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
    const fechaInicioMensual = fSuscripcion > primerDiaMes ? fSuscripcion : primerDiaMes;
    const fechaFinMensual = fCorte < fVencimiento ? fCorte : fVencimiento;
    let diasMensuales = (fechaFinMensual - fechaInicioMensual) / 86400000;
    if (diasMensuales < 0) diasMensuales = 0;
    const interesMensual = capital * s.tna * (diasMensuales / 365);

    acc.capital += capital;
    acc.interes += interes;
    acc.total += total;
    acc.interesDevengado += interesDevengado;
    acc.interesADevengar += interesADevengar;
    acc.interesMensual += interesMensual;
    acc.capitalMasDevengado += (capital + interesDevengado);

    return acc;
  }, { capital: 0, interes: 0, total: 0, interesDevengado: 0, interesADevengar: 0, interesMensual: 0, capitalMasDevengado: 0 });

  // Add Mutation
  const addMutation = useMutation({
    mutationFn: async (nuevaSerie) => {
      let res;
      if (nuevaSerie.file) {
        const formData = new FormData();
        formData.append('name', nuevaSerie.name);
        formData.append('fecha_suscripcion', nuevaSerie.fecha_suscripcion);
        formData.append('tna', nuevaSerie.tna);
        formData.append('plazo', nuevaSerie.plazo);
        formData.append('file', nuevaSerie.file);
        res = await axiosClient.post('/api/v1/inversores/series/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        res = await axiosClient.post('/api/v1/inversores/series', nuevaSerie);
      }
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
      setShowAddModal(false);
      alert('Serie creada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al crear la serie');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const res = await axiosClient.delete(`/api/v1/inversores/series/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al eliminar la serie');
    }
  });

  const editMutation = useMutation({
    mutationFn: async ({ id, data }) => {
      const res = await axiosClient.put(`/api/v1/inversores/series/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
      setEditSerieData(null);
      alert('Serie actualizada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al actualizar la serie');
    }
  });

  const renovarMutation = useMutation({
    mutationFn: async (renovacionData) => {
      const formData = new FormData();
      formData.append('serie_vieja', renovacionData.serie_vieja);
      formData.append('serie_nueva', renovacionData.serie_nueva);
      formData.append('fecha_suscripcion', renovacionData.fecha_suscripcion);
      formData.append('tna', renovacionData.tna);
      formData.append('plazo', renovacionData.plazo);
      if (renovacionData.file) {
        formData.append('file', renovacionData.file);
      }
      
      const res = await axiosClient.post('/api/v1/inversores/series/renovacion', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
      setShowRenovacionModal(false);
      if (data.df_ei && data.df_ei.length > 0) {
        setRenovacionResults(data.df_ei);
      } else {
        alert('Serie renovada con éxito. No se detectaron rescates o suscripciones adicionales.');
      }
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al renovar la serie');
    }
  });

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.4, marginLeft: '5px' }} title="Haz clic para ordenar">↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2>Series de Deuda</h2>
          <p>Gestione las series emitidas para suscripción de los inversores.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button 
            className="btn-secondary" 
            onClick={() => setTableFilters({})}
            title="Limpiar todos los filtros"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            Limpiar Filtros
          </button>
          {!isAuditor && (
            <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Plus size={16} /> Nueva Serie
            </button>
          )}
        </div>
      </header>

      <div className="glass-panel" style={{ padding: '15px', marginBottom: '20px', display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-end', backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)' }}>CÁLCULO DE INTERESES</span>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: '11px' }}>Fecha de Corte</label>
            <input type="date" value={fechaCorte} onChange={e => setFechaCorte(e.target.value)} style={{ padding: '6px 12px' }} />
          </div>
        </div>
      </div>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                {[
                            { key: 'id', label: 'ID' },
                  { key: 'name', label: 'Nombre' },
                  { key: 'fecha_suscripcion', label: 'Fecha de Susc.' },
                  { key: 'tna', label: 'TNA (%)' },
                  { key: 'plazo', label: 'Plazo (días)' },
                  { key: 'fecha_vencimiento', label: 'Fecha Venc.' },
                  { key: 'capital', label: 'Capital' },
                  { key: 'interes', label: 'Interés' },
                  { key: 'total', label: 'Total' },
                  { key: 'interesMensual', label: 'Int. Mensual' },
                  { key: 'interesDevengado', label: 'Int. Devengado' },
                  { key: 'interesADevengar', label: 'Int. a Devengar' },
                  { key: 'capitalMasDevengado', label: 'Cap. + Int. Dev.' },
                  { key: 'comision', label: 'Comisión' },
                ].map(col => {
                  const isMonetaryCol = ["capital", "interes", "total", "interesMensual", "interesDevengado", "interesADevengar", "tna", "plazo", "capitalMasDevengado"].includes(col.key);
                  const isDateCol = ["fecha_suscripcion", "fecha_vencimiento"].includes(col.key);
                  
                  return (
                    <th key={col.key} onClick={() => handleSort(col.key)} style={{ cursor: 'pointer' }}>
                      <div style={{ marginBottom: '8px' }}>
                        {col.label} <SortIcon columnKey={col.key} />
                      </div>
                      <div onClick={e => e.stopPropagation()}>
                        {isMonetaryCol ? (
                          <ExcelNumberRangeFilter
                            selectedRange={tableFilters[col.key]}
                            onChange={(range) => handleTableFilterChange(col.key, range)}
                          />
                        ) : isDateCol ? (
                          <ExcelDateFilter
                            availableDates={getAvailableOptions(col.key)}
                            selectedDates={tableFilters[col.key] || []}
                            onChange={(dates) => handleTableFilterChange(col.key, dates)}
                          />
                        ) : (
                          <ExcelListFilter
                            availableOptions={getAvailableOptions(col.key)}
                            selectedOptions={tableFilters[col.key] || []}
                            onChange={(selected) => handleTableFilterChange(col.key, selected)}
                            title={`Filtrar ${col.label}`}
                          />
                        )}
                      </div>
                    </th>
                  );
                })}
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="15" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : filteredAndSortedSeries.length === 0 ? (
                <tr><td colSpan="15" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron series.</td></tr>
              ) : (
                filteredAndSortedSeries.map(s => {
                  const capital = s.computedCapital || 0;
                  const interes = capital * s.tna * (s.plazo / 365);
                  const total = capital + interes;

                  // Handle timezone issues by using string parsing if necessary, but simple Date object works well for YYYY-MM-DD
                  const fSuscripcion = new Date(s.fecha_suscripcion + 'T00:00:00');
                  const fVencimiento = new Date(s.fecha_vencimiento + 'T00:00:00');
                  const fCorte = new Date(fechaCorte + 'T00:00:00');

                  let interesDevengado = 0;
                  if (fCorte <= fSuscripcion) {
                    interesDevengado = 0;
                  } else if (fCorte >= fVencimiento) {
                    interesDevengado = interes;
                  } else {
                    const diasTranscurridos = (fCorte - fSuscripcion) / (1000 * 60 * 60 * 24);
                    interesDevengado = capital * s.tna * (diasTranscurridos / 365);
                  }

                  const interesADevengar = Math.max(0, interes - interesDevengado);

                  // Calculo de interes mensual
                  const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
                  const fechaInicioMensual = fSuscripcion > primerDiaMes ? fSuscripcion : primerDiaMes;
                  const fechaFinMensual = fCorte < fVencimiento ? fCorte : fVencimiento;
                  let diasMensuales = (fechaFinMensual - fechaInicioMensual) / (1000 * 60 * 60 * 24);
                  if (diasMensuales < 0) diasMensuales = 0;
                  const interesMensual = capital * s.tna * (diasMensuales / 365);

                  return (
                    <tr key={s.id}>
                      <td>{s.id}</td>
                      <td><strong>{s.name}</strong></td>
                      <td>{formatDate(fSuscripcion)}</td>
                      <td>{(s.tna * 100).toFixed(2)}%</td>
                      <td>{s.plazo}</td>
                      <td>{formatDate(fVencimiento)}</td>
                      <td>{formatCurrency(capital)}</td>
                      <td>{formatCurrency(interes)}</td>
                      <td>{formatCurrency(total)}</td>
                      <td>{formatCurrency(interesMensual)}</td>
                      <td>{formatCurrency(interesDevengado)}</td>
                      <td>{formatCurrency(interesADevengar)}</td>
                      <td style={{ fontWeight: 'bold' }}>{formatCurrency(capital + interesDevengado)}</td>
                      <td>
                        {s.comision ? (
                          <span style={{ color: 'var(--success-color)', fontWeight: 'bold' }}>
                            Sí {s.comisiones?.length > 0 ? `(${s.comisiones.length})` : ''}
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)' }}>No</span>
                        )}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button 
                            className="btn-secondary" 
                            style={{ padding: '4px', fontSize: '14px' }}
                            onClick={async () => {
                              try {
                                const res = await axiosClient.get(`/api/v1/inversores/series/${s.id}/resumen`);
                                setResumenData({ serieName: s.name, data: res.data.data });
                              } catch(error) {
                                alert(error.response?.data?.detail || 'Error al obtener el resumen');
                              }
                            }}
                            title="Ver Resumen"
                          >
                            📋
                          </button>
                          {!isAuditor && (
                            <>
                              <button 
                                className="btn-secondary" 
                                style={{ padding: '4px', fontSize: '14px' }}
                                onClick={() => setEditSerieData(s)}
                                title="Editar Serie"
                              >
                                ✏️
                              </button>
                              <button 
                                className="btn-secondary" 
                                style={{ padding: '4px', fontSize: '14px' }}
                                onClick={() => {
                                  setSelectedSerieVieja(s);
                                  setShowRenovacionModal(true);
                                }}
                                title="Renovar Serie"
                              >
                                🔄
                              </button>
                              <button 
                                className="btn-secondary" 
                                style={{ padding: '4px', fontSize: '14px', color: 'var(--danger-color)' }}
                                onClick={() => {
                                  if (window.confirm('¿Está seguro de eliminar esta serie? Se eliminarán también todos los movimientos asociados.')) {
                                    deleteMutation.mutate(s.id);
                                  }
                                }}
                                title="Eliminar Serie"
                              >
                                🗑️
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="6" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Totales ({filteredAndSortedSeries.length} series):
                </td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.capital)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interes)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.total)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interesMensual)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interesDevengado)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interesADevengar)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.capitalMasDevengado)}</td>
                <td colSpan="2"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {showAddModal && (
        <AddSerieModal
          onClose={() => setShowAddModal(false)}
          onSubmit={(data) => addMutation.mutate(data)}
          isLoading={addMutation.isPending}
          comisionesDeuda={comisionesDeuda}
        />
      )}
      {editSerieData && (
        <EditSerieModal
          initialData={editSerieData}
          onClose={() => setEditSerieData(null)}
          onSubmit={(data) => editMutation.mutate({ id: editSerieData.id, data })}
          isLoading={editMutation.isPending}
          comisionesDeuda={comisionesDeuda}
          queryClient={queryClient}
        />
      )}
      {showRenovacionModal && selectedSerieVieja && (
        <RenovacionModal
          serieVieja={selectedSerieVieja}
          onClose={() => setShowRenovacionModal(false)}
          onSubmit={(data) => renovarMutation.mutate(data)}
          isLoading={renovarMutation.isPending}
        />
      )}
      {renovacionResults && (
        <RenovacionResultsModal
          data={renovacionResults}
          onClose={() => setRenovacionResults(null)}
        />
      )}
      {resumenData && (
        <ResumenModal
          serieName={resumenData.serieName}
          data={resumenData.data}
          onClose={() => setResumenData(null)}
        />
      )}
    </section>
  );
};

// Modal Component
const AddSerieModal = ({ onClose, onSubmit, isLoading, comisionesDeuda }) => {
  const [formData, setFormData] = useState({
    name: '',
    fecha_suscripcion: '',
    tna: '',
    plazo: '',
    comision: false,
    file: null
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      name: formData.name,
      fecha_suscripcion: formData.fecha_suscripcion,
      tna: parseFloat(formData.tna) / 100,
      plazo: parseInt(formData.plazo, 10),
      comision: formData.comision,
    };
    if (formData.file) {
      data.file = formData.file;
    }
    onSubmit(data);
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '400px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Nueva Serie de Deuda</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          <div className="form-group">
            <label>Nombre de la Serie *</label>
            <input
              type="text"
              required
              maxLength="100"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej. Serie I"
            />
          </div>

          <div className="form-group">
            <label>Fecha de Suscripción *</label>
            <input
              type="date"
              required
              value={formData.fecha_suscripcion}
              onChange={e => setFormData({ ...formData, fecha_suscripcion: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label>Tasa Nominal Anual (TNA %) *</label>
            <input
              type="number"
              required
              step="0.01"
              min="0"
              value={formData.tna}
              onChange={e => setFormData({ ...formData, tna: e.target.value })}
              placeholder="Ej. 45.5"
            />
          </div>

          <div className="form-group">
            <label>Plazo (días) *</label>
            <input
              type="number"
              required
              min="1"
              step="1"
              value={formData.plazo}
              onChange={e => setFormData({ ...formData, plazo: e.target.value })}
              placeholder="Ej. 365"
            />
          </div>

          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label style={{ margin: 0 }}>¿Lleva Comisión?</label>
            <input
              type="checkbox"
              checked={formData.comision}
              onChange={e => setFormData({ ...formData, comision: e.target.checked })}
              style={{ width: '18px', height: '18px' }}
            />
          </div>

          {formData.comision && (
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
              💡 Las comisiones específicas se pueden asignar después de crear la serie desde el modal de edición.
            </p>
          )}

          <div className="form-group">
            <label>Archivo de Suscripciones (Excel/CSV) - Opcional</label>
            <input
              type="file"
              accept=".xlsx,.csv"
              onChange={e => setFormData({ ...formData, file: e.target.files[0] })}
              style={{ padding: '8px 0' }}
            />
            <small style={{ color: 'var(--text-muted)' }}>Procesa y carga las suscripciones asociadas a la serie usando la función `nueva_serie`.</small>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Crear Serie'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Renovacion Modal Component
const RenovacionModal = ({ serieVieja, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    serie_nueva: '',
    fecha_suscripcion: '',
    tna: '',
    plazo: '',
    file: null
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.file) {
      alert("Es necesario adjuntar el archivo de liquidación para la renovación.");
      return;
    }
    const data = {
      serie_vieja: serieVieja.name,
      serie_nueva: formData.serie_nueva,
      fecha_suscripcion: formData.fecha_suscripcion,
      tna: parseFloat(formData.tna) / 100,
      plazo: parseInt(formData.plazo, 10),
      file: formData.file
    };
    onSubmit(data);
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '400px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Renovar Serie: {serieVieja.name}</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          <div className="form-group">
            <label>Nombre de la Nueva Serie *</label>
            <input
              type="text"
              required
              maxLength="100"
              value={formData.serie_nueva}
              onChange={e => setFormData({ ...formData, serie_nueva: e.target.value })}
              placeholder="Ej. Serie II"
            />
          </div>

          <div className="form-group">
            <label>Fecha de Suscripción *</label>
            <input
              type="date"
              required
              value={formData.fecha_suscripcion}
              onChange={e => setFormData({ ...formData, fecha_suscripcion: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label>Tasa Nominal Anual (TNA %) *</label>
            <input
              type="number"
              required
              step="0.01"
              min="0"
              value={formData.tna}
              onChange={e => setFormData({ ...formData, tna: e.target.value })}
              placeholder="Ej. 45.5"
            />
          </div>

          <div className="form-group">
            <label>Plazo (días) *</label>
            <input
              type="number"
              required
              min="1"
              step="1"
              value={formData.plazo}
              onChange={e => setFormData({ ...formData, plazo: e.target.value })}
              placeholder="Ej. 365"
            />
          </div>

          <div className="form-group">
            <label>Archivo de Liquidación (Excel/CSV) *</label>
            <input
              type="file"
              required
              accept=".xlsx,.csv"
              onChange={e => setFormData({ ...formData, file: e.target.files[0] })}
              style={{ padding: '8px 0' }}
            />
            <small style={{ color: 'var(--text-muted)' }}>Procesa los rescates, renovaciones y suscripciones.</small>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Renovando...' : 'Renovar Serie'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Renovacion Results Modal
const RenovacionResultsModal = ({ data, onClose }) => {
  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '800px', maxWidth: '95%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0 }}>Resultados de Renovación (Rescates / Suscripciones)</h3>
          <ExportExcelButton data={data} filename="Renovacion_Resultados" />
        </div>
        
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                {data.length > 0 && Object.keys(data[0]).map((key) => (
                  <th key={key}>{key}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, index) => (
                <tr key={index}>
                  {Object.entries(row).map(([key, val], idx) => {
                    const isMonetaryCol = ["Capital", "Interés", "Total", "Rescate", "Suscripción"].includes(key);
                    const formattedVal = (isMonetaryCol && !isNaN(val) && val !== "")
                      ? new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(val)
                      : String(val);
                    return <td key={idx}>{formattedVal}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
          <button type="button" className="btn-primary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
};

// Resumen Modal
const ResumenModal = ({ serieName, data, onClose }) => {
  const [filters, setFilters] = useState({});
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.4, marginLeft: '5px' }} title="Haz clic para ordenar">↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Filter data
  const filteredAndSortedData = useMemo(() => {
    if (!data) return [];
    let result = data.filter(row => {
      return Object.entries(filters).every(([key, filterValue]) => {
        if (!filterValue) return true;
        
        const isMonetaryCol = ["Capital", "Interés", "Total", "Monto", "Int. Dev."].includes(key);
        
        if (isMonetaryCol) {
          if (filterValue.min === undefined && filterValue.max === undefined) return true;
          let val = row[key];
          if (typeof val === 'string') val = val.replace(/[^0-9.-]+/g,"");
          const numVal = Number(val);
          if (isNaN(numVal)) return false;
          if (filterValue.min !== undefined && numVal < filterValue.min) return false;
          if (filterValue.max !== undefined && numVal > filterValue.max) return false;
          return true;
        } else {
          if (!Array.isArray(filterValue) || filterValue.length === 0) return true;
          const valStr = String(row[key] !== null ? row[key] : '');
          return filterValue.includes(valStr);
        }
      });
    });

    if (sortConfig.key) {
      result.sort((a, b) => {
        let valA = a[sortConfig.key];
        let valB = b[sortConfig.key];
        const isMonetaryCol = ["Capital", "Interés", "Total", "Monto", "Int. Dev."].includes(sortConfig.key);
        const isDateCol = String(sortConfig.key).toLowerCase().includes('fecha');

        if (isMonetaryCol) {
          if (typeof valA === 'string') valA = Number(valA.replace(/[^0-9.-]+/g,""));
          if (typeof valB === 'string') valB = Number(valB.replace(/[^0-9.-]+/g,""));
          valA = isNaN(valA) ? 0 : valA;
          valB = isNaN(valB) ? 0 : valB;
        } else if (isDateCol && valA && valB) {
          const parseDate = (d) => {
            if (typeof d === 'string' && d.includes('/')) {
              const parts = d.split('/');
              return new Date(parts[2], parts[1] - 1, parts[0]).getTime();
            }
            return new Date(d).getTime();
          };
          valA = parseDate(valA);
          valB = parseDate(valB);
        }

        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();

        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [data, filters, sortConfig]);

  const getAvailableOptions = (key) => {
    if (!data) return [];
    
    const validRows = data.filter(row => {
      return Object.entries(filters).every(([filterKey, filterValue]) => {
        if (filterKey === key) return true; // Skip filtering for this column itself
        if (!filterValue) return true;
        
        const isMonetaryCol = ["Capital", "Interés", "Total", "Monto", "Int. Dev."].includes(filterKey);
        
        if (isMonetaryCol) {
          if (filterValue.min === undefined && filterValue.max === undefined) return true;
          let val = row[filterKey];
          if (typeof val === 'string') val = val.replace(/[^0-9.-]+/g,"");
          const numVal = Number(val);
          if (isNaN(numVal)) return false;
          if (filterValue.min !== undefined && numVal < filterValue.min) return false;
          if (filterValue.max !== undefined && numVal > filterValue.max) return false;
          return true;
        } else {
          if (!Array.isArray(filterValue) || filterValue.length === 0) return true;
          const valStr = String(row[filterKey] !== null ? row[filterKey] : '');
          return filterValue.includes(valStr);
        }
      });
    });

    const options = new Set(validRows.map(row => String(row[key] !== null ? row[key] : '')));
    return Array.from(options).sort();
  };

  // Calculate subtotals
  const subtotals = useMemo(() => {
    const totals = {};
    if (filteredAndSortedData.length > 0) {
      Object.keys(filteredAndSortedData[0]).forEach(key => {
        const isMonetaryCol = ["Capital", "Interés", "Total", "Monto", "Int. Dev."].includes(key);
        if (isMonetaryCol) {
          totals[key] = filteredAndSortedData.reduce((acc, row) => {
            let val = row[key];
            if (typeof val === 'string') {
              val = val.replace(/[^0-9.-]+/g,"");
            }
            return acc + (val && !isNaN(val) ? Number(val) : 0);
          }, 0);
        } else {
          totals[key] = null; // not a subtotal col
        }
      });
    }
    return totals;
  }, [filteredAndSortedData]);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '900px', maxWidth: '95%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ margin: 0 }}>Resumen de Serie: {serieName}</h3>
          <ExportExcelButton data={filteredAndSortedData} filename={`Resumen_Serie_${serieName}`} />
        </div>
        
        {data && data.length > 0 ? (
          <>
            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    {Object.keys(data[0]).map((key) => {
                      const isMonetaryCol = ["Capital", "Interés", "Total", "Monto", "Int. Dev."].includes(key);
                      const isDateCol = String(key).toLowerCase().includes('fecha');
                      return (
                        <th key={key} onClick={() => handleSort(key)} style={{ cursor: 'pointer' }}>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <span>{key}</span>
                            <SortIcon columnKey={key} />
                          </div>
                          <div onClick={e => e.stopPropagation()}>
                            {isMonetaryCol ? (
                              <ExcelNumberRangeFilter
                                selectedRange={filters[key]}
                                onChange={(range) => handleFilterChange(key, range)}
                              />
                            ) : isDateCol ? (
                              <ExcelDateFilter
                                availableDates={getAvailableOptions(key)}
                                selectedDates={filters[key] || []}
                                onChange={(selected) => handleFilterChange(key, selected)}
                              />
                            ) : (
                              <ExcelListFilter
                                availableOptions={getAvailableOptions(key)}
                                selectedOptions={filters[key] || []}
                                onChange={(selected) => handleFilterChange(key, selected)}
                                title={`Filtrar ${key}`}
                              />
                            )}
                          </div>
                        </th>
                      );
                    })}
                  </tr>
                </thead>
                <tbody>
                  {filteredAndSortedData.map((row, index) => (
                    <tr key={index}>
                      {Object.entries(row).map(([key, val], idx) => {
                        const isMonetaryCol = ["Capital", "Interés", "Total", "Monto", "Int. Dev."].includes(key);
                        const formattedVal = (isMonetaryCol && !isNaN(val) && val !== "" && val !== null)
                          ? new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(val)
                          : String(val !== null ? val : '');
                        return <td key={idx}>{formattedVal}</td>;
                      })}
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    {Object.keys(data[0]).map((key, idx) => {
                      if (idx === 0) return <td key={idx} style={{ fontWeight: 'bold' }}>Totales ({filteredAndSortedData.length})</td>;
                      const subtotalVal = subtotals[key];
                      if (subtotalVal !== null && subtotalVal !== undefined) {
                        return <td key={idx} style={{ fontWeight: 'bold' }}>{new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(subtotalVal)}</td>;
                      }
                      return <td key={idx}></td>;
                    })}
                  </tr>
                </tfoot>
              </table>
            </div>
          </>
        ) : (
          <p style={{ textAlign: 'center', padding: '20px' }}>No hay datos de resumen para esta serie.</p>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
          <button type="button" className="btn-primary" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
};

export default SeriesPage;

// Edit Modal Component
const EditSerieModal = ({ initialData, onClose, onSubmit, isLoading, comisionesDeuda, queryClient }) => {
  const [formData, setFormData] = useState({
    name: initialData.name || '',
    fecha_suscripcion: initialData.fecha_suscripcion || '',
    tna: initialData.tna ? (initialData.tna * 100).toFixed(2) : '',
    plazo: initialData.plazo || '',
    comision: initialData.comision || false,
  });

  // Local state for comisiones list (starts with existing ones)
  const [comisionesAsociadas, setComisionesAsociadas] = useState(initialData.comisiones || []);
  const [selectedNewComision, setSelectedNewComision] = useState('');
  const [comisionLoading, setComisionLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      name: formData.name,
      fecha_suscripcion: formData.fecha_suscripcion,
      tna: parseFloat(formData.tna) / 100,
      plazo: parseInt(formData.plazo, 10),
      comision: formData.comision,
    };
    onSubmit(data);
  };

  const handleAddComision = async () => {
    if (!selectedNewComision) return;
    const idComision = parseInt(selectedNewComision, 10);
    // Prevent duplicates
    if (comisionesAsociadas.some(c => c.id_comision === idComision)) {
      alert('Esta comisión ya está asociada a la serie');
      return;
    }
    setComisionLoading(true);
    try {
      const res = await axiosClient.post(`/api/v1/inversores/series/${initialData.id}/comisiones`, { id_comision: idComision });
      // Find the comision object to show details
      const comision = comisionesDeuda?.find(c => c.id === idComision);
      setComisionesAsociadas(prev => [...prev, {
        id_comisiones_serie: res.data.id,
        id_comision: idComision,
        fecha: comision?.fecha || '',
        porcentaje: comision?.porcentaje || 0,
        socio_comercial: comision?.socio_comercial || null
      }]);
      setSelectedNewComision('');
      if (queryClient) queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al asociar comisión');
    } finally {
      setComisionLoading(false);
    }
  };

  const handleRemoveComision = async (comisionSerie) => {
    if (!window.confirm('¿Desea quitar esta comisión de la serie?')) return;
    setComisionLoading(true);
    try {
      await axiosClient.delete(`/api/v1/inversores/series/${initialData.id}/comisiones/${comisionSerie.id_comisiones_serie}`);
      setComisionesAsociadas(prev => prev.filter(c => c.id_comisiones_serie !== comisionSerie.id_comisiones_serie));
      if (queryClient) queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al quitar comisión');
    } finally {
      setComisionLoading(false);
    }
  };

  // Available comisiones to add (filter out already associated)
  const availableComisiones = comisionesDeuda?.filter(c => !comisionesAsociadas.some(ca => ca.id_comision === c.id)) || [];

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '500px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Editar Serie</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          <div className="form-group">
            <label>Nombre de la Serie *</label>
            <input
              type="text"
              required
              maxLength="100"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej. Serie I"
            />
          </div>

          <div className="form-group">
            <label>Fecha de Suscripción *</label>
            <input
              type="date"
              required
              value={formData.fecha_suscripcion}
              onChange={e => setFormData({ ...formData, fecha_suscripcion: e.target.value })}
            />
          </div>

          <div className="form-group">
            <label>Tasa Nominal Anual (TNA %) *</label>
            <input
              type="number"
              required
              step="0.01"
              min="0"
              value={formData.tna}
              onChange={e => setFormData({ ...formData, tna: e.target.value })}
              placeholder="Ej. 45.5"
            />
          </div>

          <div className="form-group">
            <label>Plazo (días) *</label>
            <input
              type="number"
              required
              min="1"
              step="1"
              value={formData.plazo}
              onChange={e => setFormData({ ...formData, plazo: e.target.value })}
              placeholder="Ej. 365"
            />
          </div>

          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <label style={{ margin: 0 }}>¿Lleva Comisión?</label>
            <input
              type="checkbox"
              checked={formData.comision}
              onChange={e => setFormData({ ...formData, comision: e.target.checked })}
              style={{ width: '18px', height: '18px' }}
            />
          </div>

          {/* Comisiones Section */}
          {formData.comision && (
            <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '12px' }}>
              <label style={{ fontWeight: 'bold', display: 'block', marginBottom: '10px' }}>Comisiones Asociadas</label>
              
              {/* Current comisiones list */}
              {comisionesAsociadas.length === 0 ? (
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '0 0 10px 0' }}>No hay comisiones asociadas.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '12px' }}>
                  {comisionesAsociadas.map(cs => (
                    <div key={cs.id_comisiones_serie} style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '6px', padding: '8px 10px'
                    }}>
                      <span style={{ fontSize: '13px' }}>
                        <strong>{cs.socio_comercial || `ID ${cs.id_comision}`}</strong>
                        {' — '}{(cs.porcentaje * 100).toFixed(2)}% ({cs.fecha})
                      </span>
                      <button
                        type="button"
                        onClick={() => handleRemoveComision(cs)}
                        disabled={comisionLoading}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--danger-color)', padding: '2px' }}
                        title="Quitar comisión"
                      >
                        <MinusCircle size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add new comision */}
              {availableComisiones.length > 0 && (
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <select
                    value={selectedNewComision}
                    onChange={e => setSelectedNewComision(e.target.value)}
                    style={{ flex: 1, padding: '6px 10px', borderRadius: '6px', border: '1px solid var(--border-color)', backgroundColor: 'var(--input-bg)', color: 'var(--text-color)' }}
                  >
                    <option value="">Agregar comisión...</option>
                    {availableComisiones.map(c => (
                      <option key={c.id} value={c.id}>
                        ID {c.id} — {(c.porcentaje * 100).toFixed(2)}% — {c.fecha}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAddComision}
                    disabled={!selectedNewComision || comisionLoading}
                    className="btn-primary"
                    style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    title="Agregar comisión"
                  >
                    <PlusCircle size={15} /> Agregar
                  </button>
                </div>
              )}
              {availableComisiones.length === 0 && comisionesDeuda?.length > 0 && (
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '8px 0 0 0' }}>Todas las comisiones disponibles ya están asociadas.</p>
              )}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
