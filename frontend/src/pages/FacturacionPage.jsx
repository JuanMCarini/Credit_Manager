import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounce } from '../hooks/useDebounce';
import axiosClient from '../api/axiosClient';
import ExportExcelButton from '../components/ExportExcelButton';
import { ChevronDown, Calendar, Users, Layers, Filter } from 'lucide-react';

const MultiSelect = ({ options, selected, onChange, placeholder, icon: Icon }) => {
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
    isError,
    error,
    isFetching,
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
        const fallbackStr = fallbackMinD.toISOString().split('T')[0];
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
    
    // Set default dates to current month
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    
    setFechaDesde(firstDay.toISOString().split('T')[0]);
    setFechaHasta(lastDay.toISOString().split('T')[0]);
  }, [fetchUltimaFecha]);

  const handleProcesar = async () => {
    if (!window.confirm(`¿Estás seguro que deseas procesar la facturación de ${filteredPendientes.length} cobranzas filtradas con fecha ${fechaFacturacion}?`)) return;
    
    setProcesando(true);
    try {
      const payload = { 
        cobranza_ids: filteredPendientes.map(p => p.id),
        fecha_emision: fechaFacturacion
      };
      const res = await axiosClient.post('/api/v1/facturacion/procesar', payload);
      alert(res.data.message || "Proceso finalizado.");
      queryClient.invalidateQueries({ queryKey: ['pendientes'] });
      fetchUltimaFecha(); // Refresh ultima fecha
    } catch (error) {
      alert("Error procesando facturas: " + (error.response?.data?.detail || error.message));
    } finally {
      setProcesando(false);
    }
  };

  const downloadFile = (url, filename) => {
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDescargarLibro = () => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    downloadFile(`${axiosClient.defaults.baseURL}/api/v1/facturacion/libro-iva?${params.toString()}`, 'libro_iva.xlsx');
  };

  const handleDescargarMasivo = () => {
    const params = new URLSearchParams();
    if (fechaDesde) params.append('fecha_desde', fechaDesde);
    if (fechaHasta) params.append('fecha_hasta', fechaHasta);
    downloadFile(`${axiosClient.defaults.baseURL}/api/v1/facturacion/descargar-masivo?${params.toString()}`, 'facturas.zip');
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
      <header className="section-header">
        <h2>Gestión de Facturación (ARCA)</h2>
        <p>Visualizá cobranzas pendientes de facturar, procesá emisiones automáticas y descargá reportes.</p>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Panel Superior - Pendientes */}
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '10px' }}>
            <h3 style={{ margin: 0 }}>Cobranzas Pendientes ({filteredPendientes.length})</h3>
            <div style={{ display: 'flex', gap: '10px' }}>
              <ExportExcelButton 
                data={pendientes} 
                filteredData={filteredPendientes} 
                filename="cobranzas_pendientes" 
              />
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--surface-color)', padding: '0 8px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)' }}>
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
