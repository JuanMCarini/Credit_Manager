import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import MainLayout from './components/MainLayout';
import DashboardCarteraPage from './pages/DashboardCarteraPage';
import DashboardClientesPage from './pages/DashboardClientesPage';
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
import FacturacionPage from './pages/FacturacionPage';
import BcraReportsPage from './pages/BcraReportsPage';
import FinanzasPage from './pages/FinanzasPage';
import BancosPage from './pages/BancosPage';
import ComprobantesPage from './pages/ComprobantesPage';
import ChequesPage from './pages/ChequesPage';
import PosicionIvaPage from './pages/PosicionIvaPage';
import InversoresPage from './pages/InversoresPage';
import CuentasComitentesPage from './pages/CuentasComitentesPage';
import SeriesPage from './pages/SeriesPage';
import MovimientosDeudaPage from './pages/MovimientosDeudaPage';
import PosicionIibbPage from './pages/PosicionIibbPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        
        {/* Rutas protegidas genéricas (cualquier rol) */}
        <Route element={<ProtectedRoute allowedRoles={['Auditor / Solo Lectura', 'Operador de Cobranzas', 'Oficial de Crédito', 'Gerente', 'Operador de Inversiones', 'Responsable de Finanzas']} />}>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Navigate to="/dashboard-cartera" replace />} />
            <Route path="dashboard-cartera" element={<DashboardCarteraPage />} />
            <Route path="dashboard-clientes" element={<DashboardClientesPage />} />
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
            <Route path="papeleria/creditos" element={<PapeleriaPage categoria="creditos" />} />
            <Route path="papeleria/ventas" element={<PapeleriaPage categoria="ventas_cartera" />} />
            <Route path="reportes/bcra" element={<BcraReportsPage />} />
            <Route path="facturacion" element={<FacturacionPage />} />
            <Route path="finanzas" element={<FinanzasPage />} />
            <Route path="bancos" element={<BancosPage />} />
            <Route path="comprobantes" element={<ComprobantesPage />} />
            <Route path="cheques" element={<ChequesPage />} />
            <Route path="posicion-iva" element={<PosicionIvaPage />} />
            <Route path="posicion-iibb" element={<PosicionIibbPage />} />
            
            {/* Rutas de Inversores */}
            <Route path="inversores" element={<InversoresPage />} />
            <Route path="cuentas-comitentes" element={<CuentasComitentesPage />} />
            <Route path="series" element={<SeriesPage />} />
            <Route path="movimientos-deuda" element={<MovimientosDeudaPage />} />
            
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
