# 💻 Credit Manager - Frontend

Cliente web SPA (*Single Page Application*) para la plataforma **Credit Manager**, desarrollado con [React 19](https://react.dev/) y empaquetado mediante [Vite 8](https://vite.dev/).

> 🌐 *Read this document in English: [README_en.md](README_en.md)*

---

## 🚀 Módulos y Características Principales

El frontend proporciona una interfaz moderna, reactiva y modular para operar todos los dominios financieros del backend:

### 1. Seguridad, Roles y Navegación Dinámica
* **Autenticación y RBAC**: Inicio de sesión seguro con JWT y control de acceso basado en 7 roles (*Administrador, Gerente, Oficial de Crédito, Operador de Cobranzas, Operador de Inversiones, Responsable de Finanzas, Auditor / Solo Lectura*).
* **Feature Toggling (`ModuleGuard`)**: Navegación adaptable en tiempo real según los módulos habilitados en el sistema (`creditos`, `cheques`, `inversores`, `finanzas`), redirigiendo automáticamente a la vista principal activa.

### 2. Cartera de Créditos
* **Dashboard de Cartera**: Análisis interactivo del estado global de la cartera con gráficos de evolución de cobranzas vs. vencimientos, distribución de mora, composición por socio dueño/originador, proyección de flujo de fondos y exportación a PDF (formatos Detallado y Gráfico).
* **Dashboard y Padrón de Clientes**: Ficha integral por cliente con indicadores financieros en tiempo real, consulta en línea a la Central de Deudores del BCRA, estado de cruce RePET, evaluación de riesgo UIF, cuenta corriente histórica (`ClientCCModal`) y alta/edición con **Perfil Transaccional** (`PerfilTransaccionalForm`).
* **Simulación, Originación y Renovación de Créditos**:
  * Simulador de cronogramas bajo el Sistema Francés con exportación a Excel.
  * Asistente guiado de otorgamiento (`CreditOriginationPage`) con validación de políticas crediticias, cálculo de cuota máxima afectable, carga de transferencias (`TransfersForm`) y gestión de legajos digitales (`LegajoModal`).
  * Previsualización y ejecución de renovaciones/refinanciaciones (`RenovacionPreviewModal`), edición manual de estados con justificación (`CreditEditEstadoModal`) y consulta de historial auditable de estados (`CreditHistorialModal`).
* **Cobranzas y Procesos**: Registro de cobros individuales (ordinarios o cancelaciones anticipadas), procesamiento masivo desde planillas de Excel con validación previa y panel de lotes procesados con reversión atómica.
* **Operaciones y Liquidaciones de Cartera**: Compra, venta (cesión) y recompra de carteras con simulador de Valor Actual (`CarteraPreviewModal`), descarga de contratos/legajos y procesamiento de liquidaciones periódicas a socios comerciales.
* **Facturación Electrónica y Reportes Regulados**:
  * Emisión masiva o individual de facturas electrónicas ante ARCA/AFIP, descarga de **Libro IVA Ventas** en Excel y comprobantes en ZIP/PDF.
  * Reportes analíticos de saldos y generación del **Régimen Informativo BCRA (PNFC)** y reportes **UIF (PLA/FT)**.

### 3. Cartera de Cheques
* **Custodia y Descuento de Valores (`ChequesPage`)**: Administración de cheques propios, de terceros y E-Cheqs, liquidación en vivo de operaciones de compra/venta con cálculo de días de clearing, tasas y gastos, visualización de adjuntos digitales y conciliación directa contra movimientos bancarios (`ModalAsignarCheque`).

### 4. Inversores y Deuda Privada
* **Padrón y Cuentas Comitentes**: Gestión de inversores (con validación de CUIT en ARCA) y cuentas comitentes bajo régimen de orden indistinta o conjunta, con consulta de estado de cuenta y devengamiento diario.
* **Series y Movimientos de Deuda**: Emisión de series de deuda (`SeriesPage`), simulador de renovación con retiro o capitalización de intereses (`NuevaSeriePreviewModal`) y libro mayor de suscripciones, rescates y pagos de renta (`MovimientosDeudaPage`).

### 5. Finanzas, Tesorería e Impuestos
* **Liquidación de Comisiones (`FinanzasPage`)**: Cálculo mensual y exportación a Excel de comisiones de colocación, cobranza y captación de inversores, descontando anticipos.
* **Bancos y Conciliación (`BancosPage`)**: Dashboard de liquidez (Disponible, FCI, Plazo Fijo), subida de extractos bancarios y asignación masiva de conceptos.
* **Comprobantes y Proveedores (`ComprobantesPage`)**: Gestión de facturas de compras, planes de pago en cuotas (`PlanPagoForm`) y órdenes de cancelación (`CancelacionModal`).
* **Posiciones Fiscales (`PosicionIvaPage`, `PosicionIibbPage`)**: Liquidación mensual asistida de la Posición de IVA y distribución interjurisdiccional de Ingresos Brutos (Convenio Multilateral).

### 6. Configuración, Usuarios y Papelería
* **Tablas Auxiliares (`AuxiliaryTablesPage`)**: Administración en caliente de las 18 tablas paramétricas del sistema, equipada con filtros avanzados estilo Excel para listas, fechas y rangos numéricos (`ExcelListFilter`, `ExcelDateFilter`, `ExcelNumberRangeFilter`) y exportación directa (`ExportExcelButton`).
* **Acciones del Sistema y Usuarios**: Sincronización global de estados de mora, activación/desactivación de módulos, personalización de logo/favicon corporativo, administración de usuarios y visor de auditoría (`UserAuditModal`).
* **Papelería (`PapeleriaPage`)**: Gestor de plantillas Word (`.docx`) por categoría y socio comercial con diccionario interactivo de variables para emisión de contratos y pagarés.

---

## 🛠️ Tecnologías y Librerías

* **[React 19](https://react.dev/)** + **[Vite 8](https://vite.dev/)** (UI reactiva, carga diferida con `React.lazy` y HMR)
* **[React Router v7](https://reactrouter.com/)** (Ruteo declarativo y guardias de seguridad por rol y módulo)
* **[Zustand](https://zustand-demo.pmnd.rs/)** (Gestión de estado global `useAppStore` y sesión `useAuthStore`)
* **[TanStack React Query v5](https://tanstack.com/query/latest)** + **[Axios](https://axios-http.com/)** (Caché de estado del servidor, sincronización e interceptores JWT)
* **[Recharts 3](https://recharts.org/)** (Visualización de datos y gráficos financieros interactivos)
* **[jsPDF](https://github.com/parallax/jsPDF)** + **[html2canvas](https://html2canvas.hertzen.com/)** (Generación de reportes gerenciales en PDF)
* **[SheetJS (`xlsx`)](https://sheetjs.com/)** (Lectura y exportación de planillas Excel en cliente)
* **[SweetAlert2](https://sweetalert2.github.io/)** + **[Lucide React](https://lucide.dev/)** (Alertas modales, confirmaciones e iconografía)
* **[date-fns](https://date-fns.org/)** + **[react-datepicker](https://reactdatepicker.com/)** (Manejo y selección de fechas)

---

## 📁 Estructura del Directorio `src/`

```text
frontend/src/
├── App.jsx                 # Definición de rutas, lazy-loading, ProtectedRoute y ModuleGuard
├── main.jsx                # Punto de entrada de React y proveedor de React Query
├── index.css               # Sistema de diseño, variables CSS y estilos globales
├── api/
│   ├── axiosClient.js      # Instancia Axios con inyección automática de JWT y manejo de 401/403
│   └── config.js           # Resolución dinámica de URL base de la API
├── components/             # Componentes reutilizables, modales operativos y filtros tipo Excel
│   └── Finanzas/           # Subcomponentes de tesorería, bancos, comprobantes y planes de pago
├── hooks/
│   └── useDebounce.js      # Hook para optimización de búsquedas en tiempo real
├── pages/                  # 29 vistas principales organizadas por módulo de negocio
├── store/
│   ├── useAppStore.js      # Estado global de conexión API y módulos activos
│   └── useAuthStore.js     # Persistencia de sesión, usuario autenticado y rol
└── utils/
    └── dates.js            # Formateadores y utilidades de fechas
```

---

## ⚙️ Instalación y Ejecución Local

1. **Instalar dependencias**:
   ```bash
   npm install
   ```
2. **Iniciar el servidor de desarrollo**:
   ```bash
   npm run dev
   ```
   El servidor correrá por defecto en `http://localhost:5173` y redirigirá las peticiones `/api` al backend (`http://127.0.0.1:8000` o el destino definido en `VITE_API_PROXY_TARGET`).
3. **Ejecutar el linter (ESLint)**:
   ```bash
   npm run lint
   ```
4. **Construir para producción**:
   ```bash
   npm run build
   ```
   Los archivos estáticos optimizados se generarán en la carpeta `dist/`, listos para ser servidos mediante Nginx (según la configuración incluida en `nginx.conf` y `Dockerfile`).
