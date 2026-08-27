import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axiosClient from '../api/axiosClient';
import { Plus, X } from 'lucide-react';

const SeriesPage = () => {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editSerieData, setEditSerieData] = useState(null);
  const [fechaCorte, setFechaCorte] = useState(new Date().toISOString().split('T')[0]);
  const [fSuscripcionDesde, setFSuscripcionDesde] = useState('');
  const [fSuscripcionHasta, setFSuscripcionHasta] = useState('');
  const [fVencimientoDesde, setFVencimientoDesde] = useState('');
  const [fVencimientoHasta, setFVencimientoHasta] = useState('');

  // Fetch Series
  const { data, isLoading } = useQuery({
    queryKey: ['series-deuda'],
    queryFn: async () => {
      const res = await axiosClient.get('/api/v1/inversores/series');
      return res.data;
    }
  });

  const series = data?.items || [];
  const filteredSeries = series.filter(s => {
    let match = true;
    if (fSuscripcionDesde && s.fecha_suscripcion < fSuscripcionDesde) match = false;
    if (fSuscripcionHasta && s.fecha_suscripcion > fSuscripcionHasta) match = false;
    
    if (fVencimientoDesde && s.fecha_vencimiento < fVencimientoDesde) match = false;
    if (fVencimientoHasta && s.fecha_vencimiento > fVencimientoHasta) match = false;

    return match;
  });

  const formatCurrency = (val) => new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(val);
  const formatDate = (dateObj) => dateObj.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' });

  const totals = filteredSeries.reduce((acc, s) => {
    const capital = s.capital || 0;
    const interes = capital * s.tna * (s.plazo / 365);
    const total = capital + interes;

    const fSuscripcion = new Date(s.fecha_suscripcion + 'T00:00:00');
    const fVencimiento = new Date(s.fecha_vencimiento + 'T00:00:00');
    const fCorte = new Date(fechaCorte + 'T00:00:00');

    let interesDevengado = 0;
    if (fCorte <= fSuscripcion) interesDevengado = 0;
    else if (fCorte >= fVencimiento) interesDevengado = interes;
    else interesDevengado = capital * s.tna * (((fCorte - fSuscripcion) / 86400000) / 365);

    const interesADevengar = Math.max(0, interes - interesDevengado);

    const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
    const fechaInicioMensual = fSuscripcion > primerDiaMes ? fSuscripcion : primerDiaMes;
    const fechaFinMensual = fCorte < fVencimiento ? fCorte : fVencimiento;
    let diasMensuales = (fechaFinMensual - fechaInicioMensual) / 86400000;
    if (diasMensuales < 0) diasMensuales = 0;
    const interesMensual = capital * s.tna * (diasMensuales / 365);

    acc.capital += capital;
    acc.interes += interes;
    acc.total += total;
    acc.interesDevengado += interesDevengado;
    acc.interesADevengar += interesADevengar;
    acc.interesMensual += interesMensual;

    return acc;
  }, { capital: 0, interes: 0, total: 0, interesDevengado: 0, interesADevengar: 0, interesMensual: 0 });

  // Add Mutation
  const addMutation = useMutation({
    mutationFn: async (nuevaSerie) => {
      let res;
      if (nuevaSerie.file) {
        const formData = new FormData();
        formData.append('name', nuevaSerie.name);
        formData.append('fecha_suscripcion', nuevaSerie.fecha_suscripcion);
        formData.append('tna', nuevaSerie.tna);
        formData.append('plazo', nuevaSerie.plazo);
        formData.append('file', nuevaSerie.file);
        res = await axiosClient.post('/api/v1/inversores/series/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        res = await axiosClient.post('/api/v1/inversores/series', nuevaSerie);
      }
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

  const deleteMutation = useMutation({
    mutationFn: async (id) => {
      const res = await axiosClient.delete(`/api/v1/inversores/series/${id}`);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al eliminar la serie');
    }
  });

  const editMutation = useMutation({
    mutationFn: async ({ id, data }) => {
      const res = await axiosClient.put(`/api/v1/inversores/series/${id}`, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['series-deuda'] });
      setEditSerieData(null);
      alert('Serie actualizada con éxito');
    },
    onError: (error) => {
      alert(error.response?.data?.detail || 'Error al actualizar la serie');
    }
  });

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
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

      <div className="glass-panel" style={{ padding: '15px', marginBottom: '20px', display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-end', backgroundColor: 'rgba(255, 255, 255, 0.05)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)' }}>FECHA DE SUSCRIPCIÓN</span>
          <div style={{ display: 'flex', gap: '10px' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '11px' }}>Desde</label>
              <input type="date" value={fSuscripcionDesde} onChange={e => setFSuscripcionDesde(e.target.value)} style={{ padding: '6px 12px' }} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '11px' }}>Hasta</label>
              <input type="date" value={fSuscripcionHasta} onChange={e => setFSuscripcionHasta(e.target.value)} style={{ padding: '6px 12px' }} />
            </div>
          </div>
        </div>

        <div style={{ width: '1px', backgroundColor: 'rgba(255,255,255,0.1)', height: '40px', alignSelf: 'center' }}></div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)' }}>FECHA DE VENCIMIENTO</span>
          <div style={{ display: 'flex', gap: '10px' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '11px' }}>Desde</label>
              <input type="date" value={fVencimientoDesde} onChange={e => setFVencimientoDesde(e.target.value)} style={{ padding: '6px 12px' }} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label style={{ fontSize: '11px' }}>Hasta</label>
              <input type="date" value={fVencimientoHasta} onChange={e => setFVencimientoHasta(e.target.value)} style={{ padding: '6px 12px' }} />
            </div>
          </div>
        </div>

        <div style={{ width: '1px', backgroundColor: 'rgba(255,255,255,0.1)', height: '40px', alignSelf: 'center' }}></div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
          <span style={{ fontSize: '12px', fontWeight: 'bold', color: 'var(--text-muted)' }}>CÁLCULO DE INTERESES</span>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label style={{ fontSize: '11px' }}>Fecha de Corte</label>
            <input type="date" value={fechaCorte} onChange={e => setFechaCorte(e.target.value)} style={{ padding: '6px 12px' }} />
          </div>
        </div>
      </div>

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
                <th>Capital</th>
                <th>Interés</th>
                <th>Total</th>
                <th>Int. Mensual</th>
                <th>Int. Devengado</th>
                <th>Int. a Devengar</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan="13" style={{ textAlign: 'center', padding: '20px' }}>Cargando...</td></tr>
              ) : filteredSeries.length === 0 ? (
                <tr><td colSpan="13" style={{ textAlign: 'center', padding: '20px' }}>No se encontraron series.</td></tr>
              ) : (
                filteredSeries.map(s => {
                  const capital = s.capital || 0;
                  const interes = capital * s.tna * (s.plazo / 365);
                  const total = capital + interes;

                  // Handle timezone issues by using string parsing if necessary, but simple Date object works well for YYYY-MM-DD
                  const fSuscripcion = new Date(s.fecha_suscripcion + 'T00:00:00');
                  const fVencimiento = new Date(s.fecha_vencimiento + 'T00:00:00');
                  const fCorte = new Date(fechaCorte + 'T00:00:00');

                  let interesDevengado = 0;
                  if (fCorte <= fSuscripcion) {
                    interesDevengado = 0;
                  } else if (fCorte >= fVencimiento) {
                    interesDevengado = interes;
                  } else {
                    const diasTranscurridos = (fCorte - fSuscripcion) / (1000 * 60 * 60 * 24);
                    interesDevengado = capital * s.tna * (diasTranscurridos / 365);
                  }

                  const interesADevengar = Math.max(0, interes - interesDevengado);

                  // Calculo de interes mensual
                  const primerDiaMes = new Date(fCorte.getFullYear(), fCorte.getMonth(), 1);
                  const fechaInicioMensual = fSuscripcion > primerDiaMes ? fSuscripcion : primerDiaMes;
                  const fechaFinMensual = fCorte < fVencimiento ? fCorte : fVencimiento;
                  let diasMensuales = (fechaFinMensual - fechaInicioMensual) / (1000 * 60 * 60 * 24);
                  if (diasMensuales < 0) diasMensuales = 0;
                  const interesMensual = capital * s.tna * (diasMensuales / 365);

                  return (
                    <tr key={s.id}>
                      <td>{s.id}</td>
                      <td><strong>{s.name}</strong></td>
                      <td>{formatDate(fSuscripcion)}</td>
                      <td>{(s.tna * 100).toFixed(2)}%</td>
                      <td>{s.plazo}</td>
                      <td>{formatDate(fVencimiento)}</td>
                      <td>{formatCurrency(capital)}</td>
                      <td>{formatCurrency(interes)}</td>
                      <td>{formatCurrency(total)}</td>
                      <td>{formatCurrency(interesMensual)}</td>
                      <td>{formatCurrency(interesDevengado)}</td>
                      <td>{formatCurrency(interesADevengar)}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button 
                            className="btn-secondary" 
                            style={{ padding: '4px', fontSize: '14px' }}
                            onClick={() => setEditSerieData(s)}
                            title="Editar Serie"
                          >
                            ✏️
                          </button>
                          <button 
                            className="btn-secondary" 
                            style={{ padding: '4px', fontSize: '14px', color: 'var(--danger-color)' }}
                            onClick={() => {
                              if (window.confirm('¿Está seguro de eliminar esta serie? Se eliminarán también todos los movimientos asociados.')) {
                                deleteMutation.mutate(s.id);
                              }
                            }}
                            title="Eliminar Serie"
                          >
                            🗑️
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="6" style={{ textAlign: 'right', fontWeight: 'bold' }}>
                  Totales ({filteredSeries.length} series):
                </td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.capital)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interes)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.total)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interesMensual)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interesDevengado)}</td>
                <td style={{ fontWeight: 'bold' }}>{formatCurrency(totals.interesADevengar)}</td>
                <td></td>
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
      {editSerieData && (
        <EditSerieModal
          initialData={editSerieData}
          onClose={() => setEditSerieData(null)}
          onSubmit={(data) => editMutation.mutate({ id: editSerieData.id, data })}
          isLoading={editMutation.isPending}
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
    plazo: '',
    file: null
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      name: formData.name,
      fecha_suscripcion: formData.fecha_suscripcion,
      tna: parseFloat(formData.tna) / 100,
      plazo: parseInt(formData.plazo, 10)
    };
    if (formData.file) {
      data.file = formData.file;
    }
    onSubmit(data);
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
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej. Serie I"
            />
          </div>

          <div className="form-group">
            <label>Fecha de Suscripción *</label>
            <input
              type="date"
              required
              value={formData.fecha_suscripcion}
              onChange={e => setFormData({ ...formData, fecha_suscripcion: e.target.value })}
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
              onChange={e => setFormData({ ...formData, tna: e.target.value })}
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
              onChange={e => setFormData({ ...formData, plazo: e.target.value })}
              placeholder="Ej. 365"
            />
          </div>

          <div className="form-group">
            <label>Archivo de Suscripciones (Excel/CSV) - Opcional</label>
            <input
              type="file"
              accept=".xlsx,.csv"
              onChange={e => setFormData({ ...formData, file: e.target.files[0] })}
              style={{ padding: '8px 0' }}
            />
            <small style={{ color: 'var(--text-muted)' }}>Procesa y carga las suscripciones asociadas a la serie usando la función `nueva_serie`.</small>
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

// Edit Modal Component
const EditSerieModal = ({ initialData, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: initialData.name || '',
    fecha_suscripcion: initialData.fecha_suscripcion || '',
    tna: initialData.tna ? (initialData.tna * 100).toFixed(2) : '',
    plazo: initialData.plazo || '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const data = {
      name: formData.name,
      fecha_suscripcion: formData.fecha_suscripcion,
      tna: parseFloat(formData.tna) / 100,
      plazo: parseInt(formData.plazo, 10)
    };
    onSubmit(data);
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
        <h3 style={{ marginTop: 0, marginBottom: '20px' }}>Editar Serie</h3>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

          <div className="form-group">
            <label>Nombre de la Serie *</label>
            <input
              type="text"
              required
              maxLength="100"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ej. Serie I"
            />
          </div>

          <div className="form-group">
            <label>Fecha de Suscripción *</label>
            <input
              type="date"
              required
              value={formData.fecha_suscripcion}
              onChange={e => setFormData({ ...formData, fecha_suscripcion: e.target.value })}
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
              onChange={e => setFormData({ ...formData, tna: e.target.value })}
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
              onChange={e => setFormData({ ...formData, plazo: e.target.value })}
              placeholder="Ej. 365"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <button type="button" className="btn-secondary" onClick={onClose} disabled={isLoading}>Cancelar</button>
            <button type="submit" className="btn-primary" disabled={isLoading}>
              {isLoading ? 'Guardando...' : 'Guardar Cambios'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
