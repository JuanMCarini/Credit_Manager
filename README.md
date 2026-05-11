# 💳 Credit Manager - Core Engine

Sistema de gestión de carteras de créditos y motores de amortización financiera desarrollado en Python. Este proyecto permite la administración de activos financieros, cálculo de cuotas mediante sistema francés y exposición de lógica vía API.

## 🚀 Características Principales

* **Motor de Amortización**: Cálculo preciso de cuotas mediante el Sistema Francés utilizando `numpy-financial`.
* **Gestión de IVA**: Desglose automático de IVA sobre intereses devengados, ajustado a normativas financieras.
* **Arquitectura de Datos**: Modelado robusto con SQLAlchemy, incluyendo lógica de origen de créditos (Originados vs. Comprados) mediante propiedades híbridas.
* **Web API**: Backend desarrollado con FastAPI que permite simulaciones de crédito en tiempo real.
* **Base de Datos**: Persistencia en SQLite optimizada para portabilidad y desarrollo rápido.

## 🛠️ Tecnologías Utilizadas

* **Lenguaje**: Python 3.14.4
* **Framework Web**: FastAPI & Uvicorn
* **Cálculo Científico**: NumPy & NumPy-Financial
* **ORM**: SQLAlchemy
* **Manipulación de Datos**: Pandas

## 📁 Estructura del Proyecto

```text
/src
  /api          # Endpoints y configuración del servidor web
  /database     # Modelos ORM y conexión a BD
  /logic        # Motores de cálculo financiero
  /data_io      # (WIP) Módulos de importación/exportación de datos
/notebooks      # Entorno de pruebas e integración
/data           # Almacenamiento de base de datos SQLite