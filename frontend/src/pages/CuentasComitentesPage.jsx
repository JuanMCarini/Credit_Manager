import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X, Trash2 } from 'lucide-react';

const CuentasComitentesPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);

  // Fetch Cuentas
  const { data, isLoading } = useQuery({
    queryKey: ['cuentas-comitentes'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/cuentas');
      return res.data;
    }
  });

  const cuentas = data?.items || [];
  const total = data?.total || 0;

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

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Cuentas Comitentes</h2>
          <p>Gestione las cuentas en el mercado (BCBB) y sus inversores titulares.</p>
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
                <th>ID Interno</th>
                <th>ID BCBB</th>
                <th>Tipo</th>
                <th>Titulares (Inversores)</th>
                <th>Fecha de Alta</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : cuentas.length === 0 ? (
                <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron cuentas comitentes.</td></tr>
              ) : (
                cuentas.map(cta => (
                  <tr key={cta.id}>
                    <td>{cta.id}</td>
                    <td>{cta.id_bcbb}</td>
                    <td>{cta.conjunta ? 'Conjunta' : 'Individual'}</td>
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
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="5" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Cuentas: {total}
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
    </section>
  );
};

// Modal Component
const AddCuentaModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    id_bcbb: '',
    conjunta: false,
    titulares: [] // { id_inversor, orden, activo }
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
    if (!formData.id_bcbb) {
      alert("El ID BCBB es obligatorio.");
      return;
    }
    // Validar titulares
    if (formData.titulares.some(t => !t.id_inversor)) {
      alert("Por favor seleccione un inversor para todos los titulares o elimine el titular vacío.");
      return;
    }
    
    onSubmit({
      id_bcbb: parseInt(formData.id_bcbb),
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
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Nueva Cuenta Comitente</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div className="form-group">
            <label>ID BCBB *</label>
            <input 
              type="number" 
              required 
              value={formData.id_bcbb} 
              onChange={e => setFormData({...formData, id_bcbb: e.target.value})} 
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

export default CuentasComitentesPage;
