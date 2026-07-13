import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import MainLayout from './components/MainLayout';
import SimulationPage from './pages/SimulationPage';
import BalancesPage from './pages/BalancesPage';
import ClientRegistrationPage from './pages/ClientRegistrationPage';
import ClientListPage from './pages/ClientListPage';
import CreditOriginationPage from './pages/CreditOriginationPage';
import CreditListPage from './pages/CreditListPage';
import AuxiliaryTablesPage from './pages/AuxiliaryTablesPage';
import SystemActionsPage from './pages/SystemActionsPage';
import CollectionsListPage from './pages/CollectionsListPage';
import CollectionsProcessingPage from './pages/CollectionsProcessingPage';
import PortfolioOperationsPage from './pages/PortfolioOperationsPage';
import PortfolioOriginationPage from './pages/PortfolioOriginationPage';
import PortfolioLiquidationsPage from './pages/PortfolioLiquidationsPage';
import PortfolioLiquidationsProcessingPage from './pages/PortfolioLiquidationsProcessingPage';
import UsersListPage from './pages/UsersListPage';
import CreditProcessesPage from './pages/CreditProcessesPage';
import PapeleriaPage from './pages/PapeleriaPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        {/* Rutas protegidas genéricas (cualquier rol) */}
        <Route element={<ProtectedRoute allowedRoles={['Auditor / Solo Lectura', 'Operador de Cobranzas', 'Oficial de Crédito']} />}>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/simulation" replace />} />
            <Route path="simulation" element={<SimulationPage />} />
            <Route path="balances" element={<BalancesPage />} />
            <Route path="clientes" element={<ClientListPage />} />
            <Route path="creditos" element={<CreditListPage />} />
            <Route path="alta-cliente" element={<ClientRegistrationPage />} />
            <Route path="alta-credito" element={<CreditOriginationPage />} />
            <Route path="creditos-procesos" element={<CreditProcessesPage />} />
            <Route path="cobranzas" element={<CollectionsListPage />} />
            <Route path="procesamiento-cobranzas" element={<CollectionsProcessingPage />} />
            <Route path="operaciones-cartera" element={<PortfolioOperationsPage />} />
            <Route path="liquidaciones-cartera" element={<PortfolioLiquidationsPage />} />
            <Route path="procesar-liquidaciones" element={<PortfolioLiquidationsProcessingPage />} />
            <Route path="nueva-operacion-cartera" element={<PortfolioOriginationPage />} />
            <Route path="auxiliares" element={<AuxiliaryTablesPage />} />
            <Route path="acciones" element={<SystemActionsPage />} />
            <Route path="papeleria" element={<PapeleriaPage />} />
            
            {/* Rutas exclusivas Administrador */}
            <Route element={<ProtectedRoute allowedRoles={[]} />}>
              <Route path="usuarios" element={<UsersListPage />} />
            </Route>
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
