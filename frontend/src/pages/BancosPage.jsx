import { Landmark, LayoutDashboard, ListOrdered } from 'lucide-react';
import { useState } from 'react';
import BancosTab from '../components/Finanzas/BancosTab';
import DashboardBancosTab from '../components/Finanzas/DashboardBancosTab';

const BancosPage = () => {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="page-container" style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <header className="page-header" style={{ marginBottom: '32px' }}>
        <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '28px', fontWeight: 'bold' }}>
          <Landmark size={32} color="var(--primary-color)" />
          Gestión de Bancos y Cuentas
        </h1>
        <p className="page-description" style={{ color: 'var(--text-muted)', fontSize: '15px', marginTop: '8px' }}>
          Administre sus cuentas bancarias, inversiones y registre todos los movimientos financieros.
        </p>
      </header>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '24px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
        <button 
          onClick={() => setActiveTab('dashboard')}
          style={{ 
            background: 'none', 
            border: 'none', 
            fontSize: '16px', 
            fontWeight: activeTab === 'dashboard' ? 'bold' : 'normal',
            color: activeTab === 'dashboard' ? 'var(--primary-color)' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderBottom: activeTab === 'dashboard' ? '2px solid var(--primary-color)' : '2px solid transparent'
          }}
        >
          <LayoutDashboard size={18} /> Dashboard Consolidado
        </button>
        <button 
          onClick={() => setActiveTab('movimientos')}
          style={{ 
            background: 'none', 
            border: 'none', 
            fontSize: '16px', 
            fontWeight: activeTab === 'movimientos' ? 'bold' : 'normal',
            color: activeTab === 'movimientos' ? 'var(--primary-color)' : 'var(--text-muted)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            borderBottom: activeTab === 'movimientos' ? '2px solid var(--primary-color)' : '2px solid transparent'
          }}
        >
          <ListOrdered size={18} /> Movimientos por Cuenta
        </button>
      </div>

      {activeTab === 'dashboard' && <DashboardBancosTab />}
      {activeTab === 'movimientos' && <BancosTab />}
    </div>
  );
};

export default BancosPage;
