import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import Swal from 'sweetalert2';
import { useDebounce } from '../hooks/useDebounce';
import axiosClient, { downloadFile } from '../api/axiosClient';
import ExportExcelButton from '../components/ExportExcelButton';
import { ChevronDown, Calendar, Users, Layers, Filter } from 'lucide-react';
import { getLocalDateISO } from '../utils/dates';

const MultiSelect = ({ options, selected, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleOption = (opt) => {
    if (selected.includes(opt)) {
      onChange(selected.filter(i => i !== opt));
    } else {
      onChange([...selected, opt]);
    }
  };

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%' }}>
      <div 
        className="form-control" 
        style={{ 
          cursor: 'pointer', 
          minHeight: '42px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: 'var(--surface-color)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--radius-md)',
          transition: 'all 0.2s ease',
          boxShadow: isOpen ? '0 0 0 2px rgba(var(--primary-rgb), 0.2)' : 'none'
        }}
        onClick={() => setIsOpen(!isOpen)}
        onMouseOver={e => e.currentTarget.style.borderColor = 'var(--primary-color)'}
        onMouseOut={e => e.currentTarget.style.borderColor = isOpen ? 'var(--primary-color)' : 'var(--border-color)'}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
          {selected.length === 0 ? (
            <span style={{color: 'var(--text-muted)', fontSize: '13px'}}>{placeholder}</span>
          ) : (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              {selected.length <= 1 ? selected.map(s => (
                <span key={s} style={{ background: 'var(--primary-color)', color: '#fff', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', whiteSpace: 'nowrap', fontWeight: '500' }}>
                  {s}
                </span>
              )) : (
                <span style={{ background: 'var(--primary-color)', color: '#fff', padding: '2px 10px', borderRadius: '12px', fontSize: '12px', whiteSpace: 'nowrap', fontWeight: '500' }}>
                  {selected.length} seleccionados
                </span>
              )}
            </div>
          )}
        </div>
        <ChevronDown size={16} color="var(--text-muted)" style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s ease' }} />
      </div>
      {isOpen && (
        <div style={{ 
          position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '8px', 
          background: 'var(--surface-color)', border: '1px solid var(--border-color)', 
          borderRadius: 'var(--radius-md)', zIndex: 9999, maxHeight: '250px', overflowY: 'auto', 
          padding: '8px', boxShadow: '0 8px 24px rgba(0,0,0,0.3)' 
        }}>
          {options.map(opt => (
            <label key={opt} style={{ 
              display: 'flex', alignItems: 'center', gap: '10px', padding: '8px 12px', 
              cursor: 'pointer', fontSize: '13px', borderRadius: '6px',
              transition: 'background 0.2s ease',
              color: 'var(--text-color)'
            }}
            onMouseOver={e => e.currentTarget.style.background = 'var(--surface-color)'}
            onMouseOut={e => e.currentTarget.style.background = 'transparent'}
            >
              <input 
                type="checkbox" 
                checked={selected.includes(opt)} 
                onChange={() => toggleOption(opt)} 
                style={{ 
                  cursor: 'pointer', width: '16px', height: '16px', accentColor: 'var(--primary-color)' 
                }} 
              />
              {opt}
            </label>
          ))}
          {options.length === 0 && <span style={{color: 'var(--text-muted)', fontSize: '13px', padding: '8px 12px', display: 'block'}}>No hay opciones disponibles</span>}
        </div>
      )}
    </div>
  );
};

const DateRangeFilter = ({ label, desde, setDesde, hasta, setHasta }) => (
  <div style={{ flex: '1 1 250px' }}>
    <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '500', marginBottom: '8px', color: 'var(--text-color)' }}>
      <Calendar size={14} color="var(--primary-color)" /> {label}
    </label>
    <div style={{ 
      display: 'flex', alignItems: 'center', background: 'var(--surface-color)', 
      border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '2px 8px',
      gap: '8px', transition: 'border-color 0.2s ease', height: '42px'
    }}
    onMouseOver={e => e.currentTarget.style.borderColor = 'var(--primary-color)'}
    onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border-color)'}
    >
      <input 
        type="date" 
        style={{ border: 'none', background: 'transparent', color: 'var(--text-color)', flex: 1, fontSize: '13px', outline: 'none' }} 
        value={desde} onChange={e => setDesde(e.target.value)} title="Desde" 
      />
      <span style={{ color: 'var(--text-muted)', fontSize: '14px', fontWeight: 'bold' }}>→</span>
      <input 
        type="date" 
        style={{ border: 'none', background: 'transparent', color: 'var(--text-color)', flex: 1, fontSize: '13px', outline: 'none' }} 
        value={hasta} onChange={e => setHasta(e.target.value)} title="Hasta" 
      />
    </div>
  </div>
);

const FacturacionPage = () => {
  const limit = 1000;
  const queryClient = useQueryClient();

  const [filtroSocios, setFiltroSocios] = useState([]);
  const [filtroProcesos, setFiltroProcesos] = useState([]);
  const [filtroFechaEmisionDesde, setFiltroFechaEmisionDesde] = useState('');
  const [filtroFechaEmisionHasta, setFiltroFechaEmisionHasta] = useState('');
  const [filtroFechaVtoDesde, setFiltroFechaVtoDesde] = useState('');
  const [filtroFechaVtoHasta, setFiltroFechaVtoHasta] = useState('');
  
  const [procesando, setProcesando] = useState(false);
  const [fechaFacturacion, setFechaFacturacion] = useState(getLocalDateISO());
  const [minDateStr, setMinDateStr] = useState('');
  const maxDateStr = getLocalDateISO();
  const [arcaStatus, setArcaStatus] = useState(null);
  const [puntoVenta, setPuntoVenta] = useState(1);
  const [tipoComprobante, setTipoComprobante] = useState(6);
  const [ultimoResultadoLote, setUltimoResultadoLote] = useState(null);
  
  const [fechaDesde, setFechaDesde] = useState('');
  const [fechaHasta, setFechaHasta] = useState('');

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value);
  };

  const activeFilters = useMemo(() => ({
    socios: filtroSocios,
    procesos: filtroProcesos,
    emisionDesde: filtroFechaEmisionDesde,
    emisionHasta: filtroFechaEmisionHasta,
    vtoDesde: filtroFechaVtoDesde,
    vtoHasta: filtroFechaVtoHasta,
  }), [filtroSocios, filtroProcesos, filtroFechaEmisionDesde, filtroFechaEmisionHasta, filtroFechaVtoDesde, filtroFechaVtoHasta]);
  
  const debouncedFilter = useDebounce(activeFilters, 500);

  const fetchPendientes = async ({ pageParam = 0, queryKey }) => {
    const [_key, filters] = queryKey;
    const p = {
      skip: pageParam * limit,
      limit: limit,
      ...(filters.socios && filters.socios.length > 0 && { socios: filters.socios.join(',') }),
      ...(filters.procesos && filters.procesos.length > 0 && { procesos: filters.procesos.join(',') }),
      ...(filters.emisionDesde && { fecha_emision_desde: filters.emisionDesde }),
      ...(filters.emisionHasta && { fecha_emision_hasta: filters.emisionHasta }),
      ...(filters.vtoDesde && { fecha_vto_desde: filters.vtoDesde }),
      ...(filters.vtoHasta && { fecha_vto_hasta: filters.vtoHasta }),
    };
    const res = await axiosClient.get('/api/v1/facturacion/pendientes', { params: p });
    return res.data;
  };

  const {
    data,
    isLoading: loading,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage
  } = useInfiniteQuery({
    queryKey: ['pendientes', debouncedFilter],
    queryFn: fetchPendientes,
    getNextPageParam: (lastPage, pages) => {
       const loadedItems = pages.length * limit;
       if (loadedItems < lastPage.total) {
           return pages.length;
       }
       return undefined;
    }
  });

  const pendientes = useMemo(() => data?.pages.flatMap(page => page.items) || [], [data]);
  const totalItems = data?.pages[0]?.total || 0;

  const fetchUltimaFecha = useCallback(async () => {
    try {
      const res = await axiosClient.get('/api/v1/facturacion/ultima-fecha');
      if (res.data.ultima_fecha) {
        const ultima = res.data.ultima_fecha;
        const fallbackMinD = new Date();
        fallbackMinD.setDate(new Date().getDate() - 10);
        const fallbackStr = getLocalDateISO(fallbackMinD);
        // max of fallbackStr and ultima
        const newMin = ultima > fallbackStr ? ultima : fallbackStr;
        setMinDateStr(newMin);
        setFechaFacturacion(prev => prev < newMin ? newMin : prev);
      }
    } catch (error) {
      console.error("Error cargando última fecha:", error);
    }
  }, []);

  useEffect(() => {
    fetchUltimaFecha();
    axiosClient
      .get('/api/v1/system/arca/status')
      .then((res) => {
        const st = res.data || {};
        setArcaStatus(st);
        if (st.punto_venta_default) {
          setPuntoVenta(Number(st.punto_venta_default));
        }
        if (
          st.condicion_iva_emisor === 'MONOTRIBUTISTA' ||
          st.condicion_iva_emisor === 'EXENTO'
        ) {
          setTipoComprobante(11);
        } else {
          setTipoComprobante(6);
        }
      })
      .catch(() => {});
    
    // Set default dates to current month
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    
    setFechaDesde(getLocalDateISO(firstDay));
    setFechaHasta(getLocalDateISO(lastDay));
  }, [fetchUltimaFecha]);

  const handleProcesar = async () => {
    const envActual = (arcaStatus?.environment || 'mock').toLowerCase();
    const esReal = envActual === 'homologacion' || envActual === 'produccion';
    const tipoLabel =
      Number(tipoComprobante) === 11
        ? 'Factura C (Cod. 011)'
        : 'Factura B (Cod. 006)';
    const pvStr = String(puntoVenta || 1).padStart(4, '0');

    if (esReal) {
      const confirmReal = await Swal.fire({
        icon: 'warning',
        title:
          envActual === 'produccion'
            ? '⚠️ Confirmar Emisión Fiscal REAL en ARCA (PRODUCCIÓN)'
            : 'Confirmar Emisión en ARCA (HOMOLOGACIÓN)',
        html: `
          <div style="text-align:left;font-size:14px;line-height:1.6;">
            <p>Estás por emitir comprobantes electrónicos reales ante <strong>ARCA (${envActual.toUpperCase()})</strong>:</p>
            <ul style="margin:8px 0;padding-left:18px;">
              <li><strong>Cantidad de cobranzas:</strong> ${filteredPendientes.length}</li>
              <li><strong>Punto de Venta:</strong> ${pvStr}</li>
              <li><strong>Tipo de Comprobante:</strong> ${tipoLabel}</li>
              <li><strong>Fecha de Emisión:</strong> ${fechaFacturacion}</li>
              <li><strong>Importe Total:</strong> ${formatCurrency(totales.importe_total)}</li>
            </ul>
            <p style="color:#f59e0b;margin-top:8px;"><strong>¿Confirmás que deseás emitir estas facturas reales en ARCA?</strong></p>
          </div>
        `,
        showCancelButton: true,
        confirmButtonColor: envActual === 'produccion' ? '#dc2626' : '#2563eb',
        cancelButtonColor: '#64748b',
        confirmButtonText: 'Sí, emitir facturas reales en ARCA',
        cancelButtonText: 'Cancelar',
      });
      if (!confirmReal.isConfirmed) return;
    } else {
      if (
        !window.confirm(
          `¿Estás seguro que deseas simular (modo MOCK) la facturación de ${filteredPendientes.length} cobranzas con fecha ${fechaFacturacion}?`
        )
      ) {
        return;
      }
    }
    
    setProcesando(true);
    setUltimoResultadoLote(null);
    try {
      const payload = { 
        cobranza_ids: filteredPendientes.map(p => p.id),
        fecha_emision: fechaFacturacion,
        punto_venta: Number(puntoVenta || 1),
        tipo_comprobante: Number(tipoComprobante || 6),
        confirmar_real: esReal,
      };
      const res = await axiosClient.post('/api/v1/facturacion/procesar', payload);
      setUltimoResultadoLote(res.data);
      const errCount = Array.isArray(res.data?.errores) ? res.data.errores.length : 0;
      await Swal.fire({
        icon: errCount > 0 ? 'warning' : 'success',
        title: errCount > 0 ? 'Lote procesado con observaciones' : 'Facturación completada',
        text: res.data.message || 'Proceso finalizado.',
      });
      queryClient.invalidateQueries({ queryKey: ['pendientes'] });
      fetchUltimaFecha(); // Refresh ultima fecha
    } catch (error) {
      await Swal.fire({
        icon: 'error',
        title: 'Error procesando facturas',
        text: error.response?.data?.detail || error.message,
      });
    } finally {
      setProcesando(false);
    }
  };

  const handleDescargarLibro = async () => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    await downloadFile('/api/v1/facturacion/libro-iva', Object.fromEntries(params), 'libro_iva.xlsx');
  };

  const handleDescargarMasivo = async () => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    await downloadFile('/api/v1/facturacion/descargar-masivo', Object.fromEntries(params), 'facturas.zip');
  };

  // Opciones extraídas para selectores múltiples
  const sociosOptions = useMemo(() => {
    const socios = new Set(pendientes.map(p => p.socio_originador).filter(Boolean));
    return Array.from(socios).sort();
  }, [pendientes]);

  const procesosOptions = useMemo(() => {
    const procesos = new Set(pendientes.map(p => p.proceso_nombre).filter(Boolean));
    return Array.from(procesos).sort();
  }, [pendientes]);

  const filteredPendientes = pendientes;

  const totales = useMemo(() => {
    return filteredPendientes.reduce((acc, p) => ({
      capital: acc.capital + (p.capital || 0),
      interes: acc.interes + (p.interes || 0),
      iva: acc.iva + (p.iva || 0),
      importe_total: acc.importe_total + (p.importe_total || 0)
    }), { capital: 0, interes: 0, iva: 0, importe_total: 0 });
  }, [filteredPendientes]);

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2>Gestión de Facturación (ARCA)</h2>
          <p>Visualizá cobranzas pendientes de facturar, procesá emisiones automáticas y descargá reportes.</p>
        </div>
        <div
          style={{
            padding: '8px 14px',
            borderRadius: '999px',
            fontSize: '12px',
            fontWeight: '700',
            backgroundColor:
              arcaStatus?.environment === 'produccion'
                ? 'rgba(239, 68, 68, 0.15)'
                : arcaStatus?.environment === 'homologacion'
                ? 'rgba(59, 130, 246, 0.15)'
                : 'rgba(245, 158, 11, 0.15)',
            color:
              arcaStatus?.environment === 'produccion'
                ? '#f87171'
                : arcaStatus?.environment === 'homologacion'
                ? '#60a5fa'
                : '#fbbf24',
            border: '1px solid currentColor',
          }}
        >
          Entorno ARCA: {(arcaStatus?.environment || 'mock').toUpperCase()}
          {arcaStatus?.environment === 'mock' ? ' (Simulación sin validez fiscal)' : ''}
        </div>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {ultimoResultadoLote?.errores?.length > 0 && (
          <div
            className="glass-panel"
            style={{
              padding: '14px 18px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              background: 'rgba(239, 68, 68, 0.1)',
              fontSize: '13px',
            }}
          >
            <strong>Errores detectados en el último lote ({ultimoResultadoLote.errores.length}):</strong>
            <ul style={{ margin: '6px 0 0 18px' }}>
              {ultimoResultadoLote.errores.slice(0, 10).map((err, idx) => (
                <li key={idx}>
                  Cobranza #{err.cobranza_id}: {err.error}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Panel Superior - Pendientes */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '10px' }}>
            <h3 style={{ margin: 0 }}>Cobranzas Pendientes ({filteredPendientes.length})</h3>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              <ExportExcelButton 
                data={pendientes} 
                filteredData={filteredPendientes} 
                filename="cobranzas_pendientes" 
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--surface-color)', padding: '0 8px', height: '40px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 500 }}>PV:</label>
                <input
                  type="number"
                  min="1"
                  max="99999"
                  value={puntoVenta}
                  onChange={(e) => setPuntoVenta(Number(e.target.value) || 1)}
                  style={{ width: '64px', background: 'transparent', border: 'none', color: 'var(--text-color)', fontSize: '13px', outline: 'none' }}
                  title="Punto de Venta ARCA"
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'var(--surface-color)', padding: '0 8px', height: '40px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 500 }}>Comprobante:</label>
                <select
                  value={tipoComprobante}
                  onChange={(e) => setTipoComprobante(Number(e.target.value))}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-color)', fontSize: '13px', outline: 'none' }}
                >
                  <option value={6}>Factura B (006)</option>
                  <option value={11}>Factura C (011)</option>
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--surface-color)', padding: '0 8px', height: '40px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
                <label style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 500 }}>Fecha Factura:</label>
                <input 
                  type="date" 
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-color)', fontSize: '13px', outline: 'none' }}
                  value={fechaFacturacion}
                  min={minDateStr}
                  max={maxDateStr}
                  onChange={(e) => setFechaFacturacion(e.target.value)}
                  title="Fecha de emisión del comprobante (ARCA permite hasta 10 días hacia atrás)"
                />
              </div>
              <button 
                className="btn-primary" 
                onClick={handleProcesar} 
                disabled={procesando || filteredPendientes.length === 0}
              >
                {procesando ? 'Procesando...' : 'Procesar Facturación ⚡'}
              </button>
            </div>
          </div>

          {/* Panel de Filtros */}
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.02)', 
            border: '1px solid var(--border-color)', 
            borderRadius: 'var(--radius-md)', 
            padding: '20px', 
            marginBottom: '24px',
            position: 'relative',
            zIndex: 50
          }}>
            <h4 style={{ margin: '0 0 16px 0', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', color: 'var(--text-color)', fontWeight: '600' }}>
              <Filter size={16} color="var(--primary-color)" /> Filtros de Búsqueda
            </h4>
            <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-start' }}>
              <div style={{ flex: '1 1 250px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '500', marginBottom: '8px', color: 'var(--text-color)' }}>
                  <Users size={14} color="var(--primary-color)" /> Socio Originador
                </label>
                <MultiSelect 
                  options={sociosOptions} 
                  selected={filtroSocios} 
                  onChange={setFiltroSocios} 
                  placeholder="Seleccionar socios..." 
                  icon={Users}
                />
              </div>
              
              <DateRangeFilter 
                label="Emisión Cobranza" 
                desde={filtroFechaEmisionDesde} setDesde={setFiltroFechaEmisionDesde}
                hasta={filtroFechaEmisionHasta} setHasta={setFiltroFechaEmisionHasta}
              />

              <DateRangeFilter 
                label="Vencimiento Cuota" 
                desde={filtroFechaVtoDesde} setDesde={setFiltroFechaVtoDesde}
                hasta={filtroFechaVtoHasta} setHasta={setFiltroFechaVtoHasta}
              />

              <div style={{ flex: '1 1 250px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', fontWeight: '500', marginBottom: '8px', color: 'var(--text-color)' }}>
                  <Layers size={14} color="var(--primary-color)" /> Proceso de Cobranza
                </label>
                <MultiSelect 
                  options={procesosOptions} 
                  selected={filtroProcesos} 
                  onChange={setFiltroProcesos} 
                  placeholder="Seleccionar procesos..." 
                  icon={Layers}
                />
              </div>
            </div>
          </div>
          
          <div className="table-responsive" style={{ maxHeight: '500px', overflowY: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Fecha Cobranza</th>
                  <th>Socio Originador</th>
                  <th>Vto. Cuota</th>
                  <th>Proceso</th>
                  <th>Tipo</th>
                  <th style={{ textAlign: 'right' }}>NO GRAVADO</th>
                  <th style={{ textAlign: 'right' }}>GRAVADO</th>
                  <th style={{ textAlign: 'right' }}>IVA</th>
                  <th style={{ textAlign: 'right' }}>Importe Total</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan="10" style={{ textAlign: 'center', padding: '30px' }}>Cargando datos...</td></tr>
                ) : filteredPendientes.length === 0 ? (
                  <tr><td colSpan="10" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '30px' }}>No hay cobranzas pendientes con los filtros aplicados.</td></tr>
                ) : (
                  filteredPendientes.map(p => (
                    <tr key={p.id}>
                      <td>#{p.id}</td>
                      <td>{p.fecha}</td>
                      <td>{p.socio_originador}</td>
                      <td>{p.vencimiento_cuota || '-'}</td>
                      <td style={{ whiteSpace: 'nowrap' }}>{p.proceso_nombre || '-'}</td>
                      <td>{p.tipo_cobranza}</td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{formatCurrency(p.capital)}</td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{formatCurrency(p.interes)}</td>
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{formatCurrency(p.iva)}</td>
                      <td style={{ textAlign: 'right', fontWeight: 'bold', whiteSpace: 'nowrap' }}>{formatCurrency(p.importe_total)}</td>
                    </tr>
                  ))
                )}
                {hasNextPage && (
                  <tr>
                    <td colSpan="10" style={{ textAlign: 'center', padding: '15px' }}>
                      <button 
                        className="btn-primary" 
                        onClick={() => fetchNextPage()}
                        disabled={isFetchingNextPage}
                        style={{ width: 'auto', padding: '8px 20px', margin: '0 auto', display: 'block' }}
                      >
                        {isFetchingNextPage ? "Cargando más registros..." : "Mostrar más registros"}
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
              {!loading && filteredPendientes.length > 0 && (
                <tfoot>
                  <tr style={{ background: 'var(--surface-color)', fontWeight: 'bold' }}>
                    <td colSpan="6" style={{ textAlign: 'right', paddingRight: '20px' }}>
                      TOTALES (Mostrando {filteredPendientes.length} de {totalItems}):
                    </td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--primary-color)' }}>{formatCurrency(totales.capital)}</td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--primary-color)' }}>{formatCurrency(totales.interes)}</td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--primary-color)' }}>{formatCurrency(totales.iva)}</td>
                    <td style={{ textAlign: 'right', whiteSpace: 'nowrap', color: 'var(--primary-color)', fontSize: '1.1em' }}>{formatCurrency(totales.importe_total)}</td>
                  </tr>
                </tfoot>
              )}
            </table>
          </div>
        </div>

        {/* Panel Inferior - Reportes */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '10px' }}>
            Reportes y Descargas Generales 📥
          </h3>
          
          <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Fecha Desde</label>
              <div style={{ display: 'flex', alignItems: 'center', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0 8px' }}>
                <Calendar size={16} color="var(--primary-color)" style={{ marginRight: '8px' }} />
                <input 
                  type="date" 
                  className="form-control" 
                  style={{ border: 'none', paddingLeft: 0 }}
                  value={fechaDesde} 
                  onChange={e => setFechaDesde(e.target.value)} 
                />
              </div>
            </div>
            <div style={{ flex: 1, minWidth: '200px' }}>
              <label style={{ display: 'block', fontSize: '14px', marginBottom: '8px', color: 'var(--text-muted)' }}>Fecha Hasta</label>
              <div style={{ display: 'flex', alignItems: 'center', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-md)', padding: '0 8px' }}>
                <Calendar size={16} color="var(--primary-color)" style={{ marginRight: '8px' }} />
                <input 
                  type="date" 
                  className="form-control" 
                  style={{ border: 'none', paddingLeft: 0 }}
                  value={fechaHasta} 
                  onChange={e => setFechaHasta(e.target.value)} 
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <button className="btn-secondary" onClick={handleDescargarLibro} style={{ height: '42px', padding: '0 20px' }}>
                Descargar Libro IVA (Excel)
              </button>
              <button className="btn-secondary" onClick={handleDescargarMasivo} style={{ height: '42px', padding: '0 20px' }}>
                Descargar PDFs (ZIP)
              </button>
            </div>
          </div>
        </div>

      </div>
    </section>
  );
};

export default FacturacionPage;
