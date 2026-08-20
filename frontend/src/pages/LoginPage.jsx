import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/useAuthStore';
import { LogIn } from 'lucide-react';
import { API_BASE_URL } from '../api/config';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [logoError, setLogoError] = useState(false);
  const navigate = useNavigate();
  const login = useAuthStore((state) => state.login);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });

      const data = await response.json();

      if (response.ok) {
        login(data.user, data.access_token);
        navigate('/');
      } else {
        setError(data.detail || 'Error al iniciar sesión');
      }
    } catch (err) {
      setError('Error de conexión con el servidor');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'var(--bg-base)',
      zIndex: 1000
    }}>
      <div className="glass-panel" style={{
        width: '100%',
        maxWidth: '420px',
        padding: '40px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        boxSizing: 'border-box'
      }}>
        
        {!logoError ? (
          <img 
            src="/static/logo.png" 
            alt="App Logo" 
            style={{ maxHeight: '100px', maxWidth: '100%', marginBottom: '24px', objectFit: 'contain' }}
            onError={() => setLogoError(true)}
          />
        ) : (
          <>
            <div style={{
              width: '64px',
              height: '64px',
              backgroundColor: 'rgba(59, 130, 246, 0.1)',
              borderRadius: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '24px',
              border: '1px solid rgba(59, 130, 246, 0.2)'
            }}>
              <LogIn size={32} color="var(--accent-primary)" />
            </div>
            <h2 style={{ marginBottom: '8px', color: 'var(--text-primary)' }}>Credit Manager</h2>
          </>
        )}
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '32px', textAlign: 'center' }}>
          Ingresa tus credenciales para continuar
        </p>

        <form style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '20px' }} onSubmit={handleSubmit}>
          {error && (
            <div style={{
              width: '100%',
              padding: '12px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--error)',
              fontSize: '14px',
              textAlign: 'center',
              boxSizing: 'border-box'
            }}>
              {error}
            </div>
          )}
          
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="email">Correo Electrónico</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="admin@creditmanager.com"
              required
            />
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary"
            style={{ marginTop: '8px' }}
          >
            {isLoading ? 'Iniciando sesión...' : 'Iniciar Sesión'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
