import { useState } from 'react';
import axiosClient from '../api/axiosClient';

const SystemActionsPage = () => {
  const [loading, setLoading] = useState(false);

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

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Acciones del Sistema</h2>
        <p>Mantenimiento, recalculo y sincronización global de la base de datos.</p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '24px', borderRadius: 'var(--radius-lg)', textAlign: 'center' }}>
          <h3 style={{ marginBottom: '12px' }}>Sincronizar Estados 🔄</h3>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px' }}>
            Recalcula y actualiza en cascada los estados de todas las cuotas, créditos y clientes en base a la fecha de hoy y los saldos de cobranza.
          </p>
          <button className="btn-primary" onClick={handleSyncStates} disabled={loading} style={{ width: '100%', maxWidth: '300px', margin: '0 auto', display: 'block' }}>
            {loading ? "Ejecutando Sincronización..." : "Ejecutar Sincronización"}
          </button>
        </div>
      </div>
    </section>
  );
};

export default SystemActionsPage;
