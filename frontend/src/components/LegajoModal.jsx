import { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const formatCurrency = (num) => {
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS' }).format(num);
};

const LegajoModal = ({ creditoId, onClose }) => {
  const [documentos, setDocumentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [transferencias, setTransferencias] = useState([]);
  const [selectedTransferencia, setSelectedTransferencia] = useState('');
  const [isLegajoFirmado, setIsLegajoFirmado] = useState(false);

  const fetchDocumentos = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get(`/api/v1/creditos/${creditoId}/documentos`);
      setDocumentos(res.data);
    } catch (error) {
      alert("Error cargando documentos: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (creditoId) {
      fetchDocumentos();
      fetchTransferencias();
    }
  }, [creditoId]);

  const fetchTransferencias = async () => {
    try {
      const res = await axiosClient.get(`/api/v1/creditos/${creditoId}/transferencias`);
      setTransferencias(res.data);
    } catch (error) {
      console.error("Error cargando transferencias", error);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    if (selectedTransferencia) {
      formData.append('transferencia_id', selectedTransferencia);
    }
    formData.append('es_legajo_firmado', isLegajoFirmado);

    try {
      await axiosClient.post(`/api/v1/creditos/${creditoId}/documentos`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setFile(null);
      setSelectedTransferencia('');
      setIsLegajoFirmado(false);
      document.getElementById('legajoFileInput').value = '';
      fetchDocumentos();
    } catch (error) {
      alert("Error subiendo el archivo:\n" + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("¿Estás seguro de eliminar este documento?")) return;
    try {
      await axiosClient.delete(`/api/v1/creditos/${creditoId}/documentos/${docId}`);
      fetchDocumentos();
    } catch (error) {
      alert("Error eliminando documento: " + error.message);
    }
  };

  const handleDownload = (docId, nombreArchivo) => {
    axiosClient.get(`/api/v1/creditos/${creditoId}/documentos/${docId}/download`, { responseType: 'blob' })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', nombreArchivo);
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((error) => alert("Error descargando el archivo: " + error.message));
  };

  const handleDownloadMerged = () => {
    axiosClient.get(`/api/v1/creditos/${creditoId}/documentos/merged/download`, { responseType: 'blob' })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `legajo_credito_${creditoId}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((error) => alert("Error al generar el PDF combinado: " + error.message));
  };

  const handleGeneratePapeleria = async () => {
    setLoading(true);
    try {
      const response = await axiosClient.post(`/api/v1/papeleria/generar_por_credito/${creditoId}`, {}, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Papeleria_Credito_${creditoId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error(error);
      const backendError = error.response?.data?.detail || error.message;
      alert("Error al generar la papelería:\n" + backendError);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', display: 'flex', justifyContent: 'center',
      alignItems: 'center', zIndex: 9999, animation: 'fadeIn 0.3s'
    }}>
      <div className="modal-content glass-panel" onClick={e => e.stopPropagation()} style={{
        width: '600px', maxWidth: '90%', maxHeight: '80vh', overflowY: 'auto',
        padding: '24px', borderRadius: '12px', background: 'var(--surface-color)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>Legajo - Crédito #{creditoId}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--text-color)', fontSize: '24px', cursor: 'pointer' }}>&times;</button>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', alignItems: 'center' }}>
          <input 
            type="file" 
            id="legajoFileInput" 
            accept=".pdf,image/png,image/jpeg,image/jpg" 
            onChange={handleFileChange}
            style={{ flex: 1, padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <select 
              value={selectedTransferencia}
              onChange={(e) => setSelectedTransferencia(e.target.value)}
              style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)', color: 'white' }}
            >
              <option value="">Vincular a Transf. (Opcional)</option>
              {transferencias.map(t => (
                <option key={t.id} value={t.id}>
                  #{t.id} - {formatCurrency(t.monto)} - {t.banco || t.razon_social}
                </option>
              ))}
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', cursor: 'pointer' }}>
              <input 
                type="checkbox" 
                checked={isLegajoFirmado} 
                onChange={(e) => setIsLegajoFirmado(e.target.checked)} 
              />
              Marcar como Legajo Firmado
            </label>
          </div>
          <button className="btn-primary" onClick={handleUpload} disabled={!file || uploading} style={{ width: 'auto' }}>
            {uploading ? "Subiendo..." : "Subir Archivo"}
          </button>
        </div>

        <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.05)', padding: '12px', borderRadius: '8px' }}>
          <div>
            <h4 style={{ margin: '0 0 4px 0', fontSize: '14px' }}>Generador de Papelería</h4>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-color-muted)' }}>Autocompleta los documentos Word configurados para este crédito.</p>
          </div>
          <button className="btn-primary" onClick={handleGeneratePapeleria} disabled={loading} style={{ background: 'var(--success-color)' }}>
            🖨️ Generar y Descargar Papelería
          </button>
        </div>

        {documentos.length > 0 && (
          <div style={{ marginBottom: '16px', textAlign: 'right' }}>
            <button className="btn-secondary" onClick={handleDownloadMerged} style={{ background: 'var(--primary-color)' }}>
              📄 Descargar Legajo Completo (PDF)
            </button>
          </div>
        )}

        {loading ? (
          <p className="text-center">Cargando documentos...</p>
        ) : documentos.length === 0 ? (
          <p className="text-center" style={{ padding: '20px', opacity: 0.7 }}>No hay documentos en el legajo de este crédito.</p>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Archivo</th>
                  <th>Fecha Subida</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {documentos.map(doc => (
                  <tr key={doc.id}>
                    <td>
                      <div>{doc.nombre_archivo}</div>
                      {doc.transferencia_id && (
                        <div style={{ fontSize: '12px', color: 'var(--primary-color)', marginTop: '4px' }}>
                          🔗 Vinculado a Transf. #{doc.transferencia_id}
                        </div>
                      )}
                    </td>
                    <td>{new Date(doc.fecha_subida).toLocaleString('es-AR')}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button className="btn-secondary" onClick={() => handleDownload(doc.id, doc.nombre_archivo)} style={{ padding: '4px 8px', fontSize: '14px' }} title="Descargar">
                          ⬇️
                        </button>
                        <button className="btn-secondary" onClick={() => handleDelete(doc.id)} style={{ padding: '4px 8px', fontSize: '14px', color: 'var(--danger-color)' }} title="Eliminar">
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default LegajoModal;
