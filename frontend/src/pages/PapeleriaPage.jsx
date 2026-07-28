import React, { useState, useEffect, useRef } from 'react';
import axiosClient from '../api/axiosClient';

const PapeleriaPage = ({ categoria = 'creditos' }) => {
  const [socios, setSocios] = useState([]);
  const [documentos, setDocumentos] = useState([]);
  const [companyInfo, setCompanyInfo] = useState(null);
  const [selectedSocio, setSelectedSocio] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingActions, setLoadingActions] = useState({});

  // Variables modal state
  const [systemFields, setSystemFields] = useState([]);
  const [variablesModalOpen, setVariablesModalOpen] = useState(false);
  const [selectedDocForVariables, setSelectedDocForVariables] = useState(null);
  const [docVariables, setDocVariables] = useState([]);
  const [savingVariables, setSavingVariables] = useState(false);

  // Replace file state
  const fileInputRef = useRef(null);
  const [replacingDocId, setReplacingDocId] = useState(null);

  // Edit socio state
  const [editingSocioDocId, setEditingSocioDocId] = useState(null);

  useEffect(() => {
    fetchCompanyInfo();
    fetchSocios();
    fetchSystemFields();
  }, []);

  useEffect(() => {
    fetchDocumentos();
  }, [categoria]);

  const fetchCompanyInfo = async () => {
    try {
      const res = await axiosClient.get('/api/v1/system/company');
      setCompanyInfo(res.data);
    } catch (error) {
      console.error("Error fetching company info:", error);
    }
  };

  const fetchSocios = async () => {
    try {
      const res = await axiosClient.get('/api/v1/auxiliares/socios');
      setSocios(res.data);
    } catch (error) {
      console.error("Error fetching socios:", error);
    }
  };

  const fetchDocumentos = async () => {
    try {
      const res = await axiosClient.get(`/api/v1/papeleria?categoria=${categoria}`);
      setDocumentos(res.data);
    } catch (error) {
      console.error("Error fetching documentos:", error);
    }
  };

  const fetchSystemFields = async () => {
    try {
      const res = await axiosClient.get('/api/v1/papeleria/system_fields');
      setSystemFields(res.data);
    } catch (error) {
      console.error("Error fetching system fields:", error);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (selectedSocio === '' || !file) {
      alert("Por favor seleccione un socio comercial y un archivo.");
      return;
    }

    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'doc' && ext !== 'docx') {
      alert("Solo se permiten archivos Word (.doc, .docx)");
      return;
    }

    const formData = new FormData();
    formData.append('socio_id', selectedSocio);
    formData.append('categoria', categoria);
    formData.append('file', file);

    setLoading(true);
    try {
      await axiosClient.post('/api/v1/papeleria/upload', formData);
      alert("Documento subido correctamente.");
      setFile(null);
      document.getElementById('fileInput').value = '';
      fetchDocumentos();
    } catch (error) {
      alert("Error al subir el documento: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const triggerReplace = (docId) => {
    setReplacingDocId(docId);
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleSocioChange = async (docId, newSocioId) => {
    try {
      await axiosClient.patch(`/api/v1/papeleria/${docId}/socio`, { socio_id: newSocioId });
      setEditingSocioDocId(null);
      fetchDocumentos();
    } catch (error) {
      alert("Error al actualizar socio: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleReplaceFileChange = async (e) => {
    if (e.target.files.length === 0 || !replacingDocId) return;
    const replaceFile = e.target.files[0];
    
    const ext = replaceFile.name.split('.').pop().toLowerCase();
    if (ext !== 'doc' && ext !== 'docx') {
      alert("Solo se permiten archivos Word (.doc, .docx)");
      e.target.value = '';
      setReplacingDocId(null);
      return;
    }

    const formData = new FormData();
    formData.append('file', replaceFile);

    setLoadingActions(prev => ({ ...prev, [`replace-${replacingDocId}`]: true }));
    try {
      await axiosClient.put(`/api/v1/papeleria/${replacingDocId}/file`, formData);
      alert("Documento reemplazado correctamente.");
      fetchDocumentos();
    } catch (error) {
      alert("Error al reemplazar el documento: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoadingActions(prev => ({ ...prev, [`replace-${replacingDocId}`]: false }));
      setReplacingDocId(null);
      e.target.value = '';
    }
  };

  const handleDownload = async (docId, fileName) => {
    setLoadingActions(prev => ({ ...prev, [`download-${docId}`]: true }));
    try {
      const response = await axiosClient.get(`/api/v1/papeleria/download/${docId}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      alert("Error al descargar el documento.");
    } finally {
      setLoadingActions(prev => ({ ...prev, [`download-${docId}`]: false }));
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("¿Está seguro de eliminar este documento?")) return;
    setLoadingActions(prev => ({ ...prev, [`delete-${docId}`]: true }));
    try {
      await axiosClient.delete(`/api/v1/papeleria/${docId}`);
      alert("Documento eliminado.");
      fetchDocumentos();
    } catch (error) {
      alert("Error al eliminar el documento.");
    } finally {
      setLoadingActions(prev => ({ ...prev, [`delete-${docId}`]: false }));
    }
  };

  const handleReorder = async (newList) => {
    try {
      const payload = {
        documentos: newList.map((d, index) => ({ id: d.id, orden: index }))
      };
      await axiosClient.post('/api/v1/papeleria/reorder', payload);
    } catch (error) {
      console.error("Error al reordenar", error);
    }
  };

  const moveUp = (index) => {
    if (index === 0) return;
    const newDocs = [...documentos];
    const temp = newDocs[index - 1];
    newDocs[index - 1] = newDocs[index];
    newDocs[index] = temp;
    setDocumentos(newDocs);
    handleReorder(newDocs);
  };

  const moveDown = (index) => {
    if (index === documentos.length - 1) return;
    const newDocs = [...documentos];
    const temp = newDocs[index + 1];
    newDocs[index + 1] = newDocs[index];
    newDocs[index] = temp;
    setDocumentos(newDocs);
    handleReorder(newDocs);
  };

  // Variables Modal Logic
  const openVariablesModal = async (doc) => {
    setLoadingActions(prev => ({ ...prev, [`vars-${doc.id}`]: true }));
    setDocVariables([]);
    try {
      const res = await axiosClient.get(`/api/v1/papeleria/${doc.id}/variables`);
      const sortedVars = [...res.data].sort((a, b) => {
        const aEmpty = !a.system_field || String(a.system_field).trim() === '' || !systemFields.some(sf => sf.value === a.system_field);
        const bEmpty = !b.system_field || String(b.system_field).trim() === '' || !systemFields.some(sf => sf.value === b.system_field);
        if (aEmpty && !bEmpty) return -1;
        if (!aEmpty && bEmpty) return 1;
        return 0;
      });
      setDocVariables(sortedVars);
      setSelectedDocForVariables(doc);
      setVariablesModalOpen(true);
    } catch (error) {
      console.error("Error fetching variables", error);
    } finally {
      setLoadingActions(prev => ({ ...prev, [`vars-${doc.id}`]: false }));
    }
  };

  const closeVariablesModal = () => {
    setVariablesModalOpen(false);
    setSelectedDocForVariables(null);
    setDocVariables([]);
  };

  const addVariableRow = () => {
    setDocVariables([...docVariables, { placeholder: '', system_field: '' }]);
  };

  const removeVariableRow = (index) => {
    const newVars = [...docVariables];
    newVars.splice(index, 1);
    setDocVariables(newVars);
  };

  const updateVariable = (index, field, value) => {
    const newVars = [...docVariables];
    newVars[index][field] = value;
    setDocVariables(newVars);
  };

  const saveVariables = async () => {
    // Validate
    if (docVariables.some(v => !v.placeholder || !v.placeholder.trim())) {
      alert("Por favor asegúrese de que todos los marcadores tengan un nombre válido.");
      return;
    }
    setSavingVariables(true);
    try {
      await axiosClient.post(`/api/v1/papeleria/${selectedDocForVariables.id}/variables`, {
        variables: docVariables
      });
      alert("Variables guardadas exitosamente.");
      closeVariablesModal();
    } catch (error) {
      alert("Error al guardar las variables.");
    } finally {
      setSavingVariables(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Papelería - {categoria === 'creditos' ? 'Créditos' : 'Ventas de Cartera'}</h2>
        <p>Gestión de documentos Word (.doc, .docx) asociados a Socios Comerciales para {categoria === 'creditos' ? 'créditos' : 'ventas de cartera'}.</p>
      </header>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
        <div className="form-container glass-panel">
          <form onSubmit={handleUpload}>
            <div className="form-group">
              <label>Socio Comercial</label>
              <select 
                value={selectedSocio} 
                onChange={(e) => setSelectedSocio(e.target.value)}
                required
              >
                <option value="">-- Seleccione un Socio --</option>
                <option value="0" style={{ fontWeight: 'bold' }}>
                  {companyInfo ? companyInfo.razon_social : 'Empresa Dueña del Sistema'}
                </option>
                {socios.filter(socio => !companyInfo || socio.cuit !== companyInfo.cuit).map(socio => (
                  <option key={socio.id} value={socio.id}>{socio.razon_social} (CUIT: {socio.cuit})</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Documento Word (.doc, .docx)</label>
              <input 
                id="fileInput"
                type="file" 
                accept=".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
                onChange={handleFileChange} 
                required 
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Subiendo..." : "Subir Documento"}
            </button>
          </form>
        </div>

        <div className="results-container glass-panel">
          <div className="results-header">
            <h3>Documentos Cargados</h3>
          </div>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ textAlign: 'center' }}>Orden</th>
                  <th style={{ textAlign: 'center' }}>Socio Comercial</th>
                  <th style={{ textAlign: 'center' }}>Archivo</th>
                  <th style={{ textAlign: 'center' }}>Fecha de Subida</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {documentos.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="text-center empty-state">No hay documentos subidos.</td>
                  </tr>
                ) : (
                  documentos.map((doc, index) => (
                    <tr key={doc.id}>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
                          <button 
                            className="btn-secondary" 
                            style={{ padding: '2px 6px', fontSize: '10px' }}
                            onClick={() => moveUp(index)}
                            disabled={index === 0}
                          >▲</button>
                          <span>{index + 1}</span>
                          <button 
                            className="btn-secondary" 
                            style={{ padding: '2px 6px', fontSize: '10px' }}
                            onClick={() => moveDown(index)}
                            disabled={index === documentos.length - 1}
                          >▼</button>
                        </div>
                      </td>
                      <td>
                        {editingSocioDocId === doc.id ? (
                          <select 
                            defaultValue={doc.socio_id}
                            onChange={(e) => handleSocioChange(doc.id, e.target.value)}
                            onBlur={() => setEditingSocioDocId(null)}
                            autoFocus
                            style={{ padding: '4px', borderRadius: '4px', border: '1px solid var(--border-color)', background: 'var(--bg-color)', color: 'var(--text-color)' }}
                          >
                            <option value="0" style={{ fontWeight: 'bold' }}>
                              {companyInfo ? companyInfo.razon_social : 'Empresa Dueña del Sistema'}
                            </option>
                            {socios.filter(s => !companyInfo || s.cuit !== companyInfo.cuit).map(s => (
                              <option key={s.id} value={s.id}>{s.razon_social}</option>
                            ))}
                          </select>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {doc.socio_nombre}
                            <button 
                              onClick={() => setEditingSocioDocId(doc.id)} 
                              className="btn-secondary" 
                              style={{ padding: '2px 6px', fontSize: '10px' }}
                              title="Editar Socio"
                            >
                              ✏️
                            </button>
                          </div>
                        )}
                      </td>
                      <td>{doc.nombre_archivo}</td>
                      <td>{new Date(doc.fecha_subida).toLocaleString('es-AR')}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', justifyContent: 'center' }}>
                          <button 
                            onClick={() => openVariablesModal(doc)}
                            className="btn-primary" 
                            title="Mapear Variables"
                            style={{ padding: '6px 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                            disabled={loadingActions[`vars-${doc.id}`]}
                          >
                            {loadingActions[`vars-${doc.id}`] ? '⏳' : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                                <line x1="16" y1="13" x2="8" y2="13"></line>
                                <line x1="16" y1="17" x2="8" y2="17"></line>
                                <polyline points="10 9 9 9 8 9"></polyline>
                              </svg>
                            )}
                          </button>
                          <button 
                            onClick={() => handleDownload(doc.id, doc.nombre_archivo)}
                            className="btn-secondary" 
                            title="Descargar documento"
                            style={{ padding: '6px 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                            disabled={loadingActions[`download-${doc.id}`]}
                          >
                            {loadingActions[`download-${doc.id}`] ? '⏳' : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="7 10 12 15 17 10"></polyline>
                                <line x1="12" y1="15" x2="12" y2="3"></line>
                              </svg>
                            )}
                          </button>
                          <button 
                            onClick={() => triggerReplace(doc.id)}
                            className="btn-secondary" 
                            title="Reemplazar archivo"
                            style={{ padding: '6px 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                            disabled={loadingActions[`replace-${doc.id}`]}
                          >
                            {loadingActions[`replace-${doc.id}`] ? '⏳' : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                <polyline points="17 8 12 3 7 8"></polyline>
                                <line x1="12" y1="3" x2="12" y2="15"></line>
                              </svg>
                            )}
                          </button>
                          <button 
                            onClick={() => handleDelete(doc.id)}
                            className="btn-danger" 
                            title="Eliminar documento"
                            style={{ padding: '6px 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                            disabled={loadingActions[`delete-${doc.id}`]}
                          >
                            {loadingActions[`delete-${doc.id}`] ? '⏳' : (
                              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6"></polyline>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                <line x1="10" y1="11" x2="10" y2="17"></line>
                                <line x1="14" y1="11" x2="14" y2="17"></line>
                              </svg>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {variablesModalOpen && selectedDocForVariables && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div className="modal-content glass-panel" style={{ width: '600px', maxWidth: '90%', maxHeight: '90vh', overflowY: 'auto', padding: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0 }}>Variables - {selectedDocForVariables.nombre_archivo}</h3>
              <button onClick={closeVariablesModal} style={{ background: 'transparent', border: 'none', fontSize: '1.5rem', cursor: 'pointer', color: 'var(--text-color)' }}>&times;</button>
            </div>

            <p style={{ marginBottom: '1rem', fontSize: '0.9rem', color: 'var(--text-color-muted)' }}>
              Escriba el nombre del marcador tal cual está en el Word (sin llaves). Ej: NOMBRE_CLIENTE.<br/>
              Luego seleccione el campo del sistema que lo reemplazará.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
              {docVariables.map((v, i) => (
                <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input 
                    type="text" 
                    placeholder="Marcador (ej. DNI)" 
                    value={v.placeholder} 
                    onChange={(e) => updateVariable(i, 'placeholder', e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <select 
                    value={v.system_field} 
                    onChange={(e) => updateVariable(i, 'system_field', e.target.value)}
                    style={{ flex: 2 }}
                  >
                    <option value="">-- Seleccionar Campo --</option>
                    {systemFields.map(sf => (
                      <option key={sf.value} value={sf.value}>{sf.label}</option>
                    ))}
                  </select>
                  <button onClick={() => removeVariableRow(i)} className="btn-danger" style={{ padding: '8px' }}>X</button>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <button onClick={addVariableRow} className="btn-secondary">+ Añadir Variable</button>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={closeVariablesModal} className="btn-secondary">Cancelar</button>
                <button onClick={saveVariables} className="btn-primary" disabled={savingVariables}>
                  {savingVariables ? "Guardando..." : "Guardar"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <input 
        type="file" 
        ref={fileInputRef} 
        style={{ display: 'none' }} 
        accept=".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
        onChange={handleReplaceFileChange} 
      />
    </section>
  );
};

export default PapeleriaPage;
