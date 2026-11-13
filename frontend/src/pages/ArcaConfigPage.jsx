import { useState, useEffect, useCallback } from 'react';
import axiosClient from '../api/axiosClient';
import { useAuthStore } from '../store/useAuthStore';

const STATUS_BADGES = {
  VIGENTE: {
    label: 'Vigente',
    bg: 'rgba(16, 185, 129, 0.15)',
    border: 'rgba(16, 185, 129, 0.4)',
    color: '#34d399',
    dot: '#10b981',
  },
  PROXIMO_A_VENCER: {
    label: 'Próximo a vencer (≤ 5 días)',
    bg: 'rgba(245, 158, 11, 0.15)',
    border: 'rgba(245, 158, 11, 0.4)',
    color: '#fbbf24',
    dot: '#f59e0b',
  },
  VENCIDO: {
    label: 'Vencido',
    bg: 'rgba(239, 68, 68, 0.15)',
    border: 'rgba(239, 68, 68, 0.4)',
    color: '#f87171',
    dot: '#ef4444',
  },
  SIN_CERTIFICADO: {
    label: 'Sin certificado',
    bg: 'rgba(148, 163, 184, 0.15)',
    border: 'rgba(148, 163, 184, 0.35)',
    color: '#94a3b8',
    dot: '#64748b',
  },
};

const formatIsoDate = (isoStr) => {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    if (Number.isNaN(d.getTime())) return isoStr;
    return d.toLocaleDateString('es-AR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoStr;
  }
};

const ArcaConfigPage = () => {
  const { user } = useAuthStore();
  const isAdmin =
    user?.rol === 'Administrador' || user?.rol?.nombre === 'Administrador';

  const [statusData, setStatusData] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [feedback, setFeedback] = useState(null);

  // Paso 1: Generar CSR
  const [csrForm, setCsrForm] = useState({
    cuit: '',
    razon_social: '',
    alias: 'credit-manager-arca',
  });
  const [generatingCsr, setGeneratingCsr] = useState(false);

  // Paso 2: Subir Certificado (.crt y opcional .key)
  const [crtFile, setCrtFile] = useState(null);
  const [keyFile, setKeyFile] = useState(null);
  const [uploadingCert, setUploadingCert] = useState(false);

  // Paso 3: Entorno y Punto de Venta
  const [configForm, setConfigForm] = useState({
    environment: 'mock',
    cuit: '',
    punto_venta_default: 1,
    dias_alerta_vencimiento: 5,
  });
  const [savingConfig, setSavingConfig] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [connResult, setConnResult] = useState(null);

  const fetchStatus = useCallback(async () => {
    setLoadingStatus(true);
    try {
      const [arcaRes, companyRes] = await Promise.all([
        axiosClient.get('/api/v1/system/arca/status'),
        axiosClient.get('/api/v1/system/company').catch(() => ({ data: {} })),
      ]);
      const data = arcaRes.data;
      const comp = companyRes.data || {};
      setStatusData(data);

      setConfigForm({
        environment: data.environment || 'mock',
        cuit: data.cuit || comp.cuit || '',
        punto_venta_default: data.punto_venta_default ?? 1,
        dias_alerta_vencimiento: data.dias_alerta_vencimiento ?? 5,
      });

      setCsrForm((prev) => ({
        cuit: prev.cuit || data.cuit || comp.cuit || '',
        razon_social: prev.razon_social || comp.razon_social || 'Yoyo S.A.',
        alias: prev.alias || 'credit-manager-arca',
      }));
    } catch (err) {
      setFeedback({
        type: 'error',
        text:
          err.response?.data?.detail ||
          'No se pudo obtener el estado de configuración ARCA.',
      });
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const triggerBlobDownload = (blobData, filename) => {
    const url = window.URL.createObjectURL(new Blob([blobData]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleGenerateCsr = async (e) => {
    e.preventDefault();
    setGeneratingCsr(true);
    setFeedback(null);
    try {
      const response = await axiosClient.post(
        '/api/v1/system/arca/generar-csr',
        csrForm,
        { responseType: 'blob' }
      );
      triggerBlobDownload(response.data, 'arca.csr');
      setFeedback({
        type: 'success',
        text: 'Clave privada (arca.key) y solicitud CSR (arca.csr) generadas correctamente. Se inició la descarga de arca.csr.',
      });
      await fetchStatus();
    } catch (err) {
      let detail = 'Error al generar el pedido CSR.';
      if (err.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const parsed = JSON.parse(text);
          detail = parsed.detail || detail;
        } catch {
          // ignore
        }
      } else if (err.response?.data?.detail) {
        detail = err.response.data.detail;
      }
      setFeedback({ type: 'error', text: detail });
    } finally {
      setGeneratingCsr(false);
    }
  };

  const handleDownloadFile = async (endpoint, filename) => {
    setFeedback(null);
    try {
      const response = await axiosClient.get(endpoint, { responseType: 'blob' });
      triggerBlobDownload(response.data, filename);
    } catch (err) {
      setFeedback({
        type: 'error',
        text: `No se pudo descargar ${filename}. Verifique que haya sido generado previamente.`,
      });
    }
  };

  const handleUploadCertificate = async (e) => {
    e.preventDefault();
    if (!crtFile) {
      setFeedback({
        type: 'error',
        text: 'Seleccione un archivo de certificado (.crt o .pem) para subir.',
      });
      return;
    }

    setUploadingCert(true);
    setFeedback(null);
    try {
      const formData = new FormData();
      formData.append('crt_file', crtFile);
      if (keyFile) {
        formData.append('key_file', keyFile);
      }

      const res = await axiosClient.post(
        '/api/v1/system/arca/subir-certificado',
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      setCrtFile(null);
      setKeyFile(null);
      setFeedback({
        type: 'success',
        text:
          res.data?.message ||
          'Certificado digital X.509 validado y guardado con éxito.',
      });
      await fetchStatus();
    } catch (err) {
      setFeedback({
        type: 'error',
        text:
          err.response?.data?.detail ||
          'Error al validar o guardar el certificado digital.',
      });
    } finally {
      setUploadingCert(false);
    }
  };

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    setSavingConfig(true);
    setFeedback(null);
    try {
      const res = await axiosClient.put('/api/v1/system/arca/config', {
        environment: configForm.environment,
        cuit: configForm.cuit,
        punto_venta_default: Number(configForm.punto_venta_default),
        dias_alerta_vencimiento: Number(configForm.dias_alerta_vencimiento),
      });
      setFeedback({
        type: 'success',
        text:
          res.data?.message ||
          'Parámetros de facturación ARCA actualizados correctamente.',
      });
      await fetchStatus();
    } catch (err) {
      setFeedback({
        type: 'error',
        text:
          err.response?.data?.detail ||
          'Error al actualizar la configuración de ARCA.',
      });
    } finally {
      setSavingConfig(false);
    }
  };

  const handleTestConnection = async () => {
    setTestingConn(true);
    setConnResult(null);
    setFeedback(null);
    try {
      const res = await axiosClient.post('/api/v1/system/arca/probar-conexion');
      setConnResult(res.data);
      setFeedback({
        type: 'success',
        text: res.data?.message || 'Prueba de conexión ejecutada con éxito.',
      });
    } catch (err) {
      setFeedback({
        type: 'error',
        text:
          err.response?.data?.detail ||
          'Falló la prueba de conexión con los servidores de ARCA.',
      });
    } finally {
      setTestingConn(false);
    }
  };

  const estadoKey = statusData?.estado_vigencia || 'SIN_CERTIFICADO';
  const badge = STATUS_BADGES[estadoKey] || STATUS_BADGES.SIN_CERTIFICADO;

  return (
    <section
      className="tab-content active"
      style={{ animation: 'fadeIn 0.4s ease' }}
    >
      <header className="section-header" style={{ marginBottom: '20px' }}>
        <h2>Configuración Fiscal ARCA (AFIP)</h2>
        <p>
          Gestión de certificados digitales X.509 (WSAA / WSFEv1), entorno de
          facturación electrónica y verificación de servidores.
        </p>
      </header>

      {feedback && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            marginBottom: '20px',
            fontSize: '14px',
            backgroundColor:
              feedback.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : 'rgba(239, 68, 68, 0.15)',
            color: feedback.type === 'success' ? '#34d399' : '#f87171',
            border: `1px solid ${
              feedback.type === 'success'
                ? 'rgba(16, 185, 129, 0.35)'
                : 'rgba(239, 68, 68, 0.35)'
            }`,
          }}
        >
          {feedback.text}
        </div>
      )}

      {/* Tarjeta de Estado del Certificado */}
      <div
        className="glass-panel"
        style={{
          padding: '24px',
          borderRadius: 'var(--radius-lg)',
          marginBottom: '24px',
          border: `1px solid ${badge.border}`,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '12px',
            marginBottom: '18px',
          }}
        >
          <div>
            <h3 style={{ margin: 0 }}>Estado del Certificado Digital X.509</h3>
            <p
              style={{
                margin: '4px 0 0 0',
                fontSize: '13px',
                color: 'var(--text-muted)',
              }}
            >
              Entorno activo:{' '}
              <strong style={{ textTransform: 'uppercase', color: 'var(--text-primary)' }}>
                {statusData?.environment || 'mock'}
              </strong>{' '}
              | Punto de Venta por defecto:{' '}
              <strong>
                {String(statusData?.punto_venta_default || 1).padStart(4, '0')}
              </strong>
            </p>
          </div>

          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 14px',
              borderRadius: '999px',
              fontSize: '13px',
              fontWeight: '700',
              backgroundColor: badge.bg,
              color: badge.color,
              border: `1px solid ${badge.border}`,
            }}
          >
            <span
              style={{
                width: '9px',
                height: '9px',
                borderRadius: '50%',
                backgroundColor: badge.dot,
                display: 'inline-block',
              }}
            />
            {loadingStatus ? 'Consultando...' : badge.label}
          </span>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
          }}
        >
          <div
            style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Titular (Subject)
            </div>
            <div
              style={{
                fontSize: '13px',
                fontWeight: '600',
                marginTop: '4px',
                wordBreak: 'break-all',
              }}
            >
              {statusData?.subject || 'Sin certificado cargado'}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              CUIT Configurado
            </div>
            <div style={{ fontSize: '14px', fontWeight: '600', marginTop: '4px' }}>
              {statusData?.cuit || '—'}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Fecha de Emisión
            </div>
            <div style={{ fontSize: '14px', fontWeight: '600', marginTop: '4px' }}>
              {formatIsoDate(statusData?.fecha_emision)}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Fecha de Vencimiento
            </div>
            <div style={{ fontSize: '14px', fontWeight: '600', marginTop: '4px' }}>
              {formatIsoDate(statusData?.fecha_vencimiento)}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              borderRadius: '8px',
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Días Restantes
            </div>
            <div
              style={{
                fontSize: '16px',
                fontWeight: '700',
                marginTop: '4px',
                color: badge.color,
              }}
            >
              {statusData?.dias_restantes !== null &&
              statusData?.dias_restantes !== undefined
                ? `${statusData.dias_restantes} días`
                : '—'}
            </div>
          </div>
        </div>
      </div>

      {!isAdmin ? (
        <div
          className="glass-panel"
          style={{ padding: '20px', borderRadius: 'var(--radius-lg)' }}
        >
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>
            Solo los usuarios con rol <strong>Administrador</strong> pueden
            modificar certificados digitales o cambiar el entorno fiscal.
          </p>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
            gap: '20px',
          }}
        >
          {/* Paso 1: Generar Pedido (.csr) */}
          <div
            className="glass-panel"
            style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}
          >
            <h3 style={{ marginTop: 0, marginBottom: '8px' }}>
              Paso 1 — Generar Pedido (.csr)
            </h3>
            <p
              style={{
                fontSize: '13px',
                color: 'var(--text-muted)',
                marginBottom: '16px',
              }}
            >
              Genera una clave privada RSA de 2048 bits (<code>arca.key</code>)
              y una solicitud de certificado (<code>arca.csr</code>) para subir
              en el portal de ARCA con Clave Fiscal.
            </p>

            <form onSubmit={handleGenerateCsr}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                  CUIT del Emisor (11 dígitos)
                </label>
                <input
                  type="text"
                  value={csrForm.cuit}
                  onChange={(e) =>
                    setCsrForm({ ...csrForm, cuit: e.target.value })
                  }
                  placeholder="30712345678"
                  required
                  style={{ width: '100%' }}
                />
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                  Razón Social (O)
                </label>
                <input
                  type="text"
                  value={csrForm.razon_social}
                  onChange={(e) =>
                    setCsrForm({ ...csrForm, razon_social: e.target.value })
                  }
                  placeholder="Yoyo S.A."
                  required
                  style={{ width: '100%' }}
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                  Alias del Computador Fiscal (CN)
                </label>
                <input
                  type="text"
                  value={csrForm.alias}
                  onChange={(e) =>
                    setCsrForm({ ...csrForm, alias: e.target.value })
                  }
                  placeholder="credit-manager-arca"
                  required
                  style={{ width: '100%' }}
                />
              </div>

              <button
                type="submit"
                className="btn-primary"
                disabled={generatingCsr}
                style={{ width: '100%', marginBottom: '10px' }}
              >
                {generatingCsr
                  ? 'Generando Clave y CSR...'
                  : 'Generar y Descargar .csr'}
              </button>
            </form>

            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
              {statusData?.has_csr && (
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ flex: 1, fontSize: '12px' }}
                  onClick={() =>
                    handleDownloadFile('/api/v1/system/arca/descargar-csr', 'arca.csr')
                  }
                >
                  Descargar arca.csr actual
                </button>
              )}
              {statusData?.has_private_key && (
                <button
                  type="button"
                  className="btn-secondary"
                  style={{ flex: 1, fontSize: '12px' }}
                  onClick={() =>
                    handleDownloadFile('/api/v1/system/arca/descargar-key', 'arca.key')
                  }
                >
                  Respaldar arca.key
                </button>
              )}
            </div>

            <div
              style={{
                marginTop: '16px',
                padding: '12px',
                borderRadius: '8px',
                background: 'rgba(255,255,255,0.03)',
                fontSize: '12px',
                color: 'var(--text-muted)',
                lineHeight: '1.5',
              }}
            >
              <strong>Guía rápida en ARCA:</strong>
              <ol style={{ margin: '6px 0 0 18px', padding: 0 }}>
                <li>
                  Ingrese con Clave Fiscal a{' '}
                  <em>WSASS ( Autogestión Certificados Homologación )</em> o{' '}
                  <em>Administración de Certificados Digitales</em> (Producción).
                </li>
                <li>
                  Agregue un alias, suba el archivo <code>arca.csr</code> y
                  descargue el certificado firmado (<code>.crt</code>).
                </li>
                <li>
                  Vincule el computador fiscal al servicio{' '}
                  <strong>Facturación Electrónica (wsfe)</strong>.
                </li>
              </ol>
            </div>
          </div>

          {/* Paso 2: Cargar Certificado (.crt) */}
          <div
            className="glass-panel"
            style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}
          >
            <h3 style={{ marginTop: 0, marginBottom: '8px' }}>
              Paso 2 — Cargar Certificado (.crt)
            </h3>
            <p
              style={{
                fontSize: '13px',
                color: 'var(--text-muted)',
                marginBottom: '16px',
              }}
            >
              Suba el archivo <code>.crt</code> emitido por ARCA. El sistema
              verificará matemáticamente que corresponda a la clave privada
              almacenada.
            </p>

            <form onSubmit={handleUploadCertificate}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Certificado X.509 (.crt / .pem) *
                </label>
                <input
                  type="file"
                  accept=".crt,.pem,.cer"
                  onChange={(e) => setCrtFile(e.target.files?.[0] || null)}
                  style={{ width: '100%' }}
                />
              </div>

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '6px' }}>
                  Clave Privada (.key) — Opcional (si fue generada externamente)
                </label>
                <input
                  type="file"
                  accept=".key,.pem"
                  onChange={(e) => setKeyFile(e.target.files?.[0] || null)}
                  style={{ width: '100%' }}
                />
              </div>

              <button
                type="submit"
                className="btn-primary"
                disabled={uploadingCert || !crtFile}
                style={{ width: '100%' }}
              >
                {uploadingCert
                  ? 'Validando Certificado...'
                  : 'Validar y Guardar Certificado'}
              </button>
            </form>
          </div>

          {/* Paso 3: Entorno y Prueba de Conexión */}
          <div
            className="glass-panel"
            style={{ padding: '24px', borderRadius: 'var(--radius-lg)' }}
          >
            <h3 style={{ marginTop: 0, marginBottom: '8px' }}>
              Paso 3 — Entorno y Prueba de Conexión
            </h3>
            <p
              style={{
                fontSize: '13px',
                color: 'var(--text-muted)',
                marginBottom: '16px',
              }}
            >
              Seleccione el entorno operativo de facturación electrónica y
              verifique la conectividad con los servidores de ARCA (FEDummy y
              WSAA).
            </p>

            <form onSubmit={handleSaveConfig}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                  Entorno Operativo
                </label>
                <select
                  value={configForm.environment}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, environment: e.target.value })
                  }
                  style={{ width: '100%' }}
                >
                  <option value="mock">Mock (Simulación Local sin Red)</option>
                  <option value="homologacion">Homologación (Testing ARCA)</option>
                  <option value="produccion">Producción (Fiscal Real)</option>
                </select>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                  CUIT Emisor (11 dígitos)
                </label>
                <input
                  type="text"
                  value={configForm.cuit}
                  onChange={(e) =>
                    setConfigForm({ ...configForm, cuit: e.target.value })
                  }
                  placeholder="30712345678"
                  required
                  style={{ width: '100%' }}
                />
              </div>

              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '12px',
                  marginBottom: '16px',
                }}
              >
                <div>
                  <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                    Punto de Venta Default
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="99999"
                    value={configForm.punto_venta_default}
                    onChange={(e) =>
                      setConfigForm({
                        ...configForm,
                        punto_venta_default: e.target.value,
                      })
                    }
                    required
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '13px', marginBottom: '4px' }}>
                    Alerta Vto. (días)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="90"
                    value={configForm.dias_alerta_vencimiento}
                    onChange={(e) =>
                      setConfigForm({
                        ...configForm,
                        dias_alerta_vencimiento: e.target.value,
                      })
                    }
                    required
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn-primary"
                disabled={savingConfig}
                style={{ width: '100%', marginBottom: '10px' }}
              >
                {savingConfig
                  ? 'Guardando Configuración...'
                  : 'Guardar Configuración'}
              </button>
            </form>

            <button
              type="button"
              className="btn-secondary"
              disabled={testingConn}
              onClick={handleTestConnection}
              style={{ width: '100%' }}
            >
              {testingConn
                ? 'Probando Conexión...'
                : 'Probar Conexión con ARCA'}
            </button>

            {connResult && (
              <div
                style={{
                  marginTop: '14px',
                  padding: '12px',
                  borderRadius: '8px',
                  background: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  fontSize: '12px',
                }}
              >
                <div>
                  <strong>AppServer:</strong> {connResult.AppServer} |{' '}
                  <strong>DbServer:</strong> {connResult.DbServer} |{' '}
                  <strong>AuthServer:</strong> {connResult.AuthServer}
                </div>
                <div style={{ marginTop: '4px' }}>
                  <strong>Ticket WSAA:</strong>{' '}
                  {connResult.wsaa_autenticado
                    ? 'Autenticado correctamente'
                    : 'Sin certificado / Modo Mock'}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
};

export default ArcaConfigPage;

