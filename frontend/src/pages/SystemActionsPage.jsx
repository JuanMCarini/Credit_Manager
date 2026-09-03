import { useState } from 'react';
import axiosClient from '../api/axiosClient';
import useAppStore from '../store/useAppStore';
import { useAuthStore } from '../store/useAuthStore';

const SystemActionsPage = () => {
  const [loading, setLoading] = useState(false);
  const [logoFile, setLogoFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [faviconFile, setFaviconFile] = useState(null);
  const [uploadingFavicon, setUploadingFavicon] = useState(false);
  const [moduleSaving, setModuleSaving] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  const { systemModules, updateSystemModules } = useAppStore();
  const { user } = useAuthStore();
  const isAdmin = user?.rol === 'Administrador' || user?.rol?.nombre === 'Administrador';

  const handleSyncStates = async () => {
    if (!window.confirm("¿Está seguro que desea ejecutar la sincronización global de estados? Esto recalculará saldos y estados de todas las carteras.")) {
      return;
    }
    
    setLoading(true);
    try {
      await axiosClient.post('/api/v1/system/sync-states');
      alert("Sincronización ejecutada con éxito.");
    } catch (error) {
      alert("Error al sincronizar estados: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogoChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setLogoFile(e.target.files[0]);
    }
  };

  const handleLogoUpload = async () => {
    if (!logoFile) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', logoFile);
      await axiosClient.post('/api/v1/system/logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("Logo actualizado con éxito.");
      setLogoFile(null);
      window.location.reload();
    } catch (error) {
      alert("Error al subir el logo: " + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handleFaviconChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFaviconFile(e.target.files[0]);
    }
  };

  const handleFaviconUpload = async () => {
    if (!faviconFile) return;
    setUploadingFavicon(true);
    try {
      const formData = new FormData();
      formData.append('file', faviconFile);
      await axiosClient.post('/api/v1/system/favicon', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      alert("Favicon actualizado con éxito.");
      setFaviconFile(null);
      
      // Actualizar inmediatamente el favicon en el documento
      const t = Date.now();
      const linkPng = document.getElementById('app-favicon') || document.querySelector("link[rel~='icon']");
      if (linkPng) {
        linkPng.href = `/static/favicon.png?v=${t}`;
      }
      setTimeout(() => {
        window.location.reload();
      }, 300);
    } catch (error) {
      alert("Error al subir el favicon: " + (error.response?.data?.detail || error.message));
    } finally {
      setUploadingFavicon(false);
    }
  };

  const handleToggleModule = async (key) => {
    const currentStatus = systemModules[key] !== false;
    const newStatus = !currentStatus;
    const updated = {
      ...systemModules,
      [key]: newStatus
    };

    setModuleSaving(true);
    setFeedbackMsg(null);
    try {
      await updateSystemModules(updated);
      setFeedbackMsg({ type: 'success', text: `Sección "${getModuleTitle(key)}" ${newStatus ? 'habilitada' : 'deshabilitada'} correctamente.` });
      setTimeout(() => setFeedbackMsg(null), 4000);
    } catch (error) {
      setFeedbackMsg({ type: 'error', text: `Error al actualizar la sección: ${error.response?.data?.detail || error.message}` });
    } finally {
      setModuleSaving(false);
    }
  };

  const getModuleTitle = (key) => {
    switch (key) {
      case 'creditos': return 'Cartera de Créditos';
      case 'cheques': return 'Cartera de Cheques';
      case 'inversores': return 'Inversores';
      case 'finanzas': return 'Finanzas';
      default: return key;
    }
  };

  const modulesList = [
    {
      key: 'creditos',
      title: 'CARTERA DE CRÉDITOS',
      icon: '💳',
      description: 'Acceso a Dashboard de Cartera, Clientes, Créditos, Cobranzas, Facturación, Gestión de Carteras y Reportes.'
    },
    {
      key: 'cheques',
      title: 'CARTERA DE CHEQUES',
      icon: '📑',
      description: 'Acceso al módulo de operación, ingreso y negociación de cheques de pago diferido.'
    },
    {
      key: 'inversores',
      title: 'INVERSORES',
      icon: '👥',
      description: 'Acceso a la cartera de Inversores, Cuentas Comitentes, Series de Deuda y Movimientos de Deuda.'
    },
    {
      key: 'finanzas',
      title: 'FINANZAS',
      icon: '📈',
      description: 'Acceso a Liquidación de Comisiones, Bancos y Cuentas, Comprobantes, Posición de IVA y Posición de IIBB.'
    }
  ];

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Acciones del Sistema</h2>
        <p>Mantenimiento, configuración y sincronización global de la base de datos.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        
        {/* Panel de Habilitar / Deshabilitar Secciones (Solo Administradores) */}
        {isAdmin && (
          <div className="glass-panel" style={{ gridColumn: '1 / -1', padding: '24px', borderRadius: 'var(--radius-lg)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  Habilitar / Deshabilitar Secciones del Sistema ⚙️
                </h3>
                <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: '4px 0 0 0' }}>
                  Controla la visibilidad de los módulos en toda la aplicación. Al deshabilitar una sección, su acceso desaparecerá del menú lateral.
                </p>
              </div>
              <span style={{ fontSize: '12px', fontWeight: '600', padding: '4px 10px', borderRadius: '6px', background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8', border: '1px solid rgba(99, 102, 241, 0.3)' }}>
                Exclusivo Administrador
              </span>
            </div>

            {feedbackMsg && (
              <div style={{
                padding: '10px 16px',
                borderRadius: '8px',
                marginBottom: '16px',
                fontSize: '14px',
                backgroundColor: feedbackMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: feedbackMsg.type === 'success' ? '#10b981' : '#f87171',
                border: `1px solid ${feedbackMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
              }}>
                {feedbackMsg.text}
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
              {modulesList.map(mod => {
                const isActive = systemModules[mod.key] !== false;
                return (
                  <div 
                    key={mod.key} 
                    style={{
                      padding: '16px 20px',
                      borderRadius: 'var(--radius-md)',
                      background: isActive ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.2)',
                      border: `1px solid ${isActive ? 'var(--border-color, rgba(255,255,255,0.1))' : 'rgba(255, 255, 255, 0.04)'}`,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s ease',
                      opacity: isActive ? 1 : 0.75
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '20px' }}>{mod.icon}</span>
                          <span style={{ fontWeight: '700', fontSize: '15px', color: 'var(--text-primary)' }}>
                            {mod.title}
                          </span>
                        </div>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: '700',
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          padding: '3px 8px',
                          borderRadius: '6px',
                          backgroundColor: isActive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: isActive ? '#34d399' : '#f87171',
                          border: `1px solid ${isActive ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
                        }}>
                          {isActive ? 'Habilitado' : 'Deshabilitado'}
                        </span>
                      </div>
                      <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0 0 16px 0', lineHeight: '1.4' }}>
                        {mod.description}
                      </p>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                      <label style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', cursor: moduleSaving ? 'not-allowed' : 'pointer' }}>
                        <span style={{ fontSize: '13px', color: isActive ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                          {isActive ? 'Visible en la app' : 'Oculto en la app'}
                        </span>
                        <div 
                          onClick={() => !moduleSaving && handleToggleModule(mod.key)}
                          style={{
                            width: '46px',
                            height: '24px',
                            backgroundColor: isActive ? 'var(--primary-color, #4f46e5)' : 'rgba(255,255,255,0.15)',
                            borderRadius: '12px',
                            position: 'relative',
                            transition: 'background-color 0.25s ease',
                            boxShadow: isActive ? '0 0 10px rgba(79, 70, 229, 0.4)' : 'none',
                            cursor: 'pointer'
                          }}
                        >
                          <div style={{
                            width: '18px',
                            height: '18px',
                            backgroundColor: '#ffffff',
                            borderRadius: '50%',
                            position: 'absolute',
                            top: '3px',
                            left: isActive ? '25px' : '3px',
                            transition: 'left 0.25s ease',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.3)'
                          }} />
                        </div>
                      </label>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)', textAlign: 'center' }}>
          <h3 style={{ marginBottom: '12px' }}>Sincronizar Estados 🔄</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
            Recalcula y actualiza en cascada los estados de todas las cuotas, créditos y clientes en base a la fecha de hoy y los saldos de cobranza.
          </p>
          <button className="btn-primary" onClick={handleSyncStates} disabled={loading} style={{ width: '100%', maxWidth: '300px', margin: '0 auto', display: 'block' }}>
            {loading ? "Ejecutando Sincronización..." : "Ejecutar Sincronización"}
          </button>
        </div>

        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)', textAlign: 'center' }}>
          <h3 style={{ marginBottom: '12px' }}>Logo de la Aplicación 🖼️</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
            Sube un logo personalizado para que sea visible en la barra lateral de la aplicación.
          </p>
          <input 
            type="file" 
            accept="image/*" 
            onChange={handleLogoChange} 
            style={{ marginBottom: '15px', width: '100%', maxWidth: '300px', margin: '0 auto 15px auto', display: 'block' }}
          />
          <button className="btn-primary" onClick={handleLogoUpload} disabled={!logoFile || uploading} style={{ width: '100%', maxWidth: '300px', margin: '0 auto', display: 'block' }}>
            {uploading ? "Subiendo..." : "Subir Logo"}
          </button>
        </div>

        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)', textAlign: 'center' }}>
          <h3 style={{ marginBottom: '12px' }}>Favicon de la Aplicación 🌐</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
            Sube un favicon personalizado (.ico, .png, .svg) para la pestaña del navegador.
          </p>
          <input 
            type="file" 
            accept=".ico,image/x-icon,image/png,image/svg+xml,image/*" 
            onChange={handleFaviconChange} 
            style={{ marginBottom: '15px', width: '100%', maxWidth: '300px', margin: '0 auto 15px auto', display: 'block' }}
          />
          <button className="btn-primary" onClick={handleFaviconUpload} disabled={!faviconFile || uploadingFavicon} style={{ width: '100%', maxWidth: '300px', margin: '0 auto', display: 'block' }}>
            {uploadingFavicon ? "Subiendo..." : "Subir Favicon"}
          </button>
        </div>
      </div>
    </section>
  );
};

export default SystemActionsPage;
