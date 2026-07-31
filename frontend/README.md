# Credit Manager - Frontend

Este es el cliente web para el sistema **Credit Manager**, desarrollado con [React](https://react.dev/) y empaquetado mediante [Vite](https://vitejs.dev/).

## Características Principales

El frontend proporciona una interfaz gráfica moderna e interactiva para consumir la API de Credit Manager, incluyendo:

- **Dashboard de Cartera**: Análisis interactivo del estado global de la cartera. Incluye gráficos de evolución, composición por dueño, proyección de vencimientos, estados de morosidad y exportación optimizada a PDF (formatos Detallado y Gráfico).
- **Dashboard de Clientes (Ficha Individual)**: Vista integral de la situación de cada cliente. Permite visualizar datos de contacto, filtrar por uno o múltiples créditos asociados y consultar en tiempo real los KPIs financieros (Saldo Total, Monto en Mora, Cuotas Vencidas).
- **Listados y Búsquedas**: Herramientas rápidas de paginación y búsqueda para navegar a través del padrón de clientes y listado completo de créditos, con redirección directa a la ficha analítica de cada uno.

## Tecnologías

- **React 18** (UI y Componentes)
- **Vite** (Build tool y HMR)
- **Recharts** (Gráficos interactivos y visualización de datos)
- **jsPDF + html2canvas** (Generación de reportes y exportación en PDF)
- **CSS Modules / Vanilla CSS** (Estilos y variables de diseño del sistema)

## Instalación y Ejecución Local

1. Instalar dependencias:
   ```bash
   npm install
   ```
2. Iniciar el servidor de desarrollo local:
   ```bash
   npm run dev
   ```
3. Construir para producción:
   ```bash
   npm run build
   ```

El servidor de desarrollo correrá normalmente en `http://localhost:5173`.
