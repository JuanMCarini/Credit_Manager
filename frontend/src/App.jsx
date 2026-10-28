import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import MainLayout from './components/MainLayout';
import useAppStore from './store/useAppStore';

const LoginPage = lazy(() => import('./pages/LoginPage'));
const DashboardCarteraPage = lazy(() => import('./pages/DashboardCarteraPage'));
const DashboardClientesPage = lazy(() => import('./pages/DashboardClientesPage'));
const SimulationPage = lazy(() => import('./pages/SimulationPage'));
const BalancesPage = lazy(() => import('./pages/BalancesPage'));
const ClientRegistrationPage = lazy(() => import('./pages/ClientRegistrationPage'));
const ClientListPage = lazy(() => import('./pages/ClientListPage'));
const CreditOriginationPage = lazy(() => import('./pages/CreditOriginationPage'));
const CreditListPage = lazy(() => import('./pages/CreditListPage'));
const AuxiliaryTablesPage = lazy(() => import('./pages/AuxiliaryTablesPage'));
const SystemActionsPage = lazy(() => import('./pages/SystemActionsPage'));
const CollectionsListPage = lazy(() => import('./pages/CollectionsListPage'));
const CollectionsProcessingPage = lazy(() => import('./pages/CollectionsProcessingPage'));
const PortfolioOperationsPage = lazy(() => import('./pages/PortfolioOperationsPage'));
const PortfolioOriginationPage = lazy(() => import('./pages/PortfolioOriginationPage'));
const PortfolioLiquidationsPage = lazy(() => import('./pages/PortfolioLiquidationsPage'));
const PortfolioLiquidationsProcessingPage = lazy(() => import('./pages/PortfolioLiquidationsProcessingPage'));
const UsersListPage = lazy(() => import('./pages/UsersListPage'));
const CreditProcessesPage = lazy(() => import('./pages/CreditProcessesPage'));
const PapeleriaPage = lazy(() => import('./pages/PapeleriaPage'));
const FacturacionPage = lazy(() => import('./pages/FacturacionPage'));
const BcraReportsPage = lazy(() => import('./pages/BcraReportsPage'));
const FinanzasPage = lazy(() => import('./pages/FinanzasPage'));
const BancosPage = lazy(() => import('./pages/BancosPage'));
const ComprobantesPage = lazy(() => import('./pages/ComprobantesPage'));
const ChequesPage = lazy(() => import('./pages/ChequesPage'));
const PosicionIvaPage = lazy(() => import('./pages/PosicionIvaPage'));
const InversoresPage = lazy(() => import('./pages/InversoresPage'));
const CuentasComitentesPage = lazy(() => import('./pages/CuentasComitentesPage'));
const SeriesPage = lazy(() => import('./pages/SeriesPage'));
const MovimientosDeudaPage = lazy(() => import('./pages/MovimientosDeudaPage'));
const PosicionIibbPage = lazy(() => import('./pages/PosicionIibbPage'));

const IndexRedirect = () => {
  const { systemModules } = useAppStore();
  if (systemModules?.creditos !== false) return <Navigate to="/dashboard-cartera" replace />;
  if (systemModules?.cheques !== false) return <Navigate to="/cheques" replace />;
  if (systemModules?.inversores !== false) return <Navigate to="/inversores" replace />;
  if (systemModules?.finanzas !== false) return <Navigate to="/finanzas" replace />;
  return <Navigate to="/auxiliares" replace />;
};

const ModuleGuard = ({ moduleKey }) => {
  const { systemModules } = useAppStore();
  if (systemModules && systemModules[moduleKey] === false) {
    return <IndexRedirect />;
  }
  return <Outlet />;
};

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: 'var(--text-primary)' }}>Cargando...</div>}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          {/* Rutas protegidas genéricas (cualquier rol) */}
          <Route element={<ProtectedRoute allowedRoles={['Auditor / Solo Lectura', 'Operador de Cobranzas', 'Oficial de Crédito', 'Gerente', 'Operador de Inversiones', 'Responsable de Finanzas']} />}>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<IndexRedirect />} />

              {/* Rutas de Cartera de Créditos */}
              <Route element={<ModuleGuard moduleKey="creditos" />}>
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
                <Route path="papeleria/creditos" element={<PapeleriaPage categoria="creditos" />} />
                <Route path="papeleria/ventas" element={<PapeleriaPage categoria="ventas_cartera" />} />
                <Route path="reportes/bcra" element={<BcraReportsPage />} />
                <Route path="facturacion" element={<FacturacionPage />} />
              </Route>

              {/* Rutas de Cartera de Cheques */}
              <Route element={<ModuleGuard moduleKey="cheques" />}>
                <Route path="cheques" element={<ChequesPage />} />
              </Route>

              {/* Rutas de Inversores */}
              <Route element={<ModuleGuard moduleKey="inversores" />}>
                <Route path="inversores" element={<InversoresPage />} />
                <Route path="cuentas-comitentes" element={<CuentasComitentesPage />} />
                <Route path="series" element={<SeriesPage />} />
                <Route path="movimientos-deuda" element={<MovimientosDeudaPage />} />
              </Route>

              {/* Rutas de Finanzas */}
              <Route element={<ModuleGuard moduleKey="finanzas" />}>
                <Route path="finanzas" element={<FinanzasPage />} />
                <Route path="bancos" element={<BancosPage />} />
                <Route path="comprobantes" element={<ComprobantesPage />} />
                <Route path="posicion-iva" element={<PosicionIvaPage />} />
                <Route path="posicion-iibb" element={<PosicionIibbPage />} />
              </Route>

              {/* Configuración y comunes */}
              <Route path="auxiliares" element={<AuxiliaryTablesPage />} />
              <Route path="acciones" element={<SystemActionsPage />} />
              
              {/* Rutas exclusivas Administrador */}
              <Route element={<ProtectedRoute allowedRoles={[]} />}>
                <Route path="usuarios" element={<UsersListPage />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
