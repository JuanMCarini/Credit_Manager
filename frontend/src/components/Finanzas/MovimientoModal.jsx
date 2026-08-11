import { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import axiosClient from '../../api/axiosClient';

const CategoriaMovimientoOpciones = [
  "Ingreso",
  "Egreso",
  "Suscripción FCI",
  "Rescate FCI",
  "Ingresos a plazo fijo",
  "Egresos de plazo fijo"
];

const MovimientoModal = ({ isOpen, onClose, onSaved, movimiento = null, cuentaIdDefault = '' }) => {
  const [cuentas, setCuentas] = useState([]);
  const [conceptos, setConceptos] = useState([]);
  const [clasificaciones, setClasificaciones] = useState([]);
  const [formData, setFormData] = useState({
    cuenta_id: cuentaIdDefault,
    fecha: new Date().toISOString().substring(0, 10),
    nro_comprobante: '',
    concepto_id: '',
    descripcion: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Nuevo Concepto State
  const [showNewConcepto, setShowNewConcepto] = useState(false);
  const [nuevoConcepto, setNuevoConcepto] = useState({
    name: '',
    tipo_movimiento: 'Ingreso',
    descripcion: '',
    clasificacion_id: ''
  });

  useEffect(() => {
    if (isOpen) {
      fetchCuentas();
      fetchConceptos();
      fetchClasificaciones();
      if (movimiento) {
        setFormData({
          cuenta_id: movimiento.cuenta_id,
          fecha: movimiento.fecha,
          monto: movimiento.monto,
          nro_comprobante: movimiento.nro_comprobante || '',
          concepto_id: movimiento.concepto_id || '',
          descripcion: movimiento.descripcion || ''
        });
      } else {
        setFormData({
          cuenta_id: cuentaIdDefault,
          fecha: new Date().toISOString().substring(0, 10),
          monto: '',
          nro_comprobante: '',
          concepto_id: '',
          descripcion: ''
        });
      }
      setShowNewConcepto(false);
      setNuevoConcepto({ name: '', tipo_movimiento: 'Ingreso', descripcion: '', clasificacion_id: '' });
      setError('');
    }
  }, [isOpen, movimiento, cuentaIdDefault]);

  const fetchCuentas = async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/cuentas');
      setCuentas(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchConceptos = async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/conceptos');
      setConceptos(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchClasificaciones = async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/clasificaciones');
      setClasificaciones(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateConcepto = async () => {
    if (!nuevoConcepto.name.trim()) return;
    try {
      setLoading(true);
      const res = await axiosClient.post('/api/finanzas/conceptos', nuevoConcepto);
      await fetchConceptos();
      setFormData({ ...formData, concepto_id: res.data.id });
      setShowNewConcepto(false);
      setNuevoConcepto({ name: '', tipo_movimiento: 'Ingreso', descripcion: '', clasificacion_id: '' });
    } catch (err) {
      console.error(err);
      setError('Error al crear el concepto.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const newData = { ...prev, [name]: value };
      return newData;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (movimiento) {
        await axiosClient.put(`/api/finanzas/movimientos/${movimiento.id}`, formData);
      } else {
        await axiosClient.post('/api/finanzas/movimientos', formData);
      }
      onSaved();
      onClose();
    } catch (err) {
      console.error(err);
      setError('Error al guardar el movimiento.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '500px', boxShadow: 'var(--shadow-lg)', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold' }}>{movimiento ? 'Editar Movimiento' : 'Nuevo Movimiento'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <X size={24} />
          </button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Cuenta</label>
              <select name="cuenta_id" value={formData.cuenta_id} onChange={handleChange} className="form-control" required>
                <option value="">Seleccione una cuenta...</option>
                {cuentas.map(c => <option key={c.id} value={c.id}>{c.banco?.nombre_banco} - {c.nombre}</option>)}
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Fecha</label>
              <input type="date" name="fecha" value={formData.fecha} onChange={handleChange} className="form-control" required />
            </div>
          </div>

          <div>
            <label className="form-label">Concepto</label>
            {!showNewConcepto ? (
              <div style={{ display: 'flex', gap: '8px' }}>
                <select name="concepto_id" value={formData.concepto_id} onChange={handleChange} className="form-control" required style={{ flex: 1 }}>
                  <option value="">Seleccione un concepto...</option>
                  {clasificaciones.map(cl => (
                    <optgroup key={cl.id} label={cl.name}>
                      {conceptos
                        .filter(c => c.clasificacion_id === cl.id)
                        .map(c => <option key={c.id} value={c.id}>{c.name} ({c.tipo_movimiento})</option>)}
                    </optgroup>
                  ))}
                  <optgroup label="Sin Clasificación">
                    {conceptos
                      .filter(c => !c.clasificacion_id)
                      .map(c => <option key={c.id} value={c.id}>{c.name} ({c.tipo_movimiento})</option>)}
                  </optgroup>
                </select>
                <button type="button" className="btn btn-outline" onClick={() => setShowNewConcepto(true)}>
                  + Nuevo
                </button>
              </div>
            ) : (
              <div style={{ border: '1px dashed var(--border-color)', padding: '12px', borderRadius: '8px', background: 'var(--background-color)' }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '14px' }}>Nuevo Concepto</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <input type="text" className="form-control" placeholder="Nombre (Ej: Gastos Varios)" value={nuevoConcepto.name} onChange={(e) => setNuevoConcepto({...nuevoConcepto, name: e.target.value})} />
                  <select className="form-control" value={nuevoConcepto.tipo_movimiento} onChange={(e) => setNuevoConcepto({...nuevoConcepto, tipo_movimiento: e.target.value})}>
                    {CategoriaMovimientoOpciones.map(opt => <option key={opt} value={opt}>{opt}</option>)}
                  </select>
                  <select className="form-control" value={nuevoConcepto.clasificacion_id} onChange={(e) => setNuevoConcepto({...nuevoConcepto, clasificacion_id: e.target.value})}>
                    <option value="">Sin Clasificación (Opcional)</option>
                    {clasificaciones.map(cl => <option key={cl.id} value={cl.id}>{cl.name}</option>)}
                  </select>
                  <input type="text" className="form-control" placeholder="Descripción (Opcional)" value={nuevoConcepto.descripcion} onChange={(e) => setNuevoConcepto({...nuevoConcepto, descripcion: e.target.value})} />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <button type="button" className="btn btn-primary" onClick={handleCreateConcepto} disabled={loading} style={{ flex: 1 }}>Guardar Concepto</button>
                    <button type="button" className="btn btn-outline" onClick={() => setShowNewConcepto(false)}>Cancelar</button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="form-label">Monto</label>
            <input type="number" step="0.01" name="monto" value={formData.monto} onChange={handleChange} className="form-control" required placeholder="0.00" />
          </div>

          <div>
            <label className="form-label">Nro. Comprobante</label>
            <input type="text" name="nro_comprobante" value={formData.nro_comprobante} onChange={handleChange} className="form-control" placeholder="Opcional" />
          </div>
          
          <div>
            <label className="form-label">Descripción / Referencia</label>
            <input type="text" name="descripcion" value={formData.descripcion} onChange={handleChange} className="form-control" placeholder="Detalles adicionales..." />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || showNewConcepto}>
              <Save size={18} style={{ marginRight: '8px' }} />
              Guardar Movimiento
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default MovimientoModal;
