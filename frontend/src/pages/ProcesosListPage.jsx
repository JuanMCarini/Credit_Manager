import { useState, useEffect, useMemo } from 'react';
import axiosClient from '../api/axiosClient';

const ProcesosListPage = () => {
  const [procesos, setProcesos] = useState([]);
  const [loading, setLoading] = useState(false);
  
  const [filter, setFilter] = useState({ ID: '', Tipo: [], Estado: [], Fecha: { start: '', end: '' } });
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  
  const [showTipoFilter, setShowTipoFilter] = useState(false);
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);

  const TIPOS_DISPONIBLES = ['INDIVIDUAL', 'MASIVO_CSV'];
  const ESTADOS_DISPONIBLES = ['COMPLETADO', 'REVERTIDO', 'PROCESANDO', 'FALLIDO'];

  const fetchProcesos = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/api/v1/procesos');
      setProcesos(res.data);
    } catch (error) {
      alert("Error cargando procesos: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProcesos();
  }, []);

  const handleDelete = async (id) => {
    if (!window.confirm(`¿Está seguro que desea eliminar el proceso de ingesta #${id} junto con todas sus cobranzas asociadas?`)) return;
    try {
      await axiosClient.delete(`/api/v1/procesos/${id}`);
      alert('Proceso eliminado con éxito.');
      fetchProcesos();
    } catch (error) {
      alert("Error eliminando proceso: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const handleTipoToggle = (tipo) => {
    setFilter(prev => {
      const current = prev.Tipo;
      if (current.includes(tipo)) return { ...prev, Tipo: current.filter(e => e !== tipo) };
      return { ...prev, Tipo: [...current, tipo] };
    });
  };

  const handleEstadoToggle = (estado) => {
    setFilter(prev => {
      const current = prev.Estado;
      if (current.includes(estado)) return { ...prev, Estado: current.filter(e => e !== estado) };
      return { ...prev, Estado: [...current, estado] };
    });
  };

  const filteredAndSortedProcesos = useMemo(() => {
    let result = [...procesos];

    if (filter.ID) result = result.filter(p => String(p.ID).includes(filter.ID));
    if (filter.Tipo.length > 0) result = result.filter(p => filter.Tipo.includes(p.Tipo));
    if (filter.Estado.length > 0) result = result.filter(p => filter.Estado.includes(p.Estado));
    if (filter.Fecha.start) result = result.filter(p => p["Fecha Ejecución"] >= filter.Fecha.start);
    if (filter.Fecha.end) result = result.filter(p => p["Fecha Ejecución"] <= filter.Fecha.end);

    if (sortConfig.key) {
      result.sort((a, b) => {
        let valA = a[sortConfig.key] ?? '';
        let valB = b[sortConfig.key] ?? '';
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [procesos, filter, sortConfig]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado de Procesos de Ingesta</h2>
          <p>Vista de procesos de cobranza, tanto masivos como individuales.</p>
        </div>
        <button className="btn-primary" onClick={fetchProcesos} disabled={loading} style={{ width: 'auto' }}>
          {loading ? "Actualizando..." : "Actualizar Datos"}
        </button>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('ID')} style={{ cursor: 'pointer' }}>
                  ID Lote <SortIcon columnKey="ID" />
                  <input type="text" placeholder="Filtrar ID..." value={filter.ID} onChange={e => setFilter({ ...filter, ID: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                
                <th onClick={() => handleSort('Tipo')} style={{ cursor: 'pointer', position: 'relative' }}>
                  Tipo <SortIcon columnKey="Tipo" />
                  <div onClick={e => { e.stopPropagation(); setShowTipoFilter(!showTipoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                    {filter.Tipo.length === 0 ? "Todos" : `${filter.Tipo.length} selec.`}
                  </div>
                  {showTipoFilter && (
                    <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px' }}>
                      {TIPOS_DISPONIBLES.map(est => (
                        <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                          <input type="checkbox" checked={filter.Tipo.includes(est)} onChange={() => handleTipoToggle(est)} />
                          {est}
                        </label>
                      ))}
                    </div>
                  )}
                </th>
                
                <th onClick={() => handleSort('Estado')} style={{ cursor: 'pointer', position: 'relative' }}>
                  Estado <SortIcon columnKey="Estado" />
                  <div onClick={e => { e.stopPropagation(); setShowEstadoFilter(!showEstadoFilter); }} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', borderRadius: '4px', textAlign: 'center', cursor: 'pointer' }}>
                    {filter.Estado.length === 0 ? "Todos" : `${filter.Estado.length} selec.`}
                  </div>
                  {showEstadoFilter && (
                    <div onClick={e => e.stopPropagation()} style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100, background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column', gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px' }}>
                      {ESTADOS_DISPONIBLES.map(est => (
                        <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                          <input type="checkbox" checked={filter.Estado.includes(est)} onChange={() => handleEstadoToggle(est)} />
                          {est}
                        </label>
                      ))}
                    </div>
                  )}
                </th>

                <th onClick={() => handleSort('Fecha Ejecución')} style={{ cursor: 'pointer' }}>
                  Fecha Ejecución <SortIcon columnKey="Fecha Ejecución" />
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <input type="date" value={filter.Fecha.start} onChange={e => setFilter({ ...filter, Fecha: { ...filter.Fecha, start: e.target.value } })} style={{ width: '100%', padding: '4px', fontSize: '10px' }} title="Desde" />
                    <input type="date" value={filter.Fecha.end} onChange={e => setFilter({ ...filter, Fecha: { ...filter.Fecha, end: e.target.value } })} style={{ width: '100%', padding: '4px', fontSize: '10px' }} title="Hasta" />
                  </div>
                </th>
                
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedProcesos.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center empty-state" style={{ padding: '40px' }}>
                    {loading ? "Cargando..." : "No hay procesos para mostrar con los filtros actuales."}
                  </td>
                </tr>
              ) : (
                filteredAndSortedProcesos.map(p => (
                  <tr key={p.ID}>
                    <td>{p.ID}</td>
                    <td>
                       <span className={`status-badge status-${(p.Tipo || '').toLowerCase().replace(/ /g, '-')}`}>
                         {p.Tipo}
                       </span>
                    </td>
                    <td>
                       <span className={`status-badge status-${(p.Estado || '').toLowerCase()}`}>
                         {p.Estado}
                       </span>
                    </td>
                    <td>{p["Fecha Ejecución"]}</td>
                    <td>
                      <button className="btn-secondary" onClick={() => handleDelete(p.ID)} style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--error)' }}>🗑️ Eliminar Lote</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
};

export default ProcesosListPage;
