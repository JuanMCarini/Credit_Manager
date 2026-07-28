import { useState, useRef } from 'react';
import axiosClient from '../api/axiosClient';

const CreditProcessesPage = () => {
  const [processType, setProcessType] = useState('MASIVA_ARCHIVOS');
  
  // States for Masiva Archivos
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [files, setFiles] = useState([]);
  const [resultsFiles, setResultsFiles] = useState(null);
  const fileInputRef = useRef(null);

  // States for Importacion Creditos
  const [loadingImport, setLoadingImport] = useState(false);
  const [proveedor, setProveedor] = useState('QUOTA_CFL');
  const [clientesFile, setClientesFile] = useState(null);
  const [creditosFile, setCreditosFile] = useState(null);
  const [transfFile, setTransfFile] = useState(null);
  const [webCargaFile, setWebCargaFile] = useState(null);
  const [archivosImport, setArchivosImport] = useState([]);
  const [resultsImport, setResultsImport] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
      setResultsFiles(null);
    }
  };

  const handleUploadFiles = async () => {
    if (files.length === 0) {
      alert("Por favor, seleccione al menos un archivo o un ZIP.");
      return;
    }

    setLoadingFiles(true);
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));

    try {
      const response = await axiosClient.post('/api/v1/creditos/procesos/upload-batch', formData);
      
      setResultsFiles(response.data);
      alert("Proceso finalizado.");
      setFiles([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error(error);
      alert("Error en el procesamiento masivo: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleImportCreditos = async () => {
    if (proveedor === 'QUOTA_CFL') {
      if (!clientesFile || !creditosFile || !transfFile) {
        alert("Por favor, seleccione los archivos Excel/CSV obligatorios.");
        return;
      }
    } else if (proveedor === 'WEB_CARGA_CFL') {
      if (!webCargaFile) {
        alert("Por favor, seleccione el archivo TXT de Web Carga.");
        return;
      }
    }

    setLoadingImport(true);
    const formData = new FormData();
    formData.append('proveedor', proveedor);
    
    if (proveedor === 'QUOTA_CFL') {
      formData.append('clientes_file', clientesFile);
      formData.append('creditos_file', creditosFile);
      formData.append('transferencias_file', transfFile);
    } else if (proveedor === 'WEB_CARGA_CFL') {
      formData.append('archivo_web_carga', webCargaFile);
    }
    
    archivosImport.forEach((f) => formData.append('archivos', f));

    try {
      const response = await axiosClient.post('/api/v1/creditos/importacion-masiva', formData);
      
      setResultsImport(response.data);
      alert("Importación procesada. " + (response.data.errores_count > 0 ? "Se encontraron algunos errores." : "Todo exitoso."));
    } catch (error) {
      console.error(error);
      alert("Error en la importación: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingImport(false);
    }
  };

  const downloadExcelErrors = () => {
    if (resultsImport && resultsImport.excel_base64) {
      const link = document.createElement('a');
      link.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${resultsImport.excel_base64}`;
      link.download = `Reporte_Errores_Importacion_${new Date().getTime()}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Procesos de Crédito</h2>
        <p>Seleccione y ejecute procesos masivos en la cartera de créditos.</p>
      </header>

      <div style={{ marginBottom: '24px' }}>
        <label className="form-label" style={{ fontWeight: 'bold' }}>Seleccione el tipo de proceso:</label>
        <select 
          className="form-input" 
          value={processType} 
          onChange={(e) => setProcessType(e.target.value)}
          style={{ maxWidth: '400px', cursor: 'pointer' }}
        >
          <option value="MASIVA_ARCHIVOS">Carga Masiva de Archivos (Clásico)</option>
          <option value="IMPORTACION_CREDITOS">Importación Masiva de Créditos (Proveedores)</option>
        </select>
      </div>

      {processType === 'MASIVA_ARCHIVOS' && (
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

            <button className="btn-primary" onClick={handleUploadFiles} disabled={loadingFiles || files.length === 0} style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
              {loadingFiles ? (
                <>
                  <svg className="spinner" viewBox="0 0 50 50" style={{ width: '20px', height: '20px', stroke: 'currentColor', strokeWidth: 4, fill: 'none', animation: 'spin 1s linear infinite' }}><circle cx="25" cy="25" r="20" strokeDasharray="90 150"></circle></svg>
                  Procesando...
                </>
              ) : "Subir y Procesar Archivos"}
            </button>
          </div>

          {resultsFiles && (
            <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
              <h3 style={{ marginBottom: '16px' }}>Resultados del Procesamiento</h3>
              
              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontWeight: '500', color: 'var(--success)' }}>Procesados con éxito:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsFiles.procesados?.length || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: '500', color: 'var(--danger)' }}>Errores encontrados:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsFiles.errores?.length || 0}</span>
                </div>
              </div>

              {resultsFiles.errores && resultsFiles.errores.length > 0 && (
                <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <table className="data-table" style={{ fontSize: '13px' }}>
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left' }}>Archivo</th>
                        <th style={{ textAlign: 'left' }}>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resultsFiles.errores.map((err, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ color: 'var(--danger)', wordBreak: 'break-all' }}>{err.archivo}</td>
                          <td style={{ color: 'var(--text-secondary)' }}>{err.error}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              
              {resultsFiles.procesados && resultsFiles.procesados.length > 0 && (
                <div style={{ maxHeight: '200px', overflowY: 'auto', marginTop: '20px' }}>
                  <h4 style={{ fontSize: '13px', marginBottom: '8px', color: 'var(--success)' }}>Archivos vinculados</h4>
                  <ul style={{ fontSize: '12px', color: 'var(--text-secondary)', paddingLeft: '20px' }}>
                    {resultsFiles.procesados.map((proc, i) => (
                      <li key={i}>{proc.archivo} → Crédito ID: {proc.credito_id} {proc.transferencia_id ? `(Transf. ${proc.transferencia_id})` : ''}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {processType === 'IMPORTACION_CREDITOS' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
          <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}>
            <h3 style={{ marginBottom: '16px' }}>Importación Masiva desde Proveedor</h3>
            
            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label className="form-label">Proveedor de Origen</label>
              <select 
                className="form-input" 
                value={proveedor} 
                onChange={(e) => setProveedor(e.target.value)}
              >
                <option value="QUOTA_CFL">Quota de Estudio CFL</option>
                <option value="WEB_CARGA_CFL">Web Carga de Estudio CFL</option>
              </select>
            </div>

            {proveedor === 'QUOTA_CFL' && (
              <>
                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label">Archivo de Clientes (Excel)</label>
                  <input type="file" className="form-input" accept=".xlsx,.xls" onChange={(e) => setClientesFile(e.target.files[0])} />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label">Archivo de Créditos (Excel)</label>
                  <input type="file" className="form-input" accept=".xlsx,.xls" onChange={(e) => setCreditosFile(e.target.files[0])} />
                </div>

                <div className="form-group" style={{ marginBottom: '16px' }}>
                  <label className="form-label">Archivo de Transferencias (CSV)</label>
                  <input type="file" className="form-input" accept=".csv" onChange={(e) => setTransfFile(e.target.files[0])} />
                </div>
              </>
            )}

            {proveedor === 'WEB_CARGA_CFL' && (
              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label">Archivo de Importación Web Carga (.txt)</label>
                <input type="file" className="form-input" accept=".txt" onChange={(e) => setWebCargaFile(e.target.files[0])} />
              </div>
            )}

            <div className="form-group" style={{ marginBottom: '24px' }}>
              <label className="form-label">Archivos de Legajos y Comprobantes (PDFs o ZIP)</label>
              <input type="file" className="form-input" multiple accept=".zip,.pdf" onChange={(e) => setArchivosImport(Array.from(e.target.files))} />
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>Puedes subir varios PDFs o comprimirlos todos en un único archivo ZIP.</p>
            </div>

            <button className="btn-primary" onClick={handleImportCreditos} disabled={loadingImport || (proveedor === 'QUOTA_CFL' && (!clientesFile || !creditosFile || !transfFile)) || (proveedor === 'WEB_CARGA_CFL' && !webCargaFile)} style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px' }}>
              {loadingImport ? (
                <>
                  <svg className="spinner" viewBox="0 0 50 50" style={{ width: '20px', height: '20px', stroke: 'currentColor', strokeWidth: 4, fill: 'none', animation: 'spin 1s linear infinite' }}><circle cx="25" cy="25" r="20" strokeDasharray="90 150"></circle></svg>
                  Procesando Importación...
                </>
              ) : "Iniciar Importación Masiva"}
            </button>
          </div>

          {resultsImport && (
            <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)', display: 'flex', flexDirection: 'column' }}>
              <h3 style={{ marginBottom: '16px' }}>Resultados de la Importación</h3>
              
              <div style={{ marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Nuevos Clientes:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.nuevos_clientes || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Clientes Actualizados:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.clientes_actualizados || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--success)' }}>Nuevos Créditos:</span>
                  <span style={{ fontWeight: 'bold', color: 'var(--success)' }}>{resultsImport.resumen?.nuevos_creditos || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Créditos Pre-existentes (Omitidos):</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.creditos_existentes || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Transferencias Importadas:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.transferencias_importadas || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Documentos Vinculados:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.archivos_procesados || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '4px' }}>
                  <span style={{ color: 'var(--success)' }}>Pasados a FIRMADO:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.pasados_a_firmado || 0}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--success)' }}>Pasados a ACTIVO:</span>
                  <span style={{ fontWeight: 'bold' }}>{resultsImport.resumen?.pasados_a_activo || 0}</span>
                </div>
              </div>

              {resultsImport.errores_count > 0 && (
                <div style={{ marginTop: 'auto', padding: '16px', backgroundColor: 'rgba(239, 68, 68, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid var(--danger-color)' }}>
                  <h4 style={{ color: 'var(--danger-color)', marginBottom: '8px' }}>Se encontraron {resultsImport.errores_count} errores</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                    Ocurrieron problemas con algunos registros que no pudieron ser importados. Descargue el reporte para ver el detalle exacto.
                  </p>
                  <button onClick={downloadExcelErrors} style={{ width: '100%', padding: '10px', backgroundColor: 'var(--danger-color)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', cursor: 'pointer', fontWeight: 'bold' }}>
                    📥 Descargar Reporte de Errores (Excel)
                  </button>
                </div>
              )}
              
              {resultsImport.errores_count === 0 && (
                <div style={{ marginTop: 'auto', padding: '16px', backgroundColor: 'rgba(34, 197, 94, 0.1)', borderRadius: 'var(--radius-md)', border: '1px solid var(--success-color)', textAlign: 'center' }}>
                  <span style={{ fontSize: '24px' }}>🎉</span>
                  <h4 style={{ color: 'var(--success-color)', marginTop: '8px' }}>¡Importación Perfecta!</h4>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Todos los registros fueron procesados exitosamente sin ningún error.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
};

export default CreditProcessesPage;
