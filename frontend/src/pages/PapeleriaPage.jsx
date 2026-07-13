import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const PapeleriaPage = () => {
  const [socios, setSocios] = useState([]);
  const [documentos, setDocumentos] = useState([]);
  const [companyInfo, setCompanyInfo] = useState(null);
  const [selectedSocio, setSelectedSocio] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchCompanyInfo();
    fetchSocios();
    fetchDocumentos();
  }, []);

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
      const res = await axiosClient.get('/api/v1/papeleria');
      setDocumentos(res.data);
    } catch (error) {
      console.error("Error fetching documentos:", error);
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
    formData.append('file', file);

    setLoading(true);
    try {
      await axiosClient.post('/api/v1/papeleria/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("Documento subido correctamente.");
      setFile(null);
      document.getElementById('fileInput').value = ''; // Reset file input
      fetchDocumentos();
    } catch (error) {
      alert("Error al subir el documento: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (docId, fileName) => {
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
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("¿Está seguro de eliminar este documento?")) return;
    
    try {
      await axiosClient.delete(`/api/v1/papeleria/${docId}`);
      alert("Documento eliminado.");
      fetchDocumentos();
    } catch (error) {
      alert("Error al eliminar el documento.");
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Papelería</h2>
        <p>Gestión de documentos Word (.doc, .docx) asociados a Socios Comerciales.</p>
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
                {socios.map(socio => (
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
                  <th style={{ textAlign: 'center' }}>Socio Comercial</th>
                  <th style={{ textAlign: 'center' }}>Archivo</th>
                  <th style={{ textAlign: 'center' }}>Fecha de Subida</th>
                  <th style={{ textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {documentos.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="text-center empty-state">No hay documentos subidos.</td>
                  </tr>
                ) : (
                  documentos.map((doc) => (
                    <tr key={doc.id}>
                      <td>{doc.socio_nombre}</td>
                      <td>{doc.nombre_archivo}</td>
                      <td>{new Date(doc.fecha_subida).toLocaleString('es-AR')}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <button 
                            onClick={() => handleDownload(doc.id, doc.nombre_archivo)}
                            className="btn-secondary" 
                            title="Descargar documento"
                            style={{ padding: '6px 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                              <polyline points="7 10 12 15 17 10"></polyline>
                              <line x1="12" y1="15" x2="12" y2="3"></line>
                            </svg>
                          </button>
                          <button 
                            onClick={() => handleDelete(doc.id)}
                            className="btn-danger" 
                            title="Eliminar documento"
                            style={{ padding: '6px 10px', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                          >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="3 6 5 6 21 6"></polyline>
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                              <line x1="10" y1="11" x2="10" y2="17"></line>
                              <line x1="14" y1="11" x2="14" y2="17"></line>
                            </svg>
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
    </section>
  );
};

export default PapeleriaPage;
