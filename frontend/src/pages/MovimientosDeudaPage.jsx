import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X } from 'lucide-react';

const MovimientosDeudaPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);

  // Fetch Movimientos
  const { data, isLoading } = useQuery({
    queryKey: ['movimientos-deuda'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/movimientos');
      return res.data;
    }
  });

  const movimientos = data?.items || [];
  const total = data?.total || 0;

  // Add Mutation
  const addMutation = useMutation({
    mutationFn: async (nuevoMovimiento) => {
      const res = await axiosClient.post('/api/v1/inversores/movimientos', nuevoMovimiento);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['movimientos-deuda'] });
      setShowAddModal(false);
      alert('Movimiento registrado con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al registrar el movimiento');
    }
  });

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(amount);
  };

  const getTipoBadge = (tipo) => {
    switch (tipo) {
      case 'SUSCRIPCION': return <span className="status-badge status-activo">Suscripción</span>;
      case 'RESCATE': return <span className="status-badge status-inactivo" style={{ background: 'var(--danger-color)' }}>Rescate</span>;
      case 'VENCIMIENTO': return <span className="status-badge" style={{ background: 'var(--text-secondary)' }}>Vencimiento</span>;
      default: return tipo;
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Movimientos de Deuda</h2>
          <p>Gestione suscripciones, rescates y vencimientos de las cuentas comitentes.</p>
        </div>
        <div>
          <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Registrar Movimiento
          </button>
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Fecha</th>
                <th>Cuenta (BCBB)</th>
                <th>Serie</th>
                <th>Tipo de Movimiento</th>
                <th>Monto</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : movimientos.length === 0 ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>No se registraron movimientos.</td></tr>
              ) : (
                movimientos.map(m => (
                  <tr key={m.id}>
                    <td>{m.id}</td>
                    <td>{new Date(m.fecha).toLocaleDateString()}</td>
                    <td>{m.cuenta_bcbb ? `Cta ${m.cuenta_bcbb}` : `ID ${m.id_cuenta_comitente}`}</td>
                    <td>{m.serie_name || `ID ${m.id_serie}`}</td>
                    <td>{getTipoBadge(m.tipo_movimiento)}</td>
                    <td style={{ fontWeight: 'bold' }}>{formatCurrency(m.monto)}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="6" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Movimientos: {total}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {showAddModal && (
        <AddMovimientoModal 
          onClose={() => setShowAddModal(false)}
          onSubmit={(data) => addMutation.mutate(data)}
          isLoading={addMutation.isPending}
        />
      )}
    </section>
  );
};

// Modal Component
const AddMovimientoModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    id_cuenta_comitente: '',
    id_serie: '',
    fecha: new Date().toISOString().split('T')[0], // YYYY-MM-DD
    monto: '',
    tipo_movimiento: 'SUSCRIPCION'
  });

  // Fetch Cuentas
  const { data: cuentasData } = useQuery({
    queryKey: ['cuentas-list'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/cuentas', { params: { limit: 1000 } });
      return res.data.items || [];
    }
  });

  // Fetch Series
  const { data: seriesData } = useQuery({
    queryKey: ['series-list'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/series', { params: { limit: 1000 } });
      return res.data.items || [];
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      id_cuenta_comitente: parseInt(formData.id_cuenta_comitente),
      id_serie: parseInt(formData.id_serie),
      fecha: new Date(formData.fecha).toISOString(), // FastAPI expects datetime
      monto: parseFloat(formData.monto),
      tipo_movimiento: formData.tipo_movimiento
    });
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
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Registrar Movimiento</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div className="form-group">
            <label>Cuenta Comitente *</label>
            <select 
              required 
              value={formData.id_cuenta_comitente} 
              onChange={(e) => setFormData({...formData, id_cuenta_comitente: e.target.value})}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-color)' }}
            >
              <option value="">-- Seleccionar Cuenta --</option>
              {cuentasData?.map(cta => (
                <option key={cta.id} value={cta.id}>BCBB: {cta.id_bcbb} {cta.conjunta ? '(Conjunta)' : '(Individual)'}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Serie *</label>
            <select 
              required 
              value={formData.id_serie} 
              onChange={(e) => setFormData({...formData, id_serie: e.target.value})}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-color)' }}
            >
              <option value="">-- Seleccionar Serie --</option>
              {seriesData?.map(s => (
                <option key={s.id} value={s.id}>{s.name} (TNA: {s.tna}%)</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Tipo de Movimiento *</label>
            <select 
              required 
              value={formData.tipo_movimiento} 
              onChange={(e) => setFormData({...formData, tipo_movimiento: e.target.value})}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-color)' }}
            >
              <option value="SUSCRIPCION">Suscripción</option>
              <option value="RESCATE">Rescate</option>
              <option value="VENCIMIENTO">Vencimiento</option>
            </select>
          </div>

          <div className="form-group">
            <label>Fecha *</label>
            <input 
              type="date" 
              required 
              value={formData.fecha} 
              onChange={e => setFormData({...formData, fecha: e.target.value})} 
            />
          </div>

          <div className="form-group">
            <label>Monto *</label>
            <input 
              type="number" 
              required 
              step="0.01"
              min="0.01"
              value={formData.monto} 
              onChange={e => setFormData({...formData, monto: e.target.value})} 
              placeholder="Ej. 1000000.00"
            />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Registrando...' : 'Registrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MovimientosDeudaPage;
