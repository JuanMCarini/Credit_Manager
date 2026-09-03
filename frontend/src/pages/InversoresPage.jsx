import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X, Search, Trash2, Edit2 } from 'lucide-react';
import ExcelListFilter from '../components/ExcelListFilter';
import { useAuthStore } from '../store/useAuthStore';

const InversoresPage = () => {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const isAuditor = user?.rol === 'Auditor / Solo Lectura';
  const [showAddModal, setShowAddModal] = useState(false);
  const [editInversor, setEditInversor] = useState(null);
  const [filters, setFilters] = useState({});

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Fetch Inversores
  const { data, isLoading } = useQuery({
    queryKey: ['inversores'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores', { params: { limit: 1000 } });
      return res.data;
    }
  });

  const inversores = data?.items || [];
  
  const filteredInversores = useMemo(() => {
    if (!inversores) return [];
    return inversores.filter(inv => {
      return Object.entries(filters).every(([key, filterValue]) => {
        if (!filterValue || filterValue.length === 0) return true;
        let valStr = '';
        if (key === 'estado') {
          valStr = inv.activo ? 'Activo' : 'Inactivo';
        } else {
          valStr = String(inv[key] !== null && inv[key] !== undefined ? inv[key] : '');
        }
        return filterValue.includes(valStr);
      });
    });
  }, [inversores, filters]);

  const getAvailableOptions = (key) => {
    if (!inversores) return [];
    if (key === 'estado') return ['Activo', 'Inactivo'];
    const options = new Set(inversores.map(inv => String(inv[key] !== null && inv[key] !== undefined ? inv[key] : '')));
    return Array.from(options).filter(Boolean).sort();
  };

  // Add Inversor Mutation
  const addMutation = useMutation({
    mutationFn: async (newInversor) => {
      const res = await axiosClient.post('/api/v1/inversores', newInversor);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inversores'] });
      setShowAddModal(false);
      alert('Inversor creado con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al crear inversor');
    }
  });

  // Edit Inversor Mutation
  const editMutation = useMutation({
    mutationFn: async (updatedInversor) => {
      const res = await axiosClient.put(`/api/v1/inversores/${updatedInversor.id}`, updatedInversor);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inversores'] });
      setEditInversor(null);
      alert('Inversor actualizado con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al actualizar inversor');
    }
  });

  // Delete Inversor Mutation
  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const res = await axiosClient.delete(`/api/v1/inversores/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inversores'] });
      alert('Inversor eliminado con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al eliminar inversor');
    }
  });

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar este inversor?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Listado de Inversores</h2>
          <p>Gestione los inversores que participan en el financiamiento.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {!isAuditor && (
            <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Plus size={16} /> Nuevo Inversor
            </button>
          )}
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                {[
                  { key: 'id', label: 'ID' },
                  { key: 'cuit', label: 'CUIT' },
                  { key: 'razon_social', label: 'Razón Social' },
                  { key: 'mail', label: 'Email' },
                  { key: 'telefono', label: 'Teléfono' },
                  { key: 'nombre_banco', label: 'Banco' },
                  { key: 'estado', label: 'Estado' }
                ].map(col => (
                  <th key={col.key}>
                    <div style={{ marginBottom: '8px' }}>{col.label}</div>
                    <ExcelListFilter
                      availableOptions={getAvailableOptions(col.key)}
                      selectedOptions={filters[col.key] || []}
                      onChange={(selected) => handleFilterChange(col.key, selected)}
                      title={`Filtrar ${col.label}`}
                    />
                  </th>
                ))}
                {!isAuditor && <th>Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : filteredInversores.length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron inversores.</td></tr>
              ) : (
                filteredInversores.map(inv => (
                  <tr key={inv.id}>
                    <td>{inv.id}</td>
                    <td>{inv.cuit}</td>
                    <td>{inv.razon_social}</td>
                    <td>{inv.mail || '-'}</td>
                    <td>{inv.telefono || '-'}</td>
                    <td>{inv.nombre_banco || '-'}</td>
                    <td>
                      <span className={`status-badge ${inv.activo ? 'status-activo' : 'status-inactivo'}`}>
                        {inv.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </td>
                    {!isAuditor && (
                      <td>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button className="btn-secondary" onClick={() => setEditInversor(inv)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar">
                            ✏️
                          </button>
                          <button className="btn-secondary" onClick={() => handleDelete(inv.id)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                            🗑️
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={isAuditor ? "7" : "8"} style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Inversores: {filteredInversores.length}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {showAddModal && (
        <AddInversorModal 
          onClose={() => setShowAddModal(false)}
          onSubmit={(data) => addMutation.mutate(data)}
          isLoading={addMutation.isPending}
        />
      )}

      {editInversor && (
        <AddInversorModal 
          initialData={editInversor}
          onClose={() => setEditInversor(null)}
          onSubmit={(data) => editMutation.mutate({ ...data, id: editInversor.id })}
          isLoading={editMutation.isPending}
        />
      )}
    </section>
  );
};

// Modal Component
const AddInversorModal = ({ initialData, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState(initialData || {
    cuit: '',
    razon_social: '',
    domicilio_legal: '',
    mail: '',
    telefono: '',
    cbu: '',
    nro_cuenta_bancaria: '',
    nombre_banco: '',
    activo: true
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

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
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>{initialData ? 'Editar Inversor' : 'Nuevo Inversor'}</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label>CUIT *</label>
            <input type="text" required maxLength="11" value={formData.cuit} onChange={e => setFormData({...formData, cuit: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Razón Social *</label>
            <input type="text" required value={formData.razon_social} onChange={e => setFormData({...formData, razon_social: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Domicilio Legal</label>
            <input type="text" value={formData.domicilio_legal} onChange={e => setFormData({...formData, domicilio_legal: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={formData.mail} onChange={e => setFormData({...formData, mail: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Teléfono</label>
            <input type="text" value={formData.telefono} onChange={e => setFormData({...formData, telefono: e.target.value})} />
          </div>
          <h4 style={{ margin: '10px 0 0 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '5px' }}>Datos Bancarios</h4>
          <div className="form-group">
            <label>CBU</label>
            <input type="text" value={formData.cbu} onChange={e => setFormData({...formData, cbu: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Nombre del Banco</label>
            <input type="text" value={formData.nombre_banco} onChange={e => setFormData({...formData, nombre_banco: e.target.value})} />
          </div>
          <div className="form-group">
            <label>Nro. Cuenta Bancaria</label>
            <input type="text" value={formData.nro_cuenta_bancaria} onChange={e => setFormData({...formData, nro_cuenta_bancaria: e.target.value})} />
          </div>
          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
            <input type="checkbox" id="activo" checked={formData.activo} onChange={e => setFormData({...formData, activo: e.target.checked})} />
            <label htmlFor="activo" style={{ margin: 0 }}>Inversor Activo</label>
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Guardar Inversor'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default InversoresPage;
