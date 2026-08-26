import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X, Search, Trash2 } from 'lucide-react';
import { useDebounce } from '../hooks/useDebounce';

const InversoresPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearch = useDebounce(searchTerm, 500);

  // Fetch Inversores
  const { data, isLoading } = useQuery({
    queryKey: ['inversores', debouncedSearch],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores', { params: { search: debouncedSearch } });
      return res.data;
    }
  });

  const inversores = data?.items || [];
  const total = data?.total || 0;

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
          <div className="search-bar" style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-secondary)' }} />
            <input 
              type="text" 
              placeholder="Buscar por CUIT o Razón Social..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ paddingLeft: '32px', width: '250px' }}
            />
          </div>
          <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Nuevo Inversor
          </button>
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>CUIT</th>
                <th>Razón Social</th>
                <th>Email</th>
                <th>Teléfono</th>
                <th>Banco</th>
                <th>Estado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : inversores.length === 0 ? (
                <tr><td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron inversores.</td></tr>
              ) : (
                inversores.map(inv => (
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
                    <td>
                      <button className="btn-secondary" onClick={() => handleDelete(inv.id)} style={{ padding: '4px', color: 'var(--danger-color)' }} title="Eliminar">
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="8" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Inversores: {total}
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
    </section>
  );
};

// Modal Component
const AddInversorModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
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
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Nuevo Inversor</h3>
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
