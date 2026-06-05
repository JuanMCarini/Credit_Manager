import { useState } from 'react';
import axiosClient from '../api/axiosClient';
import ClientForm from '../components/ClientForm';

const ClientRegistrationPage = () => {
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState({ type: '', message: '' });

  const handleSubmit = async (form) => {
    setLoading(true);
    setFeedback({ type: '', message: '' });

    const payload = {
      ...form,
      calle_nro: form.calle_nro ? Number(form.calle_nro) : null,
      id_provincia: form.id_provincia ? Number(form.id_provincia) : null,
      empleador_id: form.empleador_id ? Number(form.empleador_id) : null,
      remuneracion: form.remuneracion ? Number(form.remuneracion) : 0.0,
    };
    
    Object.keys(payload).forEach(k => {
      if (payload[k] === '') payload[k] = null;
    });

    try {
      await axiosClient.post('/api/v1/clientes', payload);
      setFeedback({ type: 'success', message: '¡Cliente registrado con éxito!' });
    } catch (error) {
      setFeedback({ type: 'error', message: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="tab-content active" style={{ animation: 'fadeIn 0.4s ease' }}>
      <header className="section-header">
        <h2>Registro de Nuevo Cliente</h2>
        <p>Dé de alta a un nuevo prospecto o cliente en la base centralizada del sistema.</p>
      </header>

      <div className="content-grid" style={{ gridTemplateColumns: '1fr' }}>
        <div className="form-container glass-panel">
           <ClientForm onSubmit={handleSubmit} loading={loading} feedback={feedback} />
        </div>
      </div>
    </section>
  );
};

export default ClientRegistrationPage;
