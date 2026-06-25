import React, { useState } from 'react';
import axiosClient from '../api/axiosClient';

const UserPasswordModal = ({ user, onClose, onSuccess }) => {
  const [newPassword, setNewPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      setFeedback({ type: 'error', message: 'La nueva contraseña debe tener al menos 6 caracteres.' });
      return;
    }

    setSaving(true);
    setFeedback(null);
    try {
      await axiosClient.put(`/api/usuarios/${user.id}/password`, {
        password: newPassword
      });
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
        width: '100%', maxWidth: '400px', position: 'relative', padding: '24px'
      }}>
        <button onClick={onClose} style={{
          position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none',
          color: 'var(--text-secondary)', cursor: 'pointer', fontSize: '20px'
        }}>✕</button>
        
        <h2 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)', fontSize: '1.2em' }}>
          Cambiar Contraseña: {user.nombre_completo}
        </h2>
        
        {feedback && (
          <div className={`feedback-message ${feedback.type === 'error' ? 'error' : 'success'}`} style={{ marginBottom: '15px' }}>
            {feedback.message}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div className="form-group">
            <label>Nueva Contraseña</label>
            <input 
              type="password" 
              className="form-control" 
              value={newPassword} 
              onChange={e => setNewPassword(e.target.value)} 
              required 
            />
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={saving}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Guardando...' : 'Cambiar Contraseña'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default UserPasswordModal;
