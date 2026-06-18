import { useState, useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { useDebounce } from '../hooks/useDebounce';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const CollectionsListPage = () => {
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const initialProcesoId = queryParams.get('proceso_id') || '';

  const [page, setPage] = useState(0);
  const limit = 50;
  
  const [filter, setFilter] = useState({ 
    ID: '', 
    ProcesoID: initialProcesoId, 
    CUIL: '', 
    CreditoID: '', 
    Tipo: ''
  });
  
  const debouncedFilter = useDebounce(filter, 500);

  const fetchCobranzas = async ({ queryKey }) => {
    const [_key, pageIndex, filters] = queryKey;
    const params = {
      skip: pageIndex * limit,
      limit: limit,
      ...(filters.ID && { id_cobranza: filters.ID }),
      ...(filters.ProcesoID && { proceso_id: filters.ProcesoID }),
      ...(filters.CUIL && { cuil: filters.CUIL }),
      ...(filters.CreditoID && { credito_id: filters.CreditoID }),
      ...(filters.Tipo && { tipo: filters.Tipo }),
    };
    
    const res = await axiosClient.get('/api/v1/cobranzas', { params });
    return res.data; // { items: [], total: number }
  };

  const { data, isLoading, isError, error, isFetching } = useQuery({
    queryKey: ['cobranzas', page, debouncedFilter],
    queryFn: fetchCobranzas,
  });

  const { data: procesosData } = useQuery({
    queryKey: ['procesos'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/procesos');
      return res.data;
    }
  });

  const cobranzas = data?.items || [];
  const totalItems = data?.total || 0;
  const totalPages = Math.ceil(totalItems / limit);

  const handleFilterChange = (key, value) => {
    setFilter(prev => ({ ...prev, [key]: value }));
    setPage(0); // Reset page on filter change
  };

  const totals = useMemo(() => {
    return cobranzas.reduce((acc, curr) => ({
      capital: acc.capital + (curr.Capital || 0),
      interes: acc.interes + (curr['Interes'] || 0),
      iva: acc.iva + (curr.IVA || 0),
      total: acc.total + (curr.Total || 0)
    }), { capital: 0, interes: 0, iva: 0, total: 0 });
  }, [cobranzas]);

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado Global de Cobranzas</h2>
          <p>Vista general de las últimas cobranzas y ajustes aplicados.</p>
        </div>
      </header>

      <div className="filter-panel glass-panel" style={{ marginBottom: '15px', padding: '15px', display: 'flex', gap: '15px', alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '12px', fontWeight: 'bold' }}>Filtrar por Proceso de Ingesta</label>
          <select 
            value={filter.ProcesoID} 
            onChange={e => handleFilterChange('ProcesoID', e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-base)', color: 'var(--text-primary)' }}
          >
            <option value="">-- Todos los Procesos --</option>
            {procesosData && procesosData.map(p => (
              <option key={p.ID} value={String(p.ID)}>
                Lote #{p.ID} - {p.Tipo} ({p.Estado}) - {p["Fecha Ejecución"]}
              </option>
            ))}
          </select>
        </div>
        <div style={{ flex: 1 }}>
            <p style={{ fontSize: '12px', opacity: 0.7 }}>
              Mostrando página {page + 1} de {totalPages || 1}. Total: {totalItems} registros. 
              {isFetching && <span style={{ marginLeft: '10px', color: 'var(--accent-primary)' }}>Actualizando...</span>}
            </p>
        </div>
      </div>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>
                  ID
                  <input type="text" placeholder="ID..." value={filter.ID} onChange={e => handleFilterChange('ID', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th>
                  Lote
                </th>
                <th>
                  CUIL
                  <input type="text" placeholder="CUIL..." value={filter.CUIL} onChange={e => handleFilterChange('CUIL', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th>
                  Crédito
                  <input type="text" placeholder="Crédito..." value={filter.CreditoID} onChange={e => handleFilterChange('CreditoID', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th>Cuota</th>
                <th>Fecha Vto</th>
                <th>
                  Tipo
                  <input type="text" placeholder="Tipo..." value={filter.Tipo} onChange={e => handleFilterChange('Tipo', e.target.value)} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th>Capital</th>
                <th>Interés</th>
                <th>IVA</th>
                <th>Total Cobrado</th>
                <th>Fecha Pago</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan="12" className="text-center empty-state" style={{ padding: '40px' }}>
                    Cargando datos...
                  </td>
                </tr>
              ) : isError ? (
                <tr>
                  <td colSpan="12" className="text-center empty-state" style={{ padding: '40px', color: 'red' }}>
                    Error cargando datos: {error.message}
                  </td>
                </tr>
              ) : cobranzas.length === 0 ? (
                <tr>
                  <td colSpan="12" className="text-center empty-state" style={{ padding: '40px' }}>
                    No hay cobranzas para mostrar con los filtros actuales.
                  </td>
                </tr>
              ) : (
                cobranzas.map(c => (
                  <tr key={c.ID}>
                    <td>{c.ID}</td>
                    <td>{c["Proceso ID"]}</td>
                    <td>{c["Cliente CUIL"]}</td>
                    <td>{c["Credito ID"]}</td>
                    <td>{c["Cuota Nro"]}</td>
                    <td>{c["Fecha Vencimiento"]}</td>
                    <td>
                       <span className={`status-badge status-${(c.Tipo || '').toLowerCase().replace(/ /g, '-')}`}>
                         {c.Tipo}
                       </span>
                    </td>
                    <td>{formatCurrency(c.Capital)}</td>
                    <td>{formatCurrency(c['Interes'])}</td>
                    <td>{formatCurrency(c.IVA)}</td>
                    <td style={{ fontWeight: 'bold' }}>{formatCurrency(c.Total)}</td>
                    <td>{c["Fecha Emision"]}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot style={{ background: 'rgba(255, 255, 255, 0.05)', fontWeight: 'bold' }}>
              <tr>
                <td colSpan="7" style={{ textAlign: 'right' }}>TOTALES (Pagina actual):</td>
                <td>{formatCurrency(totals.capital)}</td>
                <td>{formatCurrency(totals.interes)}</td>
                <td>{formatCurrency(totals.iva)}</td>
                <td style={{ color: 'var(--accent-secondary)' }}>{formatCurrency(totals.total)}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
        
        {/* Paginación */}
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '15px', gap: '10px' }}>
          <button 
            className="btn-secondary" 
            onClick={() => setPage(old => Math.max(old - 1, 0))}
            disabled={page === 0}
            style={{ width: 'auto', padding: '5px 15px' }}
          >
            Anterior
          </button>
          <span>Página {page + 1} de {totalPages || 1}</span>
          <button 
            className="btn-secondary" 
            onClick={() => setPage(old => (old + 1 < totalPages ? old + 1 : old))}
            disabled={page + 1 >= totalPages || totalPages === 0}
            style={{ width: 'auto', padding: '5px 15px' }}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
};

export default CollectionsListPage;
