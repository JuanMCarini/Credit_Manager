import React, { useState } from 'react';
import axiosClient from '../api/axiosClient';
import ClientForm from './ClientForm';

const ClientEditModal = ({ cuil, onClose, onSuccess }) => {
  const [clientData, setClientData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  React.useEffect(() => {
    const fetchClient = async () => {
      try {
        const res = await axiosClient.get(`/api/v1/clientes/${cuil}`);
        setClientData(res.data);
      } catch (err) {
        setFeedback({ type: 'error', message: 'Error al cargar el cliente.' });
      } finally {
        setLoading(false);
      }
    };
    fetchClient();
  }, [cuil]);

  const handleSubmit = async (formPayload) => {
    setSaving(true);
    setFeedback(null);
    
    const payload = {
      ...formPayload,
      calle_nro: formPayload.calle_nro ? Number(formPayload.calle_nro) : null,
      id_provincia: formPayload.id_provincia ? Number(formPayload.id_provincia) : null,
      empleador_id: formPayload.empleador_id ? Number(formPayload.empleador_id) : null,
      remuneracion: formPayload.remuneracion ? Number(formPayload.remuneracion) : 0.0,
    };
    
    Object.keys(payload).forEach(k => {
      if (payload[k] === '') payload[k] = null;
    });

    try {
      await axiosClient.put(`/api/v1/clientes/${cuil}`, payload);
      onSuccess();
      onClose();
    } catch (err) {
      setFeedback({ type: 'error', message: err.message });
      setSaving(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(0,0,0,0.5)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
      backdropFilter: 'blur(5px)'
    }}>
      <div className="glass-panel" style={{
        width: '100%', maxWidth: '900px', maxHeight: '90vh', overflowY: 'auto',
        position: 'relative', padding: '24px'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>Editar Cliente: {cuil}</h2>
        
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px' }}>Cargando datos...</div>
        ) : clientData ? (
          <ClientForm initialData={clientData} isEditMode={true} allowRepetEdit={true} onSubmit={handleSubmit} loading={saving} feedback={feedback} buttonText="Actualizar Cliente" />
        ) : (
          <div style={{ color: 'var(--error)' }}>No se pudo cargar el cliente.</div>
        )}
      </div>
    </div>
  );
};

export default ClientEditModal;
