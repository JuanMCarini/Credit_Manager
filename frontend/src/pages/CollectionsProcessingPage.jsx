import { useState } from 'react';
import axiosClient from '../api/axiosClient';

const CollectionsProcessingPage = () => {
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

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Ingreso de Cobranzas</h2>
        <p>Cargue nuevas cobranzas de forma individual o de manera masiva mediante un archivo Excel (.xlsx).</p>
      </header>

      <div className="content-grid" style={{ gridTemplateColumns: '1fr' }}>
        
        {/* Cobranza Individual */}
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '12px', fontFamily: 'var(--font-heading)', fontSize: '16px' }}>Cobranza Individual</h3>
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

        {/* Cobranza Masiva */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <h3 style={{ marginBottom: '12px', fontFamily: 'var(--font-heading)', fontSize: '16px' }}>Cobranza Masiva por Lote</h3>
          <form onSubmit={handleMasSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label>Tipo de Identificador *</label>
                <select value={masData.identificador} onChange={(e) => setMasData({...masData, identificador: e.target.value})} required>
                  <option value="CLIENTE_DNI">Documento del Cliente (DNI)</option>
                  <option value="CLIENTE_CUIL">CUIL del Cliente</option>
                  <option value="CREDITO_ID">ID del Crédito</option>
                  <option value="ID_EXTERNO">ID Externo</option>
                  <option value="PROVEEDOR_CUIT">CUIT del Socio/Proveedor (Con Recurso)</option>
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

      </div>
    </section>
  );
};

export default CollectionsProcessingPage;
