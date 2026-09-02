import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X, Trash2, Edit2 } from 'lucide-react';
import ExcelListFilter from '../components/ExcelListFilter';

const CuentasComitentesPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editCuenta, setEditCuenta] = useState(null);
  const [showEstadoCuenta, setShowEstadoCuenta] = useState(null);
  const [filters, setFilters] = useState({});

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Fetch Cuentas
  const { data, isLoading } = useQuery({
    queryKey: ['cuentas-comitentes'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/cuentas', { params: { limit: 1000 } });
      return res.data;
    }
  });

  const cuentas = data?.items || [];
  
  const filteredCuentas = (cuentas || []).filter(cta => {
    return Object.entries(filters).every(([key, filterValue]) => {
      if (!filterValue || filterValue.length === 0) return true;
      let valStr = '';
      if (key === 'tipo') {
        valStr = cta.conjunta ? 'Conjunta' : 'Indistinta';
      } else if (key === 'titulares') {
        valStr = cta.titulares && cta.titulares.length > 0 
          ? cta.titulares.map(t => `${t.inversor_razon_social} ${t.inversor_cuit}`).join(' ') 
          : 'Sin titulares asignados';
      } else if (key === 'fecha') {
        valStr = new Date(cta.created_at).toLocaleDateString();
      } else {
        valStr = String(cta[key] !== null && cta[key] !== undefined ? cta[key] : '');
      }
      return filterValue.includes(valStr);
    });
  });

  const getAvailableOptions = (key) => {
    if (!cuentas) return [];
    if (key === 'tipo') return ['Conjunta', 'Indistinta'];
    
    const options = new Set();
    cuentas.forEach(cta => {
      let valStr = '';
      if (key === 'titulares') {
        valStr = cta.titulares && cta.titulares.length > 0
          ? cta.titulares.map(t => `${t.inversor_razon_social} ${t.inversor_cuit}`).join(' ')
          : 'Sin titulares asignados';
      } else if (key === 'fecha') {
        valStr = new Date(cta.created_at).toLocaleDateString();
      } else {
        valStr = String(cta[key] !== null && cta[key] !== undefined ? cta[key] : '');
      }
      if (valStr) options.add(valStr);
    });
    return Array.from(options).sort();
  };

  // Add Mutation
  const addMutation = useMutation({
    mutationFn: async (nuevaCuenta) => {
      const res = await axiosClient.post('/api/v1/inversores/cuentas', nuevaCuenta);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cuentas-comitentes'] });
      setShowAddModal(false);
      alert('Cuenta Comitente creada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al crear la cuenta comitente');
    }
  });

  // Edit Mutation
  const editMutation = useMutation({
    mutationFn: async (updatedCuenta) => {
      const res = await axiosClient.put(`/api/v1/inversores/cuentas/${updatedCuenta.id}`, updatedCuenta);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cuentas-comitentes'] });
      setEditCuenta(null);
      alert('Cuenta Comitente actualizada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al actualizar la cuenta comitente');
    }
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const res = await axiosClient.delete(`/api/v1/inversores/cuentas/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cuentas-comitentes'] });
      alert('Cuenta Comitente eliminada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al eliminar la cuenta comitente');
    }
  });

  const handleDelete = (id) => {
    if (window.confirm('¿Está seguro de eliminar esta cuenta comitente?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Cuentas Comitentes</h2>
          <p>Gestione las cuentas en el mercado y sus inversores titulares.</p>
        </div>
        <div>
          <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Nueva Cuenta
          </button>
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                {[
                  { key: 'id', label: 'ID Interno' },
                  { key: 'id_externo', label: 'ID Externo' },
                  { key: 'tipo', label: 'Tipo' },
                  { key: 'titulares', label: 'Titulares (Inversores)' },
                  { key: 'fecha', label: 'Fecha de Alta' }
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
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : filteredCuentas.length === 0 ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron cuentas comitentes.</td></tr>
              ) : (
                filteredCuentas.map(cta => (
                  <tr key={cta.id}>
                    <td>{cta.id}</td>
                    <td>{cta.id_externo}</td>
                    <td>{cta.conjunta ? 'Conjunta' : 'Indistinta'}</td>
                    <td>
                      {cta.titulares && cta.titulares.length > 0 ? (
                        <ul style={{ margin: 0, paddingLeft: '15px' }}>
                          {cta.titulares.map(t => (
                            <li key={t.inversor_id}>{t.inversor_razon_social} (CUIT: {t.inversor_cuit})</li>
                          ))}
                        </ul>
                      ) : (
                        <span style={{ color: 'var(--text-secondary)' }}>Sin titulares asignados</span>
                      )}
                    </td>
                    <td>{new Date(cta.created_at).toLocaleDateString()}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button className="btn-secondary" onClick={() => setShowEstadoCuenta(cta.id)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Ver Estado de Cuenta">
                          👁️
                        </button>
                        <button className="btn-secondary" onClick={() => setEditCuenta(cta)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Editar">
                          ✏️
                        </button>
                        <button className="btn-secondary" onClick={() => handleDelete(cta.id)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="6" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Cuentas: {filteredCuentas.length}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {showAddModal && (
        <AddCuentaModal 
          onClose={() => setShowAddModal(false)}
          onSubmit={(data) => addMutation.mutate(data)}
          isLoading={addMutation.isPending}
        />
      )}

      {editCuenta && (
        <AddCuentaModal 
          initialData={editCuenta}
          onClose={() => setEditCuenta(null)}
          onSubmit={(data) => editMutation.mutate({ ...data, id: editCuenta.id })}
          isLoading={editMutation.isPending}
        />
      )}

      {showEstadoCuenta && (
        <EstadoCuentaModal
          cuentaId={showEstadoCuenta}
          onClose={() => setShowEstadoCuenta(null)}
        />
      )}
    </section>
  );
};

// Modal Component
const AddCuentaModal = ({ initialData, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState(() => {
    if (initialData) {
      return {
        id_externo: initialData.id_externo,
        conjunta: initialData.conjunta,
        titulares: (initialData.titulares || []).map(t => ({
          id_inversor: t.inversor_id,
          orden: t.orden,
          activo: true
        }))
      };
    }
    return {
      id_externo: '',
      conjunta: false,
      titulares: [] // { id_inversor, orden, activo }
    };
  });

  // Fetch Inversores para el selector
  const { data: inversoresData } = useQuery({
    queryKey: ['inversores-list'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores', { params: { limit: 1000 } });
      return res.data.items || [];
    }
  });

  const handleAddTitular = () => {
    setFormData({
      ...formData,
      titulares: [...formData.titulares, { id_inversor: '', orden: formData.titulares.length + 1, activo: true }]
    });
  };

  const handleRemoveTitular = (index) => {
    const updated = formData.titulares.filter((_, i) => i !== index);
    // Reordenar
    updated.forEach((t, i) => t.orden = i + 1);
    setFormData({ ...formData, titulares: updated });
  };

  const handleTitularChange = (index, field, value) => {
    const updated = [...formData.titulares];
    updated[index][field] = value;
    setFormData({ ...formData, titulares: updated });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.id_externo) {
      alert("El ID Externo es obligatorio.");
      return;
    }
    // Validar titulares
    if (formData.titulares.some(t => !t.id_inversor)) {
      alert("Por favor seleccione un inversor para todos los titulares o elimine el titular vacío.");
      return;
    }
    
    onSubmit({
      id_externo: formData.id_externo,
      conjunta: formData.conjunta,
      titulares: formData.titulares.map(t => ({
        id_inversor: parseInt(t.id_inversor),
        orden: t.orden,
        activo: t.activo
      }))
    });
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '600px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>{initialData ? 'Editar Cuenta Comitente' : 'Nueva Cuenta Comitente'}</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div className="form-group">
            <label>ID Externo *</label>
            <input 
              type="text" 
              required 
              value={formData.id_externo} 
              onChange={e => setFormData({...formData, id_externo: e.target.value})} 
            />
          </div>
          
          <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input 
              type="checkbox" 
              id="conjunta" 
              checked={formData.conjunta} 
              onChange={e => setFormData({...formData, conjunta: e.target.checked})} 
            />
            <label htmlFor="conjunta" style={{ margin: 0 }}>Cuenta Conjunta (Múltiples titulares)</label>
          </div>

          <div style={{ borderTop: '1px solid var(--border-color)', margin: '10px 0', paddingTop: '10px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <h4 style={{ margin: 0 }}>Titulares (Inversores asignados)</h4>
              <button type="button" className="btn-secondary" onClick={handleAddTitular} style={{ padding: '4px 8px', fontSize: '0.85em' }}>
                <Plus size={14} /> Añadir Titular
              </button>
            </div>
            
            {formData.titulares.length === 0 ? (
              <p style={{ fontSize: '0.85em', color: 'var(--text-secondary)' }}>No hay titulares asignados. Se creará una cuenta vacía.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {formData.titulares.map((t, index) => (
                  <div key={index} style={{ display: 'flex', gap: '10px', alignItems: 'center', background: 'var(--bg-color)', padding: '10px', borderRadius: '4px' }}>
                    <div className="form-group" style={{ flex: 1, margin: 0 }}>
                      <select 
                        required 
                        value={t.id_inversor} 
                        onChange={(e) => handleTitularChange(index, 'id_inversor', e.target.value)}
                        style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--surface-color)', color: 'var(--text-color)' }}
                      >
                        <option value="">-- Seleccionar Inversor --</option>
                        {inversoresData?.map(inv => (
                          <option key={inv.id} value={inv.id}>{inv.razon_social} (CUIT: {inv.cuit})</option>
                        ))}
                      </select>
                    </div>
                    <button type="button" onClick={() => handleRemoveTitular(index)} style={{ background: 'none', border: 'none', color: 'var(--danger-color)', cursor: 'pointer' }} title="Eliminar titular">
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Crear Cuenta Comitente'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Modal Component para Estado de Cuenta
const EstadoCuentaModal = ({ cuentaId, onClose }) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['estado-cuenta', cuentaId],
    queryFn: async () => {
      const res = await axiosClient.get(`/api/v1/inversores/cuentas/${cuentaId}/estado`);
      return res.data;
    }
  });

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '-';
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(value);
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '1000px', maxWidth: '95%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>
          Estado de Cuenta #{cuentaId}
          {data && data.inversores && data.inversores.length > 0 && ` (Externo: ${data.inversores[0]["ID Externo"]})`}
        </h3>
        
        {isLoading && <p>Cargando datos...</p>}
        {error && <p style={{color: 'var(--danger-color)'}}>Error al cargar el estado de cuenta: {error.response?.data?.detail || error.message}</p>}
        
        {data && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
            {/* INVERSORES */}
            <div>
              <h4 style={{ marginBottom: '10px' }}>Datos de los Inversores</h4>
              <div className="table-responsive">
                <table className="data-table" style={{ fontSize: '13px' }}>
                  <thead>
                    <tr>
                      <th>ID Inversor</th>
                      <th>Orden</th>
                      <th>Nombre Inversor</th>
                      <th>CUIL/CUIT</th>
                      <th>Domicilio</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.inversores.map((inv, idx) => (
                      <tr key={idx}>
                        <td>{inv["ID Inversor"]}</td>
                        <td>{inv["Orden"]}</td>
                        <td>{inv["Nombre Inversor"]}</td>
                        <td>{inv["CUIL/CUIT"]}</td>
                        <td>{inv["Domicilio"]}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* MOVIMIENTOS */}
            <div>
              <h4 style={{ marginBottom: '10px' }}>Movimientos y Saldos</h4>
              <div className="table-responsive">
                <table className="data-table" style={{ fontSize: '13px' }}>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Serie</th>
                      <th>Fecha Susc.</th>
                      <th>Vencimiento</th>
                      <th>Fecha Mov.</th>
                      <th>Inversores</th>
                      <th>Tipo</th>
                      <th style={{textAlign: 'right'}}>Capital</th>
                      <th style={{textAlign: 'right'}}>Interés</th>
                      <th style={{textAlign: 'right'}}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.movimientos.map((mov, idx) => (
                      <tr key={idx}>
                        <td>{mov["ID"]}</td>
                        <td>{mov["Serie"]}</td>
                        <td>{mov["Fecha Suscripción"]}</td>
                        <td>{mov["Fecha Vencimiento"]}</td>
                        <td>{mov["Fecha"]}</td>
                        <td>{mov["Inversores"]}</td>
                        <td>{mov["Tipo Movimiento"]}</td>
                        <td style={{textAlign: 'right'}}>{formatCurrency(mov["Capital"])}</td>
                        <td style={{textAlign: 'right'}}>{formatCurrency(mov["Interés"])}</td>
                        <td style={{textAlign: 'right', fontWeight: 'bold'}}>{formatCurrency(mov["Total"])}</td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr style={{ fontWeight: 'bold', backgroundColor: 'var(--bg-color)' }}>
                      <td colSpan="7" style={{textAlign: 'right'}}>Subtotales:</td>
                      <td style={{textAlign: 'right'}}>{formatCurrency(data.movimientos.reduce((sum, mov) => sum + (mov["Capital"] || 0), 0))}</td>
                      <td style={{textAlign: 'right'}}>{formatCurrency(data.movimientos.reduce((sum, mov) => sum + (mov["Interés"] || 0), 0))}</td>
                      <td style={{textAlign: 'right'}}>{formatCurrency(data.movimientos.reduce((sum, mov) => sum + (mov["Total"] || 0), 0))}</td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CuentasComitentesPage;
