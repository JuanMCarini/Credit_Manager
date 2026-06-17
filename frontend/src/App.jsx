import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
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
import ProcesosListPage from './pages/ProcesosListPage';
import PortfolioOperationsPage from './pages/PortfolioOperationsPage';
import PortfolioOriginationPage from './pages/PortfolioOriginationPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Navigate to="/simulation" replace />} />
          <Route path="simulation" element={<SimulationPage />} />
          <Route path="balances" element={<BalancesPage />} />
          <Route path="clientes" element={<ClientListPage />} />
          <Route path="creditos" element={<CreditListPage />} />
          <Route path="alta-cliente" element={<ClientRegistrationPage />} />
          <Route path="alta-credito" element={<CreditOriginationPage />} />
          <Route path="cobranzas" element={<CollectionsListPage />} />
          <Route path="procesamiento-cobranzas" element={<CollectionsProcessingPage />} />
          <Route path="procesos" element={<ProcesosListPage />} />
          <Route path="operaciones-cartera" element={<PortfolioOperationsPage />} />
          <Route path="nueva-operacion-cartera" element={<PortfolioOriginationPage />} />
          <Route path="auxiliares" element={<AuxiliaryTablesPage />} />
          <Route path="acciones" element={<SystemActionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
