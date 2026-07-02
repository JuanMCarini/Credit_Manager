import { useState, useRef } from 'react';
import axiosClient from '../api/axiosClient';

const CreditProcessesPage = () => {
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setResults(null);
    }
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      alert("Por favor, seleccione al menos un archivo o un ZIP.");
      return;
    }

    setLoading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const response = await axiosClient.post('/api/v1/creditos/procesos/upload-batch', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setResults(response.data);
      alert("Proceso finalizado.");
      setFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error(error);
      alert("Error en el procesamiento masivo: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Procesos de Crédito</h2>
        <p>Adjunte múltiples archivos o un ZIP masivo. El sistema asociará cada archivo a su crédito/transferencia correspondiente basándose en su nombre.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
          <h3 style={{ marginBottom: '16px' }}>Carga Masiva de Archivos 📁</h3>
          
          <div style={{ marginBottom: '20px' }}>
            <label className="form-label">Seleccionar Archivos (PDF, JPG, PNG o un .ZIP)</label>
            <input 
              type="file" 
              className="form-input" 
              multiple
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".zip,.pdf,.jpg,.jpeg,.png"
            />
            {files.length > 0 && (
              <p style={{ marginTop: '8px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                {files.length} archivo(s) seleccionado(s).
              </p>
            )}
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-hover)', borderRadius: 'var(--radius-md)', marginBottom: '24px' }}>
            <h4 style={{ marginBottom: '8px', fontSize: '14px' }}>Instrucciones:</h4>
            <ul style={{ fontSize: '13px', color: 'var(--text-muted)', paddingLeft: '20px', margin: 0, lineHeight: 1.6 }}>
              <li>Para <strong>Créditos</strong>: El nombre del archivo debe contener el ID o el ID Externo del crédito (ej. <code style={{color:'var(--accent)'}}>contrato-664.pdf</code>).</li>
              <li>Para <strong>Transferencias</strong>: El nombre debe respetar el formato <code>T-ID-N</code>, donde ID es el crédito y N es el número de transferencia (ej. <code style={{color:'var(--accent)'}}>T-664-1.jpg</code> para la primer transferencia del crédito 664).</li>
            </ul>
          </div>

          <button className="btn-primary" onClick={handleUpload} disabled={loading || files.length === 0} style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
            {loading ? (
              <>
                <svg className="spinner" viewBox="0 0 50 50" style={{ width: '20px', height: '20px', stroke: 'currentColor', strokeWidth: 4, fill: 'none', animation: 'spin 1s linear infinite' }}><circle cx="25" cy="25" r="20" strokeDasharray="90 150"></circle></svg>
                Procesando...
              </>
            ) : "Subir y Procesar Archivos"}
          </button>
        </div>

        {results && (
          <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
            <h3 style={{ marginBottom: '16px' }}>Resultados del Procesamiento</h3>
            
            <div style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: '500', color: 'var(--success)' }}>Procesados con éxito:</span>
                <span style={{ fontWeight: 'bold' }}>{results.procesados?.length || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: '500', color: 'var(--danger)' }}>Errores encontrados:</span>
                <span style={{ fontWeight: 'bold' }}>{results.errores?.length || 0}</span>
              </div>
            </div>

            {results.errores && results.errores.length > 0 && (
              <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                <table className="data-table" style={{ fontSize: '13px' }}>
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>Archivo</th>
                      <th style={{ textAlign: 'left' }}>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.errores.map((err, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td style={{ color: 'var(--danger)', wordBreak: 'break-all' }}>{err.archivo}</td>
                        <td style={{ color: 'var(--text-secondary)' }}>{err.error}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            
            {results.procesados && results.procesados.length > 0 && (
              <div style={{ maxHeight: '200px', overflowY: 'auto', marginTop: '20px' }}>
                <h4 style={{ fontSize: '13px', marginBottom: '8px', color: 'var(--success)' }}>Archivos vinculados</h4>
                <ul style={{ fontSize: '12px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                  {results.procesados.map((proc, i) => (
                    <li key={i}>{proc.archivo} → Crédito ID: {proc.credito_id} {proc.transferencia_id ? `(Transf. ${proc.transferencia_id})` : ''}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
};

export default CreditProcessesPage;
