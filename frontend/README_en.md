# 💻 Credit Manager - Frontend

Single Page Application (SPA) web client for the **Credit Manager** platform, developed with [React 19](https://react.dev/) and bundled using [Vite 8](https://vite.dev/).

> 🌐 *Leer este documento en Español: [README.md](README.md)*

---

## 🚀 Modules and Main Features

The frontend provides a modern, reactive, and modular interface to operate all financial domains of the backend:

### 1. Security, Roles & Dynamic Navigation
* **Authentication & RBAC**: Secure JWT login with role-based access control across 7 operational roles (*Administrator, Manager, Credit Officer, Collections Operator, Investment Operator, Finance Manager, Auditor / Read-Only*).
* **Feature Toggling (`ModuleGuard`)**: Real-time adaptive navigation based on enabled system modules (`creditos`, `cheques`, `inversores`, `finanzas`), automatically redirecting to the active default home view.

### 2. Credit Portfolio
* **Portfolio Dashboard**: Interactive global portfolio analytics featuring collection vs. maturity evolution charts, delinquency distribution, composition by owner/originator partner, cash flow projections, and PDF exports (Detailed and Graphical layouts).
* **Client Dashboard & Registry**: Comprehensive individual client profile displaying real-time financial KPIs, online BCRA Debtors Central inquiries, RePET screening status, UIF risk evaluation, historical checking account ledger (`ClientCCModal`), and registration/editing with **Transactional Profiles** (`PerfilTransaccionalForm`).
* **Credit Simulation, Origination & Renewals**:
  * French System installment simulator with Excel export.
  * Guided loan origination wizard (`CreditOriginationPage`) featuring credit policy checks, maximum affectable installment calculation, disbursement transfer forms (`TransfersForm`), and digital client file management (`LegajoModal`).
  * Loan renewal/refinancing preview and execution (`RenovacionPreviewModal`), manual status override with mandatory justification (`CreditEditEstadoModal`), and immutable state audit trail viewer (`CreditHistorialModal`).
* **Collections & Batch Processes**: Individual payment registration (regular installments or early payoffs), bulk processing from Excel spreadsheets with pre-validation, and processed batch management with atomic reversal.
* **Portfolio Operations & Settlements**: Purchase, sale (assignment), and repurchase of portfolios with a Present Value simulator (`CarteraPreviewModal`), contract/legajo bundle downloads, and periodic collection settlements for commercial partners.
* **Electronic Invoicing & Regulatory Reports**:
  * Bulk or individual electronic invoice issuance via ARCA/AFIP, **VAT Sales Ledger (Libro IVA Ventas)** Excel downloads, and ZIP/PDF invoice bundles.
  * Analytical balance reports and generation of **BCRA Reporting Regime (PNFC)** and **UIF (AML/CFT)** regulatory reports.

### 3. Check Portfolio
* **Custody & Check Discounting (`ChequesPage`)**: Management of own checks, third-party checks, and E-Cheqs, live purchase/sale discount calculation (clearing days, discount rates, administrative fees, and VAT), digital attachment viewing, and direct bank statement reconciliation (`ModalAsignarCheque`).

### 4. Investors & Private Debt
* **Investor Registry & Custody Accounts**: Investor management (with automated CUIT verification in ARCA) and custody accounts (*Cuentas Comitentes*) under joint or indistinct ownership regimes, including account statement views and daily interest accrual.
* **Debt Series & Movements**: Issuance of private debt series (`SeriesPage`), maturity renewal simulator with interest withdrawal or capitalization (`NuevaSeriePreviewModal`), and general ledger for subscriptions, redemptions, and interest payouts (`MovimientosDeudaPage`).

### 5. Finance, Treasury & Taxes
* **Commission Settlements (`FinanzasPage`)**: Monthly calculation and Excel export of origination, collection, and investor brokerage commissions, automatically deducting cash advances.
* **Banks & Reconciliation (`BancosPage`)**: Liquidity dashboard (Available Cash, Money Market Mutual Funds / FCI, Fixed-Term Deposits), bank statement uploads, and bulk concept classification.
* **Vouchers & Suppliers (`ComprobantesPage`)**: Purchase invoice management, installment payment plans (`PlanPagoForm`), and payment orders (`CancelacionModal`).
* **Tax Positions (`PosicionIvaPage`, `PosicionIibbPage`)**: Assisted monthly filing for Net VAT Position and inter-jurisdictional Gross Receipts Tax (IIBB - Multilateral Agreement).

### 6. Configuration, Users & Stationery
* **Auxiliary Tables (`AuxiliaryTablesPage`)**: Hot-management of all 18 parametric system tables, equipped with advanced Excel-style column filters for lists, dates, and numeric ranges (`ExcelListFilter`, `ExcelDateFilter`, `ExcelNumberRangeFilter`) and one-click Excel export (`ExportExcelButton`).
* **System Actions & Users**: Global delinquency state synchronization, module feature toggles, corporate logo/favicon customization, user management, and security audit trail viewer (`UserAuditModal`).
* **Stationery (`PapeleriaPage`)**: Word template (`.docx`) manager by category and commercial partner, complete with an interactive variable dictionary for automated contract and promissory note generation.

---

## 🛠️ Technologies and Libraries

* **[React 19](https://react.dev/)** + **[Vite 8](https://vite.dev/)** (Reactive UI, code-splitting via `React.lazy`, and HMR)
* **[React Router v7](https://reactrouter.com/)** (Declarative routing with role and module security guards)
* **[Zustand](https://zustand-demo.pmnd.rs/)** (Global app state `useAppStore` and auth session `useAuthStore`)
* **[TanStack React Query v5](https://tanstack.com/query/latest)** + **[Axios](https://axios-http.com/)** (Server state caching, synchronization, and JWT interceptors)
* **[Recharts 3](https://recharts.org/)** (Interactive financial charts and data visualization)
* **[jsPDF](https://github.com/parallax/jsPDF)** + **[html2canvas](https://html2canvas.hertzen.com/)** (Management PDF report generation)
* **[SheetJS (`xlsx`)](https://sheetjs.com/)** (Client-side Excel spreadsheet parsing and export)
* **[SweetAlert2](https://sweetalert2.github.io/)** + **[Lucide React](https://lucide.dev/)** (Modal alerts, confirmations, and iconography)
* **[date-fns](https://date-fns.org/)** + **[react-datepicker](https://reactdatepicker.com/)** (Date formatting and selection)

---

## 📁 `src/` Directory Structure

```text
frontend/src/
├── App.jsx                 # Route definitions, lazy-loading, ProtectedRoute, and ModuleGuard
├── main.jsx                # React entry point and React Query provider
├── index.css               # Design system, CSS variables, and global styles
├── api/
│   ├── axiosClient.js      # Axios instance with automatic JWT injection and 401/403 handling
│   └── config.js           # Dynamic API base URL resolution
├── components/             # Reusable UI components, operational modals, and Excel-like filters
│   └── Finanzas/           # Treasury, banks, vouchers, and payment plan subcomponents
├── hooks/
│   └── useDebounce.js      # Custom hook for real-time search optimization
├── pages/                  # 29 main page views organized by business module
├── store/
│   ├── useAppStore.js      # Global API status and active module state
│   └── useAuthStore.js     # Session persistence, authenticated user, and role state
└── utils/
    └── dates.js            # Date formatters and helper utilities
```

---

## ⚙️ Installation and Local Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```
2. **Start the development server**:
   ```bash
   npm run dev
   ```
   The development server runs by default on `http://localhost:5173` and proxies `/api` requests to the backend (`http://127.0.0.1:8000` or the target specified in `VITE_API_PROXY_TARGET`).
3. **Run the linter (ESLint)**:
   ```bash
   npm run lint
   ```
4. **Build for production**:
   ```bash
   npm run build
   ```
   Optimized static assets are generated in the `dist/` folder, ready to be served via Nginx (as configured in `nginx.conf` and `Dockerfile`).
