import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X } from 'lucide-react';
import ExcelListFilter from '../components/ExcelListFilter';
import ExcelNumberRangeFilter from '../components/ExcelNumberRangeFilter';

const MovimientosDeudaPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingMovimiento, setEditingMovimiento] = useState(null);
  const [viewTitularesMovimiento, setViewTitularesMovimiento] = useState(null);
  const [filters, setFilters] = useState({});

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Fetch Movimientos
  const { data, isLoading } = useQuery({
    queryKey: ['movimientos-deuda'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/movimientos', { params: { limit: 1000 } });
      return res.data;
    }
  });

  const movimientos = data?.items || [];
  
  const getMontoMultiplier = (tipo) => {
    switch (tipo) {
      case 'Suscripción': return 1;
      case 'Renovación suscripción': return 1;
      case 'Rescate': return -1;
      case 'Renovación rescate': return -1;
      case 'Vencimiento': return -1;
      case 'Retiro de intereses': return -1;
      default: return 1;
    }
  };

  const filteredMovimientos = movimientos.filter(m => {
    return Object.entries(filters).every(([key, filterValue]) => {
      if (!filterValue || (Array.isArray(filterValue) && filterValue.length === 0)) return true;
      
      if (key === 'monto') {
        if (filterValue.min === undefined && filterValue.max === undefined) return true;
        const val = Number(m.monto * getMontoMultiplier(m.tipo_movimiento));
        if (isNaN(val)) return false;
        if (filterValue.min !== undefined && val < filterValue.min) return false;
        if (filterValue.max !== undefined && val > filterValue.max) return false;
        return true;
      }
      
      let valStr = '';
      if (key === 'fecha') {
        valStr = new Date(m.fecha).toLocaleDateString();
      } else if (key === 'cuenta') {
        valStr = m.cuenta_externo ? `${m.cuenta_externo} (ID ${m.id_cuenta_comitente})` : `ID ${m.id_cuenta_comitente}`;
      } else if (key === 'serie') {
        valStr = m.tipo_movimiento === 'Renovación rescate' && m.id_serie_destino
          ? `${m.serie_name || `ID ${m.id_serie}`} ➔ ${m.serie_destino_name || `ID ${m.id_serie_destino}`}`
          : m.serie_name || `ID ${m.id_serie}`;
      } else if (key === 'tipo') {
        valStr = m.tipo_movimiento;
      } else {
        valStr = String(m[key] !== null && m[key] !== undefined ? m[key] : '');
      }
      
      return filterValue.includes(valStr);
    });
  });

  const getAvailableOptions = (key) => {
    if (!movimientos) return [];
    const options = new Set();
    movimientos.forEach(m => {
      let valStr = '';
      if (key === 'fecha') {
        valStr = new Date(m.fecha).toLocaleDateString();
      } else if (key === 'cuenta') {
        valStr = m.cuenta_externo ? `${m.cuenta_externo} (ID ${m.id_cuenta_comitente})` : `ID ${m.id_cuenta_comitente}`;
      } else if (key === 'serie') {
        valStr = m.tipo_movimiento === 'Renovación rescate' && m.id_serie_destino
          ? `${m.serie_name || `ID ${m.id_serie}`} ➔ ${m.serie_destino_name || `ID ${m.id_serie_destino}`}`
          : m.serie_name || `ID ${m.id_serie}`;
      } else if (key === 'tipo') {
        valStr = m.tipo_movimiento;
      } else if (key !== 'monto') {
        valStr = String(m[key] !== null && m[key] !== undefined ? m[key] : '');
      }
      if (valStr) options.add(valStr);
    });
    return Array.from(options).sort();
  };

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

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }) => {
      const res = await axiosClient.put(`/api/v1/inversores/movimientos/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['movimientos-deuda'] });
      setShowAddModal(false);
      setEditingMovimiento(null);
      alert('Movimiento actualizado con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al actualizar el movimiento');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const res = await axiosClient.delete(`/api/v1/inversores/movimientos/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['movimientos-deuda'] });
      alert('Movimiento eliminado con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al eliminar el movimiento');
    }
  });

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar este movimiento?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleEdit = (m) => {
    setEditingMovimiento(m);
    setShowAddModal(true);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(amount);
  };

  const getTipoBadge = (tipo) => {
    switch (tipo) {
      case 'Suscripción': 
      case 'Renovación suscripción':
        return <span className="status-badge status-activo">{tipo}</span>;
      case 'Rescate': 
      case 'Renovación rescate':
      case 'Retiro de intereses':
        return <span className="status-badge status-inactivo" style={{ background: 'var(--danger-color)' }}>{tipo}</span>;
      case 'Vencimiento': 
        return <span className="status-badge" style={{ background: 'var(--text-secondary)' }}>{tipo}</span>;
      default: return <span className="status-badge">{tipo}</span>;
    }
  };

  // getMontoMultiplier moved up

  const subtotal = filteredMovimientos.reduce((acc, m) => acc + (m.monto * getMontoMultiplier(m.tipo_movimiento)), 0);

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
                {[
                  { key: 'id', label: 'ID' },
                  { key: 'fecha', label: 'Fecha' },
                  { key: 'cuenta', label: 'Cuenta (Externa)' },
                  { key: 'serie', label: 'Serie' },
                  { key: 'tipo', label: 'Tipo de Movimiento' },
                  { key: 'monto', label: 'Monto' }
                ].map(col => (
                  <th key={col.key}>
                    <div style={{ marginBottom: '8px' }}>{col.label}</div>
                    {col.key === 'monto' ? (
                      <ExcelNumberRangeFilter
                        selectedRange={filters[col.key]}
                        onChange={(range) => handleFilterChange(col.key, range)}
                      />
                    ) : (
                      <ExcelListFilter
                        availableOptions={getAvailableOptions(col.key)}
                        selectedOptions={filters[col.key] || []}
                        onChange={(selected) => handleFilterChange(col.key, selected)}
                        title={`Filtrar ${col.label}`}
                      />
                    )}
                  </th>
                ))}
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : filteredMovimientos.length === 0 ? (
                <tr><td colSpan="7" style={{ textAlign: 'center', padding: '20px' }}>No se registraron movimientos.</td></tr>
              ) : (
                filteredMovimientos.map(m => (
                  <tr key={m.id}>
                    <td>{m.id}</td>
                    <td>{new Date(m.fecha).toLocaleDateString()}</td>
                    <td>{m.cuenta_externo ? `${m.cuenta_externo} (ID ${m.id_cuenta_comitente})` : `ID ${m.id_cuenta_comitente}`}</td>
                    <td>
                      {m.tipo_movimiento === 'Renovación rescate' && m.id_serie_destino 
                        ? `${m.serie_name || `ID ${m.id_serie}`} ➔ ${m.serie_destino_name || `ID ${m.id_serie_destino}`}`
                        : m.serie_name || `ID ${m.id_serie}`}
                    </td>
                    <td>{getTipoBadge(m.tipo_movimiento)}</td>
                    <td style={{ fontWeight: 'bold' }}>{formatCurrency(m.monto * getMontoMultiplier(m.tipo_movimiento))}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'nowrap', alignItems: 'center' }}>
                        {m.observaciones && (
                          <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px' }} onClick={() => alert(`Observación:\n\n${m.observaciones}`)} title="Ver Observación">💬</button>
                        )}
                        <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px' }} onClick={() => setViewTitularesMovimiento(m)} title="Ver Inversores">👥</button>
                        <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px' }} onClick={() => handleEdit(m)} title="Editar">✏️</button>
                        <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} onClick={() => handleDelete(m.id)} title="Eliminar">🗑️</button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="5" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Movimientos: {filteredMovimientos.length} | Subtotal:
                </td>
                <td style={{ fontWeight: 'bold', color: subtotal >= 0 ? 'var(--primary-color)' : 'var(--danger-color)' }}>
                  {formatCurrency(subtotal)}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {showAddModal && (
        <AddMovimientoModal 
          initialData={editingMovimiento}
          onClose={() => {
            setShowAddModal(false);
            setEditingMovimiento(null);
          }}
          onSubmit={(data) => {
            if (editingMovimiento) {
              updateMutation.mutate({ id: editingMovimiento.id, data });
            } else {
              addMutation.mutate(data);
            }
          }}
          isLoading={addMutation.isPending || updateMutation.isPending}
        />
      )}

      {viewTitularesMovimiento && (
        <div className="modal-overlay" style={{ animation: 'fadeIn 0.2s ease' }}>
          <div className="modal-content glass-panel" style={{ maxWidth: '600px', width: '90%' }}>
            <button onClick={() => setViewTitularesMovimiento(null)} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
              <X size={20} />
            </button>
            <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Inversores del Movimiento #{viewTitularesMovimiento.id}</h3>
            <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
              Cuenta Externa: {viewTitularesMovimiento.cuenta_externo || 'N/A'} (Interno: {viewTitularesMovimiento.id_cuenta_comitente})
            </p>
            
            {viewTitularesMovimiento.titulares && viewTitularesMovimiento.titulares.length > 0 ? (
              <table className="data-table" style={{ marginTop: '0' }}>
                <thead>
                  <tr>
                    <th>Orden</th>
                    <th>Razón Social</th>
                    <th>CUIT</th>
                  </tr>
                </thead>
                <tbody>
                  {viewTitularesMovimiento.titulares.map((t, idx) => (
                    <tr key={idx}>
                      <td>{t.orden}</td>
                      <td>{t.inversor_razon_social}</td>
                      <td>{t.inversor_cuit}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="empty-state" style={{ padding: '20px', textAlign: 'center' }}>
                No hay inversores asociados a esta cuenta.
              </div>
            )}
            
            <div className="modal-actions" style={{ marginTop: '24px', justifyContent: 'flex-end' }}>
              <button type="button" className="btn-primary" onClick={() => setViewTitularesMovimiento(null)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};

// Modal Component
const AddMovimientoModal = ({ initialData, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    id_cuenta_comitente: initialData?.id_cuenta_comitente || '',
    id_serie: initialData?.id_serie || '',
    id_serie_destino: initialData?.id_serie_destino || '',
    fecha: initialData?.fecha ? new Date(initialData.fecha).toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
    monto: initialData?.monto || '',
    tipo_movimiento: initialData?.tipo_movimiento || 'SUSCRIPCION',
    observaciones: initialData?.observaciones || ''
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
    const data = {
      id_cuenta_comitente: parseInt(formData.id_cuenta_comitente),
      id_serie: parseInt(formData.id_serie),
      fecha: new Date(formData.fecha).toISOString(), // FastAPI expects datetime
      monto: parseFloat(formData.monto),
      tipo_movimiento: formData.tipo_movimiento,
      observaciones: formData.observaciones || null
    };
    if (formData.tipo_movimiento === 'RENOVACION' && formData.id_serie_destino) {
      data.id_serie_destino = parseInt(formData.id_serie_destino);
    }
    onSubmit(data);
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
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>{initialData ? 'Editar Movimiento' : 'Registrar Movimiento'}</h3>
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
                <option key={cta.id} value={cta.id}>ID Externo: {cta.id_externo} {cta.conjunta ? '(Conjunta)' : '(Indistinta)'}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>{formData.tipo_movimiento === 'RENOVACION' ? 'Serie de Salida (vence) *' : 'Serie *'}</label>
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

          {formData.tipo_movimiento === 'RENOVACION' && (
            <div className="form-group">
              <label>Serie de Entrada (suscribe) *</label>
              <select 
                required 
                value={formData.id_serie_destino} 
                onChange={(e) => setFormData({...formData, id_serie_destino: e.target.value})}
                style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-color)' }}
              >
                <option value="">-- Seleccionar Serie --</option>
                {seriesData?.map(s => (
                  <option key={s.id} value={s.id}>{s.name} (TNA: {s.tna}%)</option>
                ))}
              </select>
            </div>
          )}

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
              <option value="RETIRO_INTERESES">Retiro de intereses</option>
              <option value="RENOVACION">Renovación</option>
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
          
          <div className="form-group">
            <label>Observaciones</label>
            <textarea 
              value={formData.observaciones} 
              onChange={e => setFormData({...formData, observaciones: e.target.value})} 
              placeholder="Opcional..."
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-color)', minHeight: '60px' }}
            />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? (initialData ? 'Actualizando...' : 'Registrando...') : (initialData ? 'Actualizar' : 'Registrar')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MovimientosDeudaPage;
