import { useState, useEffect } from 'react';
import { X, Save } from 'lucide-react';
import axiosClient from '../../api/axiosClient';

const CuentaModal = ({ isOpen, onClose, onSaved, cuenta = null }) => {
  const [bancos, setBancos] = useState([]);
  const [formData, setFormData] = useState({
    nombre: '',
    banco_id: '',
    nro: '',
    cbu: '',
    alias: '',
    tipo_cuenta: 'Cuenta Corriente'
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Nuevo Banco State
  const [showNewBanco, setShowNewBanco] = useState(false);
  const [nuevoBancoNombre, setNuevoBancoNombre] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchBancos();
      if (cuenta) {
        setFormData({
          nombre: cuenta.nombre,
          banco_id: cuenta.banco_id,
          nro: cuenta.nro || '',
          cbu: cuenta.cbu || '',
          alias: cuenta.alias || '',
          tipo_cuenta: cuenta.tipo_cuenta || 'Cuenta Corriente'
        });
      } else {
        setFormData({
          nombre: '',
          banco_id: '',
          nro: '',
          cbu: '',
          alias: '',
          tipo_cuenta: 'Cuenta Corriente'
        });
      }
      setShowNewBanco(false);
      setNuevoBancoNombre('');
      setError('');
    }
  }, [isOpen, cuenta]);

  const fetchBancos = async () => {
    try {
      const res = await axiosClient.get('/api/finanzas/bancos');
      setBancos(res.data);
    } catch (err) {
      console.error(err);
      setError('Error al cargar los bancos.');
    }
  };

  const handleCreateBanco = async () => {
    if (!nuevoBancoNombre.trim()) return;
    try {
      setLoading(true);
      const res = await axiosClient.post('/api/finanzas/bancos', { nombre_banco: nuevoBancoNombre });
      await fetchBancos();
      setFormData({ ...formData, banco_id: res.data.id });
      setShowNewBanco(false);
      setNuevoBancoNombre('');
    } catch (err) {
      console.error(err);
      setError('Error al crear el banco.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.banco_id) {
      setError('Debe seleccionar un banco.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      if (cuenta) {
        await axiosClient.put(`/api/finanzas/cuentas/${cuenta.id}`, formData);
      } else {
        await axiosClient.post('/api/finanzas/cuentas', formData);
      }
      onSaved();
      onClose();
    } catch (err) {
      console.error(err);
      setError('Error al guardar la cuenta.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="modal-content" style={{ background: 'var(--surface-color)', padding: '24px', borderRadius: 'var(--radius-lg)', width: '100%', maxWidth: '500px', boxShadow: 'var(--shadow-lg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold' }}>{cuenta ? 'Editar Cuenta' : 'Nueva Cuenta'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <X size={24} />
          </button>
        </div>

        {error && <div className="alert alert-error" style={{ marginBottom: '16px' }}>{error}</div>}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Banco</label>
              {!showNewBanco ? (
                <select name="banco_id" value={formData.banco_id} onChange={handleChange} className="form-control" required>
                  <option value="">Seleccione un banco...</option>
                  {bancos.map(b => <option key={b.id} value={b.id}>{b.nombre_banco}</option>)}
                </select>
              ) : (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input type="text" className="form-control" placeholder="Nombre del nuevo banco" value={nuevoBancoNombre} onChange={(e) => setNuevoBancoNombre(e.target.value)} />
                  <button type="button" className="btn btn-primary" onClick={handleCreateBanco} disabled={loading}>Guardar</button>
                  <button type="button" className="btn btn-outline" onClick={() => setShowNewBanco(false)}>Cancelar</button>
                </div>
              )}
            </div>
            {!showNewBanco && (
              <button type="button" className="btn btn-outline" onClick={() => setShowNewBanco(true)}>
                + Nuevo
              </button>
            )}
          </div>

          <div>
            <label className="form-label">Nombre de la Cuenta (Referencia)</label>
            <input type="text" name="nombre" value={formData.nombre} onChange={handleChange} className="form-control" required placeholder="Ej: Galicia Cta. Cte." />
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">Tipo de Cuenta</label>
              <select name="tipo_cuenta" value={formData.tipo_cuenta} onChange={handleChange} className="form-control">
                <option value="Cuenta Corriente">Cuenta Corriente</option>
                <option value="Caja de Ahorro">Caja de Ahorro</option>
                <option value="Cuenta Comitente">Cuenta Comitente</option>
              </select>
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Número de Cuenta</label>
              <input type="text" name="nro" value={formData.nro} onChange={handleChange} className="form-control" />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label className="form-label">CBU / CVU</label>
              <input type="text" name="cbu" value={formData.cbu} onChange={handleChange} className="form-control" />
            </div>
            <div style={{ flex: 1 }}>
              <label className="form-label">Alias</label>
              <input type="text" name="alias" value={formData.alias} onChange={handleChange} className="form-control" />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
            <button type="button" className="btn btn-outline" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || showNewBanco}>
              <Save size={18} style={{ marginRight: '8px' }} />
              Guardar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CuentaModal;
