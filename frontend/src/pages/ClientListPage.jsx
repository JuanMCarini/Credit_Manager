import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import ClientEditModal from '../components/ClientEditModal';
import ClientCCModal from '../components/ClientCCModal';

const ClientListPage = () => {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState({ CUIL: '', Documento: '', Apellido: '', Nombre: '', Estado: [], Mail: '', Teléfono: '' });
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [showEstadoFilter, setShowEstadoFilter] = useState(false);

  const ESTADOS_DISPONIBLES = ['ACTIVO', 'INACTIVO', 'MOROSO', 'INCOBRABLE'];

  const [editCuil, setEditCuil] = useState(null);
  const [ccCuil, setCcCuil] = useState(null);
  const navigate = useNavigate();

  const fetchClients = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get('/api/v1/clientes');
      setClients(res.data);
    } catch (error) {
      alert("Error cargando clientes: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClients();
  }, []);

  const handleDelete = async (cuil) => {
    if (!window.confirm(`¿Está seguro que desea eliminar al cliente con CUIL ${cuil}?`)) return;
    try {
      await axiosClient.delete(`/api/v1/clientes/${cuil}`);
      alert('Cliente eliminado con éxito.');
      fetchClients();
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

    // Filter
    if (filter.CUIL) result = result.filter(c => c.CUIL.includes(filter.CUIL));
    if (filter.Documento) result = result.filter(c => c.Documento.includes(filter.Documento));
    if (filter.Apellido) result = result.filter(c => c.Apellido && c.Apellido.toLowerCase().includes(filter.Apellido.toLowerCase()));
    if (filter.Nombre) result = result.filter(c => c.Nombre && c.Nombre.toLowerCase().includes(filter.Nombre.toLowerCase()));
    if (filter.Estado.length > 0) result = result.filter(c => filter.Estado.includes(c.Estado));
    if (filter.Mail) result = result.filter(c => c.Mail && c.Mail.toLowerCase().includes(filter.Mail.toLowerCase()));
    if (filter.Teléfono) result = result.filter(c => c["Teléfono"] && c["Teléfono"].toLowerCase().includes(filter.Teléfono.toLowerCase()));

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
        <button className="btn-primary" onClick={fetchClients} disabled={loading} style={{ width: 'auto' }}>
          {loading ? "Actualizando..." : "Actualizar Datos"}
        </button>
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
                <th onClick={() => handleSort('Estado')} style={{ cursor: 'pointer', position: 'relative' }}>
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
                        <button className="btn-secondary" onClick={() => navigate(`/creditos?cuil=${c.CUIL}`)} style={{ padding: '4px 8px', fontSize: '11px' }}>💳 Créditos</button>
                        <button className="btn-secondary" onClick={() => setCcCuil(c.CUIL)} style={{ padding: '4px 8px', fontSize: '11px' }}>👁️ CC</button>
                        <button className="btn-secondary" onClick={() => setEditCuil(c.CUIL)} style={{ padding: '4px 8px', fontSize: '11px' }}>✏️ Editar</button>
                        <button className="btn-secondary" onClick={() => handleDelete(c.CUIL)} style={{ padding: '4px 8px', fontSize: '11px', color: 'var(--error)' }}>🗑️</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
      {editCuil && <ClientEditModal cuil={editCuil} onClose={() => setEditCuil(null)} onSuccess={fetchClients} />}
      {ccCuil && <ClientCCModal cuil={ccCuil} clientName={clients.find(c => c.CUIL === ccCuil)?.["Apellido y Nombre"]} onClose={() => setCcCuil(null)} />}
    </section>
  );
};

export default ClientListPage;
