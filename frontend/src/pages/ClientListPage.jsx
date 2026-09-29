import { useState, useMemo } from 'react';
import { FilterX } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import ClientEditModal from '../components/ClientEditModal';
import ClientCCModal from '../components/ClientCCModal';
import ClientViewModal from '../components/ClientViewModal';
import ExportExcelButton from '../components/ExportExcelButton';
import ExcelListFilter from '../components/ExcelListFilter';
import { CreditCard, Eye, Edit, Trash2 } from 'lucide-react';
import { useAuthStore } from '../store/useAuthStore';

const ClientListPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAuditor = user?.rol === 'Auditor / Solo Lectura';

  const [filter, setFilter] = useState({ CUIL: [], Documento: [], Apellido: [], Nombre: [], Estado: [], Mail: [], Teléfono: [] });
  
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  const [editCuil, setEditCuil] = useState(null);
  const [ccCuil, setCcCuil] = useState(null);
  const [viewClient, setViewClient] = useState(null);

  const fetchClients = async () => {
    const p = {
      skip: 0,
      limit: 100000
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
  } = useQuery({
    queryKey: ['clientes'],
    queryFn: fetchClients,
    keepPreviousData: true
  });

  const clients = useMemo(() => data?.items || [], [data]);
  const totalItems = data?.total || 0;

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

    // Filtros locales
    if (filter.CUIL && filter.CUIL.length > 0) {
      result = result.filter(c => filter.CUIL.includes(c.CUIL));
    }
    if (filter.Documento && filter.Documento.length > 0) {
      result = result.filter(c => filter.Documento.includes(c.Documento));
    }
    if (filter.Apellido && filter.Apellido.length > 0) {
      result = result.filter(c => filter.Apellido.includes(c.Apellido));
    }
    if (filter.Nombre && filter.Nombre.length > 0) {
      result = result.filter(c => filter.Nombre.includes(c.Nombre));
    }
    if (filter.Estado && filter.Estado.length > 0) {
      result = result.filter(c => filter.Estado.includes(c.Estado));
    }
    if (filter.Mail && filter.Mail.length > 0) {
      result = result.filter(c => filter.Mail.includes(c.Mail));
    }
    if (filter.Teléfono && filter.Teléfono.length > 0) {
      result = result.filter(c => filter.Teléfono.includes(c["Teléfono"]));
    }

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

  const AVAILABLE_CUIL = useMemo(() => [...new Set(clients.map(c => c.CUIL).filter(Boolean))].sort(), [clients]);
  const AVAILABLE_DOCUMENTO = useMemo(() => [...new Set(clients.map(c => c.Documento).filter(Boolean))].sort(), [clients]);
  const AVAILABLE_APELLIDO = useMemo(() => [...new Set(clients.map(c => c.Apellido).filter(Boolean))].sort(), [clients]);
  const AVAILABLE_NOMBRE = useMemo(() => [...new Set(clients.map(c => c.Nombre).filter(Boolean))].sort(), [clients]);
  const AVAILABLE_ESTADO = useMemo(() => [...new Set(clients.map(c => c.Estado).filter(Boolean))].sort(), [clients]);
  const AVAILABLE_MAIL = useMemo(() => [...new Set(clients.map(c => c.Mail).filter(Boolean))].sort(), [clients]);
  const AVAILABLE_TELEFONO = useMemo(() => [...new Set(clients.map(c => c["Teléfono"]).filter(Boolean))].sort(), [clients]);

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) return <span style={{ opacity: 0.3, marginLeft: '5px' }}>↕</span>;
    return <span style={{ marginLeft: '5px' }}>{sortConfig.direction === 'asc' ? '↑' : '↓'}</span>;
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
            onClick={() => setFilter({ CUIL: [], Documento: [], Apellido: [], Nombre: [], Estado: [], Mail: [], Teléfono: [] })}
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

      {isError && (
        <div style={{ padding: '20px', background: 'rgba(255,0,0,0.1)', color: 'red', border: '1px solid red', borderRadius: '4px', marginBottom: '16px' }}>
          <strong>Error de conexión con el servidor:</strong> {error?.message}
          <br />
          <small>Por favor, recargue la página o revise la consola.</small>
        </div>
      )}

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th onClick={() => handleSort('CUIL')} style={{ cursor: 'pointer', minWidth: '130px' }}>
                  CUIL <SortIcon columnKey="CUIL" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_CUIL} 
                      selectedOptions={filter.CUIL} 
                      onChange={val => setFilter({ ...filter, CUIL: val })} 
                      title="Filtrar CUIL..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Documento')} style={{ cursor: 'pointer', minWidth: '110px' }}>
                  Documento <SortIcon columnKey="Documento" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_DOCUMENTO} 
                      selectedOptions={filter.Documento} 
                      onChange={val => setFilter({ ...filter, Documento: val })} 
                      title="Filtrar Doc..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Apellido')} style={{ cursor: 'pointer', minWidth: '130px' }}>
                  Apellido <SortIcon columnKey="Apellido" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_APELLIDO} 
                      selectedOptions={filter.Apellido} 
                      onChange={val => setFilter({ ...filter, Apellido: val })} 
                      title="Filtrar Apellido..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Nombre')} style={{ cursor: 'pointer', minWidth: '130px' }}>
                  Nombre <SortIcon columnKey="Nombre" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_NOMBRE} 
                      selectedOptions={filter.Nombre} 
                      onChange={val => setFilter({ ...filter, Nombre: val })} 
                      title="Filtrar Nombre..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Estado')} style={{ cursor: 'pointer', minWidth: '120px' }}>
                  Estado <SortIcon columnKey="Estado" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_ESTADO} 
                      selectedOptions={filter.Estado} 
                      onChange={val => setFilter({ ...filter, Estado: val })} 
                      title="Filtrar Estado..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Mail')} style={{ cursor: 'pointer', minWidth: '150px' }}>
                  Email <SortIcon columnKey="Mail" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_MAIL} 
                      selectedOptions={filter.Mail} 
                      onChange={val => setFilter({ ...filter, Mail: val })} 
                      title="Filtrar Email..." 
                    />
                  </div>
                </th>
                <th onClick={() => handleSort('Teléfono')} style={{ cursor: 'pointer', minWidth: '120px' }}>
                  Teléfono <SortIcon columnKey="Teléfono" />
                  <div style={{ marginTop: '5px' }} onClick={e => e.stopPropagation()}>
                    <ExcelListFilter 
                      availableOptions={AVAILABLE_TELEFONO} 
                      selectedOptions={filter.Teléfono} 
                      onChange={val => setFilter({ ...filter, Teléfono: val })} 
                      title="Filtrar Tel..." 
                    />
                  </div>
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
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="8" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  TOTALES (Mostrando {filteredAndSortedClients.length} de {clients.length})
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
      
      {editCuil && <ClientEditModal cuil={editCuil} onClose={() => setEditCuil(null)} onSuccess={() => queryClient.invalidateQueries({ queryKey: ['clientes'] })} />}
      {ccCuil && <ClientCCModal cuil={ccCuil} clientName={clients.find(c => c.CUIL === ccCuil)?.["Apellido y Nombre"]} onClose={() => setCcCuil(null)} />}
      {viewClient && <ClientViewModal client={viewClient} onClose={() => setViewClient(null)} />}
    </section>
  );
};

export default ClientListPage;

