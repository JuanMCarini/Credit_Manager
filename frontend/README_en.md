# Credit Manager - Frontend

This is the web client for the **Credit Manager** system, developed with [React](https://react.dev/) and bundled using [Vite](https://vitejs.dev/).

## Main Features

The frontend provides a modern and interactive graphical interface to consume the Credit Manager API, including advanced modules for comprehensive financial management:

- **Authentication and Roles**: Secure login system with role-based access control (Administrator, Auditor, Collections Operator, Credit Officer).
- **Portfolio Dashboard**: Interactive analysis of the global portfolio status. Includes evolution charts, composition by owner, maturity projections, arrears status, and optimized PDF export (Detailed and Graphical formats).
- **Client Dashboard (Individual Profile)**: Comprehensive view of each client's situation. Allows viewing contact data, filtering by one or multiple associated credits, and checking real-time financial KPIs (Total Balance, Arrears Amount, Overdue Installments).
- **Collections and Receipts Management**: Interface to register payments and issue receipts, interacting with the backend's atomic collections engine.
- **Invoicing, Settlements, and Plans**: Modules to manage invoice issuance, periodic settlements, and the creation of financing plans.
- **Centralized Configuration Management**: Auxiliary Tables panel to dynamically manage the Administrative Company and its Commercial Partners data, with automatic hot synchronization with the backend's `.env` file.
- **Lists and Searches**: Fast pagination and search tools to navigate through the client registry and the complete list of credits, with direct redirection to their analytical profiles.

## Technologies

- **React 18** (UI and Components)
- **Vite** (Build tool and HMR)
- **Recharts** (Interactive charts and data visualization)
- **jsPDF + html2canvas** (Report generation and PDF export)
- **CSS Modules / Vanilla CSS** (System design variables and styling)

## Installation and Local Setup

1. Install dependencies:
   ```bash
   npm install
   ```
2. Start the local development server:
   ```bash
   npm run dev
   ```
3. Build for production:
   ```bash
   npm run build
   ```

The development server will normally run on `http://localhost:5173`.
