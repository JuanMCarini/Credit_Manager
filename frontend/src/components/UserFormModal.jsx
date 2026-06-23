import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';

const UserFormModal = ({ user, onClose, onSuccess, roles }) => {
  const isEditing = !!user;
  const [formData, setFormData] = useState({
    nombre_completo: user?.nombre_completo || '',
    email: user?.email || '',
    rol_id: user?.rol?.id || (roles && roles.length > 0 ? roles[0].id : ''),
    is_active: user?.is_active ?? true,
    password: ''
  });
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);

    const payload = { ...formData, rol_id: parseInt(formData.rol_id) };

    try {
      if (isEditing) {
        // Password is not updated here for existing users
        delete payload.password;
        await axiosClient.put(`/api/usuarios/${user.id}`, payload);
      } else {
        if (!payload.password || payload.password.length < 6) {
          setFeedback({ type: 'error', message: 'La contraseña debe tener al menos 6 caracteres.' });
          setSaving(false);
          return;
        }
        await axiosClient.post('/api/usuarios', payload);
      }
      onSuccess();
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setFeedback({ type: 'error', message: msg });
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
        width: '100%', maxWidth: '500px', position: 'relative', padding: '24px'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>
          {isEditing ? 'Editar Usuario' : 'Nuevo Usuario'}
        </h2>
        
        {feedback && (
          <div className={`feedback-message ${feedback.type === 'error' ? 'error' : 'success'}`} style={{ marginBottom: '15px' }}>
            {feedback.message}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div className="form-group">
            <label>Nombre Completo</label>
            <input type="text" className="form-control" name="nombre_completo" value={formData.nombre_completo} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" className="form-control" name="email" value={formData.email} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Rol</label>
            <select className="form-control" name="rol_id" value={formData.rol_id} onChange={handleChange} required>
              <option value="">Seleccione un rol...</option>
              {roles.map(r => (
                <option key={r.id} value={r.id}>{r.nombre}</option>
              ))}
            </select>
          </div>
          
          {!isEditing && (
            <div className="form-group">
              <label>Contraseña</label>
              <input type="password" className="form-control" name="password" value={formData.password} onChange={handleChange} required minLength="6" />
            </div>
          )}

          {isEditing && (
            <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <input type="checkbox" id="is_active" name="is_active" checked={formData.is_active} onChange={handleChange} />
              <label htmlFor="is_active" style={{ marginBottom: 0 }}>Usuario Activo</label>
            </div>
          )}
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Guardando...' : (isEditing ? 'Actualizar' : 'Crear')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserFormModal;
