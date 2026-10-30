import { useState, useEffect, useRef } from 'react';
import { 
  X, 
  UploadCloud, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Download, 
  Trash2, 
  FileSignature,
  FileCheck
} from 'lucide-react';
import axiosClient from '../api/axiosClient';

const formatFileSize = (bytes) => {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
};

const formatFecha = (isoString) => {
  if (!isoString) return '-';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
};

const CarteraContratoModal = ({ cartera, onClose, onSuccess }) => {
  const [documentos, setDocumentos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [esContratoFirmado, setEsContratoFirmado] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const fetchDocumentos = async () => {
    setLoading(true);
    try {
      const res = await axiosClient.get(`/api/v1/carteras/${cartera.id}/documentos`);
      setDocumentos(res.data || []);
    } catch (error) {
      alert("Error cargando contratos: " + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (cartera?.id) {
      fetchDocumentos();
    }
  }, [cartera?.id]);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('es_contrato_firmado', esContratoFirmado);

    try {
      await axiosClient.post(`/api/v1/carteras/${cartera.id}/documentos`, formData);
      setFile(null);
      setEsContratoFirmado(true);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await fetchDocumentos();
      if (onSuccess) onSuccess();
    } catch (error) {
      alert("Error subiendo el archivo:\n" + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, nombreArchivo) => {
    if (!window.confirm(`¿Estás seguro de eliminar el contrato "${nombreArchivo}"?\n\nSi no quedan contratos firmados, se volverá a habilitar la descarga de las plantillas en Word y PDF.`)) return;
    try {
      await axiosClient.delete(`/api/v1/carteras/${cartera.id}/documentos/${docId}`);
      await fetchDocumentos();
      if (onSuccess) onSuccess();
    } catch (error) {
      alert("Error eliminando contrato: " + (error.response?.data?.detail || error.message));
    }
  };

  const handleDownload = (docId, nombreArchivo) => {
    axiosClient.get(`/api/v1/carteras/${cartera.id}/documentos/${docId}/download`, { responseType: 'blob' })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', nombreArchivo);
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((error) => alert("Error descargando el archivo: " + (error.response?.data?.detail || error.message)));
  };

  const handleDownloadMerged = () => {
    axiosClient.get(`/api/v1/carteras/${cartera.id}/documentos/merged/download`, { responseType: 'blob' })
      .then((response) => {
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Contrato_Firmado_Cartera_${cartera.id}.pdf`);
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((error) => alert("Error descargando contrato unificado: " + (error.response?.data?.detail || error.message)));
  };

  const tienePdf = documentos.some(d => (d.nombre_archivo || '').toLowerCase().endsWith('.pdf'));

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)', zIndex: 1100,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px',
      backdropFilter: 'blur(6px)', animation: 'fadeIn 0.2s ease',
      boxSizing: 'border-box'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '680px', maxHeight: 'calc(100vh - 32px)',
        display: 'flex', flexDirection: 'column',
        position: 'relative', padding: '20px', borderRadius: '14px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        background: '#0F172A',
        overflowY: 'auto',
        boxSizing: 'border-box'
      }}>
        {/* Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
          marginBottom: '12px', borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '10px',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '38px', height: '38px', borderRadius: '8px',
              backgroundColor: 'rgba(99, 102, 241, 0.15)', display: 'flex',
              alignItems: 'center', justifyContent: 'center', color: '#818cf8',
              border: '1px solid rgba(99, 102, 241, 0.25)', flexShrink: 0
            }}>
              <FileSignature size={22} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <h2 style={{ margin: 0, fontSize: '17px', fontWeight: 700, color: '#F8FAFC' }}>
                  Contratos Firmados
                </h2>
                <span style={{
                  fontSize: '11px', background: 'rgba(99, 102, 241, 0.2)', color: '#a5b4fc',
                  padding: '2px 7px', borderRadius: '5px', fontWeight: 600
                }}>
                  Cartera #{cartera.id}
                </span>
                <span style={{
                  fontSize: '10px', 
                  background: cartera.tipo_operacion === 'VENTA' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: cartera.tipo_operacion === 'VENTA' ? '#60a5fa' : '#34d399',
                  padding: '2px 7px', borderRadius: '5px', fontWeight: 600, textTransform: 'uppercase'
                }}>
                  {cartera.tipo_operacion}
                </span>
              </div>
              <div style={{ fontSize: '12px', color: '#94A3B8', marginTop: '2px' }}>
                <span style={{ color: '#E2E8F0', fontWeight: 500 }}>{cartera.nombre}</span>
                {cartera.socio && ` • ${cartera.socio}`}
                {cartera.fecha_compra && ` • ${cartera.fecha_compra}`}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.05)', border: 'none', borderRadius: '6px',
              color: '#94A3B8', width: '30px', height: '30px', display: 'flex',
              alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
              transition: 'all 0.15s'
            }}
            onMouseOver={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.12)'; e.currentTarget.style.color = '#fff'; }}
            onMouseOut={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#94A3B8'; }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Informative notice */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          background: 'rgba(59, 130, 246, 0.08)',
          border: '1px solid rgba(59, 130, 246, 0.2)',
          borderRadius: '6px', padding: '8px 12px', marginBottom: '12px',
          fontSize: '12px', color: '#93c5fd', lineHeight: '1.35', flexShrink: 0
        }}>
          <AlertCircle size={16} style={{ flexShrink: 0, color: '#60a5fa' }} />
          <div>
            <strong>Control de Contratos:</strong> Al adjuntar el contrato firmado, queda resguardado y <strong>se bloquea automáticamente la descarga de borradores (PDF y Word)</strong>.
          </div>
        </div>

        {/* Upload Box */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '8px', padding: '12px', marginBottom: '14px',
          flexShrink: 0
        }}>
          <input
            type="file"
            ref={fileInputRef}
            id="carteraFileInput"
            accept=".pdf,.doc,.docx,image/png,image/jpeg,image/jpg"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />

          {/* Clickable selector / dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            style={{
              border: `2px dashed ${isDragging ? '#6366f1' : file ? 'rgba(16, 185, 129, 0.5)' : 'rgba(255, 255, 255, 0.15)'}`,
              borderRadius: '6px',
              padding: '12px 14px',
              textAlign: 'center',
              cursor: 'pointer',
              background: isDragging ? 'rgba(99, 102, 241, 0.1)' : file ? 'rgba(16, 185, 129, 0.05)' : 'rgba(0, 0, 0, 0.2)',
              transition: 'all 0.15s',
              marginBottom: '10px'
            }}
          >
            {file ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <FileCheck size={22} color="#10b981" />
                <div style={{ textAlign: 'left' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#F1F5F9' }}>
                    {file.name}
                  </div>
                  <div style={{ fontSize: '11px', color: '#94A3B8' }}>
                    {formatFileSize(file.size)} • Clic para cambiar archivo
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px' }}>
                <UploadCloud size={22} color="#818cf8" />
                <div>
                  <span style={{ fontSize: '13px', fontWeight: 500, color: '#E2E8F0' }}>
                    Clic o arrastra aquí el contrato firmado
                  </span>
                  <span style={{ fontSize: '11px', color: '#64748B', display: 'block' }}>
                    PDF, Word (.docx, .doc), o imágenes (PNG, JPG)
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Form Actions */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#E2E8F0', cursor: 'pointer', userSelect: 'none' }}>
              <input
                type="checkbox"
                checked={esContratoFirmado}
                onChange={(e) => setEsContratoFirmado(e.target.checked)}
                style={{ width: '15px', height: '15px', accentColor: '#6366f1', cursor: 'pointer' }}
              />
              <span>Marcar como <strong>Contrato Firmado</strong></span>
            </label>

            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                padding: '7px 16px', fontSize: '12px', fontWeight: 600,
                borderRadius: '6px', border: 'none',
                background: !file || uploading ? 'rgba(255,255,255,0.08)' : '#4F46E5',
                color: !file || uploading ? '#64748B' : '#ffffff',
                cursor: !file || uploading ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s'
              }}
            >
              <UploadCloud size={15} />
              {uploading ? "Subiendo..." : "Subir Contrato"}
            </button>
          </div>
        </div>

        {/* Attachments Section Header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          marginBottom: '8px', flexShrink: 0
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 600, color: '#F1F5F9' }}>
              Documentos Adjuntos
            </h4>
            <span style={{
              fontSize: '11px', background: documentos.length > 0 ? 'rgba(16, 185, 129, 0.2)' : 'rgba(255, 255, 255, 0.1)',
              color: documentos.length > 0 ? '#34d399' : '#94A3B8',
              padding: '1px 7px', borderRadius: '10px', fontWeight: 600
            }}>
              {documentos.length}
            </span>
          </div>

          {documentos.length > 0 && tienePdf && (
            <button
              onClick={handleDownloadMerged}
              style={{
                display: 'flex', alignItems: 'center', gap: '5px',
                padding: '5px 10px', fontSize: '11px', fontWeight: 500,
                borderRadius: '6px', border: '1px solid rgba(99, 102, 241, 0.3)',
                background: 'rgba(99, 102, 241, 0.15)', color: '#c7d2fe',
                cursor: 'pointer', transition: 'all 0.15s'
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.25)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'rgba(99, 102, 241, 0.15)'}
            >
              <FileText size={13} color="#818cf8" />
              Descargar Contrato Completo (PDF)
            </button>
          )}
        </div>

        {/* Attachments Table Container */}
        <div style={{
          width: '100%',
          overflowX: 'hidden',
          overflowY: 'auto',
          maxHeight: '190px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '8px',
          background: 'rgba(10, 15, 29, 0.7)',
          boxSizing: 'border-box'
        }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '24px', color: '#94A3B8', fontSize: '12px' }}>
              Cargando documentos...
            </div>
          ) : documentos.length === 0 ? (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
              padding: '24px 16px', color: '#64748B', gap: '6px'
            }}>
              <FileText size={26} strokeWidth={1.5} color="#475569" />
              <div style={{ fontSize: '12px', fontWeight: 500, color: '#94A3B8' }}>
                No hay contratos firmados adjuntos para esta cartera.
              </div>
              <div style={{ fontSize: '11px', color: '#64748B' }}>
                Selecciona o arrastra un archivo arriba para adjuntarlo.
              </div>
            </div>
          ) : (
            <table style={{
              width: '100%',
              tableLayout: 'fixed',
              borderCollapse: 'collapse',
              fontSize: '12px',
              textAlign: 'left'
            }}>
              <colgroup>
                <col style={{ width: '45%' }} />
                <col style={{ width: '18%' }} />
                <col style={{ width: '23%' }} />
                <col style={{ width: '14%' }} />
              </colgroup>
              <thead>
                <tr style={{
                  background: '#0B1120',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                  color: '#94A3B8',
                  fontSize: '11px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  position: 'sticky',
                  top: 0,
                  zIndex: 2
                }}>
                  <th style={{ padding: '9px 12px', textAlign: 'left' }}>Archivo</th>
                  <th style={{ padding: '9px 4px', textAlign: 'center' }}>Estado</th>
                  <th style={{ padding: '9px 4px', textAlign: 'center' }}>Fecha Subida</th>
                  <th style={{ padding: '9px 6px', textAlign: 'center' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {documentos.map((doc, idx) => {
                  const isPdf = (doc.nombre_archivo || '').toLowerCase().endsWith('.pdf');
                  return (
                    <tr
                      key={doc.id}
                      style={{
                        borderBottom: idx < documentos.length - 1 ? '1px solid rgba(255, 255, 255, 0.05)' : 'none',
                        transition: 'background-color 0.15s'
                      }}
                      onMouseOver={(e) => e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)'}
                      onMouseOut={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      {/* Name */}
                      <td style={{ padding: '8px 12px', overflow: 'hidden' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                          <FileText size={18} style={{ flexShrink: 0, color: isPdf ? '#f87171' : '#60a5fa' }} />
                          <div style={{ minWidth: 0, flex: 1, overflow: 'hidden' }}>
                            <div style={{
                              fontWeight: 500, color: '#F1F5F9',
                              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                            }} title={doc.nombre_archivo}>
                              {doc.nombre_archivo}
                            </div>
                            <div style={{ fontSize: '10px', color: '#64748B' }}>
                              {isPdf ? 'Documento PDF' : 'Word / Adjunto'}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Status */}
                      <td style={{ padding: '8px 4px', textAlign: 'center' }}>
                        {doc.es_contrato_firmado ? (
                          <span style={{
                            display: 'inline-flex', alignItems: 'center', gap: '3px',
                            background: 'rgba(16, 185, 129, 0.15)', color: '#34d399',
                            border: '1px solid rgba(16, 185, 129, 0.3)',
                            padding: '2px 7px', borderRadius: '10px', fontSize: '10px', fontWeight: 600
                          }}>
                            <CheckCircle2 size={11} />
                            Firmado
                          </span>
                        ) : (
                          <span style={{
                            display: 'inline-block',
                            background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8',
                            border: '1px solid rgba(148, 163, 184, 0.25)',
                            padding: '2px 7px', borderRadius: '10px', fontSize: '10px', fontWeight: 500
                          }}>
                            Adjunto
                          </span>
                        )}
                      </td>

                      {/* Date */}
                      <td style={{ padding: '8px 4px', textAlign: 'center', color: '#94A3B8', fontSize: '11px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {formatFecha(doc.fecha_subida)}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '8px 6px', textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '5px', justifyContent: 'center', alignItems: 'center' }}>
                          <button
                            onClick={() => handleDownload(doc.id, doc.nombre_archivo)}
                            title="Descargar contrato"
                            style={{
                              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                              width: '28px', height: '28px', borderRadius: '6px',
                              background: 'rgba(59, 130, 246, 0.15)', border: '1px solid rgba(59, 130, 246, 0.3)',
                              color: '#60a5fa', cursor: 'pointer', transition: 'all 0.15s', padding: 0
                            }}
                            onMouseOver={(e) => { e.currentTarget.style.background = '#2563eb'; e.currentTarget.style.color = '#fff'; }}
                            onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(59, 130, 246, 0.15)'; e.currentTarget.style.color = '#60a5fa'; }}
                          >
                            <Download size={13} />
                          </button>
                          <button
                            onClick={() => handleDelete(doc.id, doc.nombre_archivo)}
                            title="Eliminar contrato adjunto"
                            style={{
                              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                              width: '28px', height: '28px', borderRadius: '6px',
                              background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.25)',
                              color: '#f87171', cursor: 'pointer', transition: 'all 0.15s', padding: 0
                            }}
                            onMouseOver={(e) => { e.currentTarget.style.background = '#dc2626'; e.currentTarget.style.color = '#fff'; }}
                            onMouseOut={(e) => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.12)'; e.currentTarget.style.color = '#f87171'; }}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div style={{ marginTop: '14px', textAlign: 'right', flexShrink: 0 }}>
          <button
            className="btn-secondary"
            onClick={onClose}
            style={{
              padding: '6px 18px', fontSize: '12px', fontWeight: 500,
              borderRadius: '6px', cursor: 'pointer'
            }}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};

export default CarteraContratoModal;
