import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X } from 'lucide-react';

const SeriesPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);

  // Fetch Series
  const { data, isLoading } = useQuery({
    queryKey: ['series-deuda'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/series');
      return res.data;
    }
  });

  const series = data?.items || [];
  const total = data?.total || 0;

  // Add Mutation
  const addMutation = useMutation({
    mutationFn: async (nuevaSerie) => {
      const res = await axiosClient.post('/api/v1/inversores/series', nuevaSerie);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
      setShowAddModal(false);
      alert('Serie creada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al crear la serie');
    }
  });

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h2>Series de Deuda</h2>
          <p>Gestione las series emitidas para suscripción de los inversores.</p>
        </div>
        <div>
          <button className="btn-primary" onClick={() => setShowAddModal(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Plus size={16} /> Nueva Serie
          </button>
        </div>
      </header>

      <div className="results-container glass-panel">
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Nombre</th>
                <th>Fecha de Suscripción</th>
                <th>TNA (%)</th>
                <th>Plazo (días)</th>
                <th>Fecha Vencimiento</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : series.length === 0 ? (
                <tr><td colSpan="6" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron series.</td></tr>
              ) : (
                series.map(s => (
                  <tr key={s.id}>
                    <td>{s.id}</td>
                    <td><strong>{s.name}</strong></td>
                    <td>{new Date(s.fecha_suscripcion).toLocaleDateString()}</td>
                    <td>{s.tna}%</td>
                    <td>{s.plazo}</td>
                    <td>{new Date(s.fecha_vencimiento).toLocaleDateString()}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="6" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Total Series: {total}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {showAddModal && (
        <AddSerieModal 
          onClose={() => setShowAddModal(false)}
          onSubmit={(data) => addMutation.mutate(data)}
          isLoading={addMutation.isPending}
        />
      )}
    </section>
  );
};

// Modal Component
const AddSerieModal = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    fecha_suscripcion: '',
    tna: '',
    plazo: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      name: formData.name,
      fecha_suscripcion: formData.fecha_suscripcion,
      tna: parseFloat(formData.tna),
      plazo: parseInt(formData.plazo, 10)
    });
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', justifyContent: 'center', alignItems: 'center'
    }}>
      <div className="glass-panel" style={{ width: '400px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '24px', position: 'relative' }}>
        <button onClick={onClose} style={{ position: 'absolute', top: '16px', right: '16px', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-color)' }}>
          <X size={20} />
        </button>
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Nueva Serie de Deuda</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div className="form-group">
            <label>Nombre de la Serie *</label>
            <input 
              type="text" 
              required 
              maxLength="100"
              value={formData.name} 
              onChange={e => setFormData({...formData, name: e.target.value})} 
              placeholder="Ej. Serie I"
            />
          </div>

          <div className="form-group">
            <label>Fecha de Suscripción *</label>
            <input 
              type="date" 
              required 
              value={formData.fecha_suscripcion} 
              onChange={e => setFormData({...formData, fecha_suscripcion: e.target.value})} 
            />
          </div>

          <div className="form-group">
            <label>Tasa Nominal Anual (TNA %) *</label>
            <input 
              type="number" 
              required 
              step="0.01"
              min="0"
              value={formData.tna} 
              onChange={e => setFormData({...formData, tna: e.target.value})} 
              placeholder="Ej. 45.5"
            />
          </div>

          <div className="form-group">
            <label>Plazo (días) *</label>
            <input 
              type="number" 
              required 
              min="1"
              step="1"
              value={formData.plazo} 
              onChange={e => setFormData({...formData, plazo: e.target.value})} 
              placeholder="Ej. 365"
            />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Crear Serie'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default SeriesPage;
