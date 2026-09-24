import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import CurrencyInput from './CurrencyInput';

const PerfilTransaccionalForm = ({ cuil, onComplete }) => {
  const [formData, setFormData] = useState({
    sueldo_bruto: 0,
    sueldo_neto: 0,
    asignacion_familiar: 0,
    horas_extras: 0,
    vacaciones: 0,
    otros: 0,
    descuentos_voluntarios: 0
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await axiosClient.get(`/api/v1/clientes/${cuil}/perfil_transaccional`);
        setFormData({
          sueldo_bruto: res.data.sueldo_bruto || 0,
          sueldo_neto: res.data.sueldo_neto || 0,
          asignacion_familiar: res.data.asignacion_familiar || 0,
          horas_extras: res.data.horas_extras || 0,
          vacaciones: res.data.vacaciones || 0,
          otros: res.data.otros || 0,
          descuentos_voluntarios: res.data.descuentos_voluntarios || 0
        });
      } catch (error) {
        console.error("Error fetching perfil transaccional", error);
        setFeedback({ type: 'error', message: 'No se pudo cargar el perfil transaccional.' });
      } finally {
        setLoading(false);
      }
    };
    if (cuil) {
      fetchData();
    }
  }, [cuil]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      await axiosClient.post(`/api/v1/clientes/${cuil}/perfil_transaccional`, formData);
      onComplete(); // Advance to next step
    } catch (error) {
      const errorMsg = error.response?.data?.detail || error.message || "Error al guardar el perfil transaccional.";
      setFeedback({ type: 'error', message: errorMsg });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Cargando perfil transaccional... ⏳</div>;
  }

  return (
    <form onSubmit={handleSubmit} style={{ animation: 'fadeIn 0.3s ease' }}>
      {feedback && (
        <div style={{
          padding: '12px', marginBottom: '16px', borderRadius: '4px',
          background: feedback.type === 'error' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
          color: feedback.type === 'error' ? '#ef4444' : '#10b981',
          borderLeft: `4px solid ${feedback.type === 'error' ? '#ef4444' : '#10b981'}`
        }}>
          {feedback.message}
        </div>
      )}

      <div className="form-row">
        <div className="form-group">
          <label>Sueldo Bruto *</label>
          <CurrencyInput value={formData.sueldo_bruto} onChange={(val) => handleChange('sueldo_bruto', val)} required />
        </div>
        <div className="form-group">
          <label>Sueldo Neto *</label>
          <CurrencyInput value={formData.sueldo_neto} onChange={(val) => handleChange('sueldo_neto', val)} required />
        </div>
      </div>

      <div style={{ gridColumn: '1 / -1', marginTop: '16px', marginBottom: '16px', fontSize: '13px', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '6px' }}>
        <strong>Conceptos a Restar del Recibo de Sueldo:</strong>
      </div>
      
      <div className="form-row">
        <div className="form-group">
          <label>Asignación Familiar</label>
          <CurrencyInput value={formData.asignacion_familiar} onChange={(val) => handleChange('asignacion_familiar', val)} />
        </div>
        <div className="form-group">
          <label>Horas Extras</label>
          <CurrencyInput value={formData.horas_extras} onChange={(val) => handleChange('horas_extras', val)} />
        </div>
        <div className="form-group">
          <label>Vacaciones</label>
          <CurrencyInput value={formData.vacaciones} onChange={(val) => handleChange('vacaciones', val)} />
        </div>
        <div className="form-group">
          <label>Otros Conceptos</label>
          <CurrencyInput value={formData.otros} onChange={(val) => handleChange('otros', val)} />
        </div>
      </div>
      
      <div className="form-row">
        <div className="form-group">
          <label>Descuentos Voluntarios</label>
          <CurrencyInput value={formData.descuentos_voluntarios} onChange={(val) => handleChange('descuentos_voluntarios', val)} />
        </div>
      </div>

      <div className="form-actions" style={{ marginTop: '24px' }}>
        <button type="submit" className="btn-primary" disabled={saving} style={{ width: '100%', fontSize: '16px', padding: '14px' }}>
          {saving ? "Guardando..." : "Guardar Perfil y Continuar"}
        </button>
      </div>
    </form>
  );
};

export default PerfilTransaccionalForm;
