import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const CollectionsProcessingPage = () => {
  const [operationType, setOperationType] = useState('individual');
  const [indData, setIndData] = useState({
    identificador: 'CLIENTE_DNI',
    id_val: '',
    monto: '',
    fecha_pago: '',
    fecha_corte: '',
    tipo: 'comun',
  });
  const [indFeedback, setIndFeedback] = useState({ type: '', message: '' });
  const [indLoading, setIndLoading] = useState(false);

  const [masData, setMasData] = useState({
    identificador: 'CLIENTE_DNI',
    id_column: 'A',
    amount_column: 'B',
    file: null,
    fecha_pago: '',
    fecha_corte: '',
    tipo: 'comun',
  });
  const [masFeedback, setMasFeedback] = useState({ type: '', message: '' });
  const [masLoading, setMasLoading] = useState(false);

  const [recData, setRecData] = useState({
    identificador: 'PROVEEDOR_CUIT',
    id_val: '',
    monto: '',
    fecha_pago: '',
  });
  const [recFeedback, setRecFeedback] = useState({ type: '', message: '' });
  const [recLoading, setRecLoading] = useState(false);

  const [socios, setSocios] = useState([]);
  const [carteras, setCarteras] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [resSocios, resCarteras] = await Promise.all([
          axiosClient.post('/api/v1/auxiliares/socios/data', { page: 1, size: 1000 }),
          axiosClient.get('/api/v1/carteras')
        ]);
        setSocios(resSocios.data.data || resSocios.data);
        setCarteras(resCarteras.data);
      } catch (error) {
        console.error("Error fetching dependencies:", error);
      }
    };
    fetchData();
  }, []);

  const handleIndSubmit = async (e) => {
    e.preventDefault();
    setIndLoading(true);
    setIndFeedback({ type: '', message: '' });

    try {
      const payload = {
        identificador: indData.identificador,
        id_val: indData.id_val,
        monto: parseFloat(indData.monto),
        fecha_pago: indData.fecha_pago,
        fecha_corte: indData.fecha_corte || null,
        anticipada: indData.tipo === 'anticipada',
      };
      const res = await axiosClient.post('/api/v1/cobranzas/individual', payload);
      setIndFeedback({ type: 'success', message: res.data.message || 'Cobranza procesada con éxito.' });
      setIndData({ ...indData, id_val: '', monto: '', fecha_pago: '', fecha_corte: '' });
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      setIndFeedback({ type: 'error', message: `Error: ${msg}` });
    } finally {
      setIndLoading(false);
    }
  };

  const handleMasSubmit = async (e) => {
    e.preventDefault();
    if (!masData.file) {
      setMasFeedback({ type: 'error', message: 'Debe seleccionar un archivo Excel.' });
      return;
    }
    setMasLoading(true);
    setMasFeedback({ type: '', message: '' });

    const formData = new FormData();
    formData.append('identificador', masData.identificador);
    formData.append('id_column', masData.id_column.toUpperCase());
    formData.append('amount_column', masData.amount_column.toUpperCase());
    if (masData.fecha_pago) formData.append('fecha_pago', masData.fecha_pago);
    if (masData.fecha_corte) formData.append('fecha_corte', masData.fecha_corte);
    formData.append('anticipada', masData.tipo === 'anticipada');
    formData.append('file', masData.file);

    try {
      const res = await axiosClient.post('/api/v1/cobranzas/masiva', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMasFeedback({ type: 'success', message: res.data.message || `Lote procesado. ID: ${res.data.proceso_id}` });
      setMasData({ ...masData, file: null, fecha_pago: '', fecha_corte: '' });
      document.getElementById('cob-mas-file').value = '';
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      setMasFeedback({ type: 'error', message: `Error: ${msg}` });
    } finally {
      setMasLoading(false);
    }
  };

  const handleRecSubmit = async (e) => {
    e.preventDefault();
    setRecLoading(true);
    setRecFeedback({ type: '', message: '' });

    try {
      const payload = {
        identificador: recData.identificador,
        id_val: recData.id_val,
        monto: parseFloat(recData.monto),
        fecha_pago: recData.fecha_pago || null,
      };
      const res = await axiosClient.post('/api/v1/cobranzas/recurso', payload);
      setRecFeedback({ type: 'success', message: res.data.message || `Cobranza con Recurso procesada. ID: ${res.data.proceso_id}` });
      setRecData({ ...recData, id_val: '', monto: '', fecha_pago: '' });
    } catch (error) {
      const msg = error.response?.data?.detail || error.message;
      setRecFeedback({ type: 'error', message: `Error: ${msg}` });
    } finally {
      setRecLoading(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Ingreso de Cobranzas</h2>
        <p>Cargue nuevas cobranzas de forma individual o de manera masiva mediante un archivo Excel (.xlsx).</p>
      </header>

      <div className="content-grid" style={{ gridTemplateColumns: '1fr' }}>
        
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-color)', marginBottom: '8px', display: 'block' }}>Tipo de Ingreso</label>
            <select 
              value={operationType} 
              onChange={(e) => setOperationType(e.target.value)}
              style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)', backgroundColor: 'var(--surface-color)', color: 'var(--text-color)', fontSize: '15px' }}
            >
              <option value="individual">Cobranza Individual</option>
              <option value="masiva">Cobranza Masiva por Lote</option>
              <option value="recurso">Cobranza con Recurso</option>
            </select>
          </div>

          {operationType === 'individual' && (
            <div style={{ animation: 'fadeIn 0.3s ease' }}>
              <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)', fontSize: '18px', color: 'var(--primary-color)' }}>Cobranza Individual</h3>
              <form onSubmit={handleIndSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Tipo de Identificador *</label>
                <select value={indData.identificador} onChange={(e) => setIndData({...indData, identificador: e.target.value})} required>
                  <option value="CLIENTE_DNI">Documento del Cliente (DNI)</option>
                  <option value="CLIENTE_CUIL">CUIL del Cliente</option>
                  <option value="CREDITO_ID">ID del Crédito</option>
                  <option value="ID_EXTERNO">ID Externo</option>
                </select>
              </div>
              <div className="form-group">
                <label>Valor *</label>
                <input type="text" value={indData.id_val} onChange={(e) => setIndData({...indData, id_val: e.target.value})} required placeholder="Ej. 12345678" />
              </div>
              <div className="form-group">
                <label>Monto a Cobrar ($) *</label>
                <input type="number" step="0.01" value={indData.monto} onChange={(e) => setIndData({...indData, monto: e.target.value})} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Fecha de Cobro *</label>
                <input type="date" value={indData.fecha_pago} onChange={(e) => setIndData({...indData, fecha_pago: e.target.value})} required />
              </div>
              <div className="form-group">
                <label>Fecha de Corte/Vto</label>
                <input type="date" value={indData.fecha_corte} onChange={(e) => setIndData({...indData, fecha_corte: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Tipo de Cobro *</label>
                <select value={indData.tipo} onChange={(e) => setIndData({...indData, tipo: e.target.value})} required>
                  <option value="comun">Común / Anticipo</option>
                  <option value="anticipada">Cancelación Anticipada (Con quita)</option>
                </select>
              </div>
            </div>
            <div className="form-actions" style={{ marginTop: '16px' }}>
              <button type="submit" className="btn-primary" style={{ width: '100%', height: '42px' }} disabled={indLoading}>
                {indLoading ? 'Procesando...' : 'Procesar Cobranza Individual'}
              </button>
            </div>
            {indFeedback.message && (
              <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: 500, color: indFeedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)' }}>
                {indFeedback.message}
              </div>
            )}
          </form>
            </div>
          )}

          {operationType === 'masiva' && (
            <div style={{ animation: 'fadeIn 0.3s ease' }}>
              <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)', fontSize: '18px', color: 'var(--primary-color)' }}>Cobranza Masiva por Lote</h3>
              <form onSubmit={handleMasSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Tipo de Identificador *</label>
                <select value={masData.identificador} onChange={(e) => setMasData({...masData, identificador: e.target.value})} required>
                  <option value="CLIENTE_DNI">Documento del Cliente (DNI)</option>
                  <option value="CLIENTE_CUIL">CUIL del Cliente</option>
                  <option value="CREDITO_ID">ID del Crédito</option>
                  <option value="ID_EXTERNO">ID Externo</option>
                  <option value="CARTERA_ID">ID de Cartera</option>
                </select>
              </div>
              <div className="form-group">
                <label>Columna ID (Ej. A) *</label>
                <input type="text" value={masData.id_column} onChange={(e) => setMasData({...masData, id_column: e.target.value})} required maxLength="2" />
              </div>
              <div className="form-group">
                <label>Columna Monto (Ej. B) *</label>
                <input type="text" value={masData.amount_column} onChange={(e) => setMasData({...masData, amount_column: e.target.value})} required maxLength="2" />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Archivo Excel (.xlsx) *</label>
                <input type="file" id="cob-mas-file" accept=".xlsx" onChange={(e) => setMasData({...masData, file: e.target.files[0]})} required />
              </div>
              <div className="form-group">
                <label>Fecha de Cobro</label>
                <input type="date" value={masData.fecha_pago} onChange={(e) => setMasData({...masData, fecha_pago: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Fecha de Corte/Vto</label>
                <input type="date" value={masData.fecha_corte} onChange={(e) => setMasData({...masData, fecha_corte: e.target.value})} />
              </div>
              <div className="form-group">
                <label>Tipo de Cobro *</label>
                <select value={masData.tipo} onChange={(e) => setMasData({...masData, tipo: e.target.value})} required>
                  <option value="comun">Común / Anticipo</option>
                  <option value="anticipada">Cancelación Anticipada (Con quita)</option>
                </select>
              </div>
            </div>
            <div className="form-actions" style={{ marginTop: '16px' }}>
              <button type="submit" className="btn-primary" style={{ width: '100%', fontSize: '16px', padding: '14px' }} disabled={masLoading}>
                {masLoading ? 'Procesando Lote...' : 'Procesar Lote Masivo'}
              </button>
            </div>
            {masFeedback.message && (
              <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: 500, color: masFeedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)' }}>
                {masFeedback.message}
              </div>
            )}
          </form>
            </div>
          )}

          {operationType === 'recurso' && (
            <div style={{ animation: 'fadeIn 0.3s ease' }}>
              <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)', fontSize: '18px', color: 'var(--primary-color)' }}>Cobranza Masiva con Recurso</h3>
              <form onSubmit={handleRecSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Tipo de Identificador *</label>
                <select value={recData.identificador} onChange={(e) => setRecData({...recData, identificador: e.target.value, id_val: ''})} required>
                  <option value="PROVEEDOR_CUIT">CUIT del Socio/Proveedor</option>
                  <option value="CARTERA_ID">ID de Cartera</option>
                </select>
              </div>
              <div className="form-group">
                <label>Identificador *</label>
                {recData.identificador === 'PROVEEDOR_CUIT' ? (
                  <select value={recData.id_val} onChange={(e) => setRecData({...recData, id_val: e.target.value})} required>
                    <option value="">Seleccione un Socio...</option>
                    {socios.map(s => (
                      <option key={s.id} value={s.cuit}>{s.razon_social} ({s.cuit})</option>
                    ))}
                  </select>
                ) : (
                  <select value={recData.id_val} onChange={(e) => setRecData({...recData, id_val: e.target.value})} required>
                    <option value="">Seleccione una Cartera...</option>
                    {carteras.map(c => (
                      <option key={c.id} value={c.id}>{c.nombre} (ID: {c.id})</option>
                    ))}
                  </select>
                )}
              </div>
              <div className="form-group">
                <label>Monto a Cobrar ($) *</label>
                <input type="number" step="0.01" value={recData.monto} onChange={(e) => setRecData({...recData, monto: e.target.value})} required />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Fecha de Cobro *</label>
                <input type="date" value={recData.fecha_pago} onChange={(e) => setRecData({...recData, fecha_pago: e.target.value})} required />
              </div>
            </div>
            <div className="form-actions" style={{ marginTop: '16px' }}>
              <button type="submit" className="btn-primary" style={{ width: '100%', fontSize: '16px', padding: '14px' }} disabled={recLoading}>
                {recLoading ? 'Procesando Recurso...' : 'Procesar Cobranza con Recurso'}
              </button>
            </div>
            {recFeedback.message && (
              <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: 500, color: recFeedback.type === 'error' ? 'var(--danger-color)' : 'var(--success-color)' }}>
                {recFeedback.message}
              </div>
            )}
          </form>
            </div>
          )}
        </div>

      </div>
    </section>
  );
};

export default CollectionsProcessingPage;
