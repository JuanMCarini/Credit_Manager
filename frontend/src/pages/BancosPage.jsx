import { Landmark } from 'lucide-react';
import BancosTab from '../components/Finanzas/BancosTab';

const BancosPage = () => {
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

      <BancosTab />
    </div>
  );
};

export default BancosPage;
