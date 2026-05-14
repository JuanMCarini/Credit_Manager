# 💳 Credit Manager - Core Engine

Sistema de gestión de carteras de créditos y motores de amortización financiera desarrollado en Python. Este proyecto permite la administración de activos financieros, cálculo de cuotas mediante sistema francés, importación masiva de datos y generación de reportes analíticos.

## 🚀 Características Principales

* **Motor de Amortización**: Cálculo preciso de cuotas mediante el Sistema Francés utilizando `numpy-financial` con forzado de fechas de vencimiento.
* **Pipeline ETL Robusto**: Ingesta masiva de carteras desde archivos CSV crudos. Implementa validación de integridad referencial, casteo seguro de nulos (`NaN`/`NaT`) y carga a la base de datos mediante transacciones atómicas (ACID).
* **Reportes Analíticos Optimizados**: Generación de cuadros de saldos y estados de deuda. Utiliza *SQL push-down* para delegar el filtrado inicial al motor relacional y vectorización lógica (`np.select`) en Pandas para evitar la saturación de memoria RAM.
* **Arquitectura de Datos**: Modelado relacional con SQLAlchemy. Incluye seguimiento granular de la propiedad de las cuotas a través de operaciones de cartera (Compra, Venta, Recompra).
* **Configuración Centralizada**: Gestión de variables de entorno y metadatos de la empresa administradora validados estrictamente en tiempo de ejecución mediante Pydantic.
* **Web API**: Backend desarrollado con FastAPI para simulaciones de crédito en tiempo real.

## 🛠️ Tecnologías Utilizadas

* **Lenguaje**: Python 3.14.4
* **Análisis y Manipulación de Datos**: Pandas, NumPy & NumPy-Financial
* **ORM y Base de Datos**: SQLAlchemy & SQLite
* **Configuración y Validación**: Pydantic & Pydantic-Settings
* **Framework Web**: FastAPI & Uvicorn

## 📁 Estructura del Proyecto

```text
Credit_Manager/
├── .env                  # Variables de entorno y metadatos de la empresa administradora
├── data/                 # Almacenamiento local de la base de datos SQLite y archivos CSV
├── notebooks/            # Entorno interactivo de pruebas, auditorías y ejecución ETL
└── src/
    ├── api/              # Endpoints y configuración del servidor web
    ├── database/         # Modelos ORM, conexión a BD y scripts de poblado inicial
    ├── etl/              # Pipelines de Extracción, Transformación y Carga (PortfolioImporter)
    ├── logic/            # Motores matemáticos de cálculo financiero (AmortizationEngine)
    ├── reports/          # Módulo de analítica y reportes de saldos de cartera
    └── config.py         # Configuración global inmutable de la aplicación