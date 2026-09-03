import { useState, useMemo } from 'react';
import { FilterX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounce } from '../hooks/useDebounce';
import axiosClient from '../api/axiosClient';
import ClientEditModal from '../components/ClientEditModal';
import ClientCCModal from '../components/ClientCCModal';
import ClientViewModal from '../components/ClientViewModal';
import ExportExcelButton from '../components/ExportExcelButton';
import { CreditCard, Eye, Edit, Trash2 } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';

const ClientListPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAuditor = user?.rol === 'Auditor / Solo Lectura';
  const limit = 1000;

  const [filter, setFilter] = useState({ CUIL: '', Documento: '', Apellido: '', Nombre: '', Estado: [], Mail: '', Teléfono: '' });
  const debouncedFilter = useDebounce(filter, 500);
  
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);

  const ESTADOS_DISPONIBLES = ['ACTIVO', 'INACTIVO', 'MOROSO', 'INCOBRABLE'];

  const [editCuil, setEditCuil] = useState(null);
  const [ccCuil, setCcCuil] = useState(null);
  const [viewClient, setViewClient] = useState(null);

  const fetchClients = async ({ pageParam = 0, queryKey }) => {
    const [_key, filters] = queryKey;
    const f = { ...filters };
    const p = {
      skip: pageParam * limit,
      limit: limit,
      ...(f.CUIL && { cuil: f.CUIL }),
      ...(f.Documento && { documento: f.Documento }),
      ...(f.Apellido && { apellido: f.Apellido }),
      ...(f.Nombre && { nombre: f.Nombre }),
      ...(f.Estado && f.Estado.length > 0 && { estado: f.Estado.join(',') }),
      ...(f.Mail && { mail: f.Mail }),
      ...(f.Teléfono && { telefono: f.Teléfono }),
    };
    const res = await axiosClient.get('/api/v1/clientes', { params: p });
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
    queryKey: ['clientes', debouncedFilter],
    queryFn: fetchClients,
    getNextPageParam: (lastPage, pages) => {
       const loadedItems = pages.length * limit;
       if (loadedItems < lastPage.total) {
           return pages.length;
       }
       return undefined;
    }
  });

  const clients = useMemo(() => data?.pages.flatMap(page => page.items) || [], [data]);
  const totalItems = data?.pages[0]?.total || 0;

  const handleDelete = async (cuil) => {
    if (!window.confirm(`¿Está seguro que desea eliminar al cliente con CUIL ${cuil}?`)) return;
    try {
      await axiosClient.delete(`/api/v1/clientes/${cuil}`);
      alert('Cliente eliminado con éxito.');
      queryClient.invalidateQueries({ queryKey: ['clientes'] });
    } catch (error) {
      alert("Error eliminando cliente: " + error.message);
    }
  };

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const filteredAndSortedClients = useMemo(() => {
    let result = [...clients];

    // Sort
    if (sortConfig.key) {
      result.sort((a, b) => {
        let valA = a[sortConfig.key] || '';
        let valB = b[sortConfig.key] || '';
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();
        
        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }
    return result;
  }, [clients, filter, sortConfig]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
  };

  const handleEstadoToggle = (estado) => {
    setFilter(prev => {
      const current = prev.Estado;
      if (current.includes(estado)) {
        return { ...prev, Estado: current.filter(e => e !== estado) };
      } else {
        return { ...prev, Estado: [...current, estado] };
      }
    });
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado de Clientes</h2>
          <p>Visualización de la cartera completa de clientes.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button className="btn-primary" onClick={() => queryClient.invalidateQueries({ queryKey: ['clientes'] })} disabled={loading || isFetching} style={{ width: 'auto' }}>
            {(loading || isFetching) ? "Actualizando..." : "Actualizar Datos"}
          </button>
          <button 
            className="btn-secondary" 
            onClick={() => setFilter({ CUIL: '', Documento: '', Apellido: '', Nombre: '', Estado: [], Mail: '', Teléfono: '' })}
            title="Limpiar todos los filtros"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '100%', padding: '0 12px' }}
          >
            <FilterX size={16} /> Limpiar Filtros
          </button>
          <ExportExcelButton 
            data={clients} 
            filteredData={filteredAndSortedClients} 
            filename="clientes_export" 
          />
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('CUIL')} style={{ cursor: 'pointer' }}>
                  CUIL <SortIcon columnKey="CUIL" />
                  <input type="text" placeholder="Filtrar CUIL..." value={filter.CUIL} onChange={e => setFilter({ ...filter, CUIL: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Documento')} style={{ cursor: 'pointer' }}>
                  Documento <SortIcon columnKey="Documento" />
                  <input type="text" placeholder="Filtrar Doc..." value={filter.Documento} onChange={e => setFilter({ ...filter, Documento: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Apellido')} style={{ cursor: 'pointer' }}>
                  Apellido <SortIcon columnKey="Apellido" />
                  <input type="text" placeholder="Filtrar Apellido..." value={filter.Apellido} onChange={e => setFilter({ ...filter, Apellido: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Nombre')} style={{ cursor: 'pointer' }}>
                  Nombre <SortIcon columnKey="Nombre" />
                  <input type="text" placeholder="Filtrar Nombre..." value={filter.Nombre} onChange={e => setFilter({ ...filter, Nombre: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Estado')} style={{ cursor: 'pointer' }}>
                  Estado <SortIcon columnKey="Estado" />
                  <div 
                    onClick={e => { e.stopPropagation(); setShowEstadoFilter(!showEstadoFilter); }}
                    style={{ 
                      width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px', 
                      background: 'rgba(255,255,255,0.1)', border: '1px solid var(--border-color)', 
                      borderRadius: '4px', textAlign: 'center', cursor: 'pointer' 
                    }}
                  >
                    {filter.Estado.length === 0 ? "Todos" : `${filter.Estado.length} selec.`}
                  </div>
                  {showEstadoFilter && (
                    <div 
                      onClick={e => e.stopPropagation()} 
                      style={{
                        position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
                        background: 'var(--surface-color)', border: '1px solid var(--border-color)',
                        borderRadius: '4px', padding: '8px', display: 'flex', flexDirection: 'column',
                        gap: '4px', boxShadow: '0 4px 12px rgba(0,0,0,0.5)', marginTop: '4px'
                      }}
                    >
                      {ESTADOS_DISPONIBLES.map(est => (
                        <label key={est} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 'normal', cursor: 'pointer' }}>
                          <input 
                            type="checkbox" 
                            checked={filter.Estado.includes(est)}
                            onChange={() => handleEstadoToggle(est)}
                          />
                          {est}
                        </label>
                      ))}
                    </div>
                  )}
                </th>
                <th onClick={() => handleSort('Mail')} style={{ cursor: 'pointer' }}>
                  Email <SortIcon columnKey="Mail" />
                  <input type="text" placeholder="Filtrar Email..." value={filter.Mail} onChange={e => setFilter({ ...filter, Mail: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th onClick={() => handleSort('Teléfono')} style={{ cursor: 'pointer' }}>
                  Teléfono <SortIcon columnKey="Teléfono" />
                  <input type="text" placeholder="Filtrar Tel..." value={filter.Teléfono} onChange={e => setFilter({ ...filter, Teléfono: e.target.value })} onClick={e => e.stopPropagation()} style={{ width: '100%', marginTop: '5px', padding: '4px', fontSize: '12px' }} />
                </th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedClients.length === 0 ? (
                <tr>
                  <td colSpan="8" className="text-center empty-state" style={{ padding: '40px' }}>
                    {loading ? "Cargando..." : "No se encontraron resultados."}
                  </td>
                </tr>
              ) : (
                filteredAndSortedClients.map(c => (
                  <tr key={c.CUIL}>
                    <td>{c.CUIL}</td>
                    <td>{c.Documento}</td>
                    <td>{c.Apellido}</td>
                    <td>{c.Nombre}</td>
                    <td>
                      <span className={`status-badge status-${(c.Estado || 'inactivo').toLowerCase()}`}>
                        {c.Estado}
                      </span>
                    </td>
                    <td>{c.Mail}</td>
                    <td>{c["Teléfono"]}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'nowrap', alignItems: 'center' }}>
                        <button className="btn-secondary" onClick={() => navigate(`/dashboard-clientes?cuil=${c.CUIL}`)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Dashboard de Cliente">
                          📊
                        </button>
                        <button className="btn-secondary" onClick={() => setViewClient(c)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Detalles">
                          ℹ️
                        </button>
                        <button className="btn-secondary" onClick={() => navigate(`/creditos?cuil=${c.CUIL}`)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Créditos">
                          💳
                        </button>
                        <button className="btn-secondary" onClick={() => setCcCuil(c.CUIL)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Cuenta Corriente">
                          👁️
                        </button>
                        {!isAuditor && (
                          <>
                            <button className="btn-secondary" onClick={() => setEditCuil(c.CUIL)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar">
                              ✏️
                            </button>
                            <button className="btn-secondary" onClick={() => handleDelete(c.CUIL)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                              🗑️
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
              {hasNextPage && (
                <tr>
                  <td colSpan="8" style={{ textAlign: 'center', padding: '15px' }}>
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
            <tfoot>
              <tr>
                <td colSpan="8" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  TOTALES (Mostrando {clients.length} de {totalItems})
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
      
      {editCuil && <ClientEditModal cuil={editCuil} onClose={() => setEditCuil(null)} onSuccess={fetchClients} />}
      {ccCuil && <ClientCCModal cuil={ccCuil} clientName={clients.find(c => c.CUIL === ccCuil)?.["Apellido y Nombre"]} onClose={() => setCcCuil(null)} />}
      {viewClient && <ClientViewModal client={viewClient} onClose={() => setViewClient(null)} />}
    </section>
  );
};

export default ClientListPage;
