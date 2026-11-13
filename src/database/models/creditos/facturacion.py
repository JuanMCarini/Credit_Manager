from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    Numeric,
    Date,
    DateTime,
    JSON,
    inspect,
    text,
    func,
)
from sqlalchemy.orm import relationship
from src.database import Base


TIPOS_COMPROBANTE_ARCA: list[dict] = [
    # Clase A
    {
        "codigo": 1,
        "letra": "A",
        "titulo": "FACTURA",
        "nombre": "Factura A",
        "clase": "Clase A (Responsable Inscripto / Monotributo)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 2,
        "letra": "A",
        "titulo": "NOTA DE DÉBITO",
        "nombre": "Nota de Débito A",
        "clase": "Clase A (Responsable Inscripto / Monotributo)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": False,
    },
    {
        "codigo": 3,
        "letra": "A",
        "titulo": "NOTA DE CRÉDITO",
        "nombre": "Nota de Crédito A",
        "clase": "Clase A (Responsable Inscripto / Monotributo)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 4,
        "letra": "A",
        "titulo": "RECIBO",
        "nombre": "Recibo A",
        "clase": "Clase A (Responsable Inscripto / Monotributo)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    # Clase B
    {
        "codigo": 6,
        "letra": "B",
        "titulo": "FACTURA",
        "nombre": "Factura B",
        "clase": "Clase B (Consumidor Final / Exento / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 7,
        "letra": "B",
        "titulo": "NOTA DE DÉBITO",
        "nombre": "Nota de Débito B",
        "clase": "Clase B (Consumidor Final / Exento / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": False,
    },
    {
        "codigo": 8,
        "letra": "B",
        "titulo": "NOTA DE CRÉDITO",
        "nombre": "Nota de Crédito B",
        "clase": "Clase B (Consumidor Final / Exento / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 9,
        "letra": "B",
        "titulo": "RECIBO",
        "nombre": "Recibo B",
        "clase": "Clase B (Consumidor Final / Exento / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    # Clase C
    {
        "codigo": 11,
        "letra": "C",
        "titulo": "FACTURA",
        "nombre": "Factura C",
        "clase": "Clase C (Operaciones Exentas / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 12,
        "letra": "C",
        "titulo": "NOTA DE DÉBITO",
        "nombre": "Nota de Débito C",
        "clase": "Clase C (Operaciones Exentas / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": False,
    },
    {
        "codigo": 13,
        "letra": "C",
        "titulo": "NOTA DE CRÉDITO",
        "nombre": "Nota de Crédito C",
        "clase": "Clase C (Operaciones Exentas / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 15,
        "letra": "C",
        "titulo": "RECIBO",
        "nombre": "Recibo C",
        "clase": "Clase C (Operaciones Exentas / Monotributo)",
        "discrimina_iva": False,
        "requiere_cuit": False,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    # Clase M
    {
        "codigo": 51,
        "letra": "M",
        "titulo": "FACTURA",
        "nombre": "Factura M",
        "clase": "Clase M (Responsable Inscripto con Retención)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 52,
        "letra": "M",
        "titulo": "NOTA DE DÉBITO",
        "nombre": "Nota de Débito M",
        "clase": "Clase M (Responsable Inscripto con Retención)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": False,
    },
    {
        "codigo": 53,
        "letra": "M",
        "titulo": "NOTA DE CRÉDITO",
        "nombre": "Nota de Crédito M",
        "clase": "Clase M (Responsable Inscripto con Retención)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 54,
        "letra": "M",
        "titulo": "RECIBO",
        "nombre": "Recibo M",
        "clase": "Clase M (Responsable Inscripto con Retención)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    # Clase E (Exportación)
    {
        "codigo": 19,
        "letra": "E",
        "titulo": "FACTURA DE EXPORTACIÓN",
        "nombre": "Factura E (Exportación)",
        "clase": "Clase E (Exportación)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": False,
    },
    {
        "codigo": 20,
        "letra": "E",
        "titulo": "NOTA DE DÉBITO EXPORTACIÓN",
        "nombre": "Nota de Débito E (Exportación)",
        "clase": "Clase E (Exportación)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": False,
    },
    {
        "codigo": 21,
        "letra": "E",
        "titulo": "NOTA DE CRÉDITO EXPORTACIÓN",
        "nombre": "Nota de Crédito E (Exportación)",
        "clase": "Clase E (Exportación)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": False,
    },
    # FCE MiPyMEs (Ley 27.440)
    {
        "codigo": 201,
        "letra": "A",
        "titulo": "FACTURA DE CRÉDITO MIPYME",
        "nombre": "Factura de Crédito Electrónica MiPyMEs (FCE) A",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": True,
    },
    {
        "codigo": 202,
        "letra": "A",
        "titulo": "NOTA DE DÉBITO MIPYME",
        "nombre": "Nota de Débito Electrónica MiPyMEs (FCE) A",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": True,
    },
    {
        "codigo": 203,
        "letra": "A",
        "titulo": "NOTA DE CRÉDITO MIPYME",
        "nombre": "Nota de Crédito Electrónica MiPyMEs (FCE) A",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": True,
        "requiere_cuit": True,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": True,
    },
    {
        "codigo": 206,
        "letra": "B",
        "titulo": "FACTURA DE CRÉDITO MIPYME",
        "nombre": "Factura de Crédito Electrónica MiPyMEs (FCE) B",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": True,
    },
    {
        "codigo": 207,
        "letra": "B",
        "titulo": "NOTA DE DÉBITO MIPYME",
        "nombre": "Nota de Débito Electrónica MiPyMEs (FCE) B",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": True,
    },
    {
        "codigo": 208,
        "letra": "B",
        "titulo": "NOTA DE CRÉDITO MIPYME",
        "nombre": "Nota de Crédito Electrónica MiPyMEs (FCE) B",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": True,
    },
    {
        "codigo": 211,
        "letra": "C",
        "titulo": "FACTURA DE CRÉDITO MIPYME",
        "nombre": "Factura de Crédito Electrónica MiPyMEs (FCE) C",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": False,
        "es_fce": True,
    },
    {
        "codigo": 212,
        "letra": "C",
        "titulo": "NOTA DE DÉBITO MIPYME",
        "nombre": "Nota de Débito Electrónica MiPyMEs (FCE) C",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": False,
        "es_nota_debito": True,
        "es_fce": True,
    },
    {
        "codigo": 213,
        "letra": "C",
        "titulo": "NOTA DE CRÉDITO MIPYME",
        "nombre": "Nota de Crédito Electrónica MiPyMEs (FCE) C",
        "clase": "FCE MiPyMEs (Ley 27.440)",
        "discrimina_iva": False,
        "requiere_cuit": True,
        "es_nota_credito": True,
        "es_nota_debito": False,
        "es_fce": True,
    },
]

TIPOS_COMPROBANTE_MAP: dict[int, dict] = {
    item["codigo"]: item for item in TIPOS_COMPROBANTE_ARCA
}

CODIGOS_NOTA_CREDITO: set[int] = {
    item["codigo"] for item in TIPOS_COMPROBANTE_ARCA if item["es_nota_credito"]
}

CODIGOS_NOTA_DEBITO: set[int] = {
    item["codigo"] for item in TIPOS_COMPROBANTE_ARCA if item["es_nota_debito"]
}

CODIGOS_FCE_MIPYME: set[int] = {
    item["codigo"] for item in TIPOS_COMPROBANTE_ARCA if item["es_fce"]
}


def get_info_tipo_comprobante(codigo: int) -> dict:
    return TIPOS_COMPROBANTE_MAP.get(
        int(codigo),
        {
            "codigo": int(codigo),
            "letra": "B" if int(codigo) in (6, 7, 8, 9) else "C",
            "titulo": "COMPROBANTE",
            "nombre": f"Comprobante {codigo}",
            "clase": "Otros",
            "discrimina_iva": False,
            "requiere_cuit": False,
            "es_nota_credito": False,
            "es_nota_debito": False,
            "es_fce": False,
        },
    )


class Factura(Base):
    """
    =============================================================================
    Model: Factura
    =============================================================================
    Guarda los comprobantes electrónicos emitidos en ARCA (ex AFIP),
    tanto aquellos originados masivamente por cobranzas de cuotas (`origen='COBRANZA'`)
    como las emisiones individuales desde el módulo de Finanzas (`origen='FINANZAS'`).
    """
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cobranza_id = Column(Integer, ForeignKey("cobranzas.id"), nullable=True, unique=True)
    origen = Column(String(30), nullable=False, default="COBRANZA")

    punto_venta = Column(Integer, nullable=False, default=1)
    tipo_comprobante = Column(Integer, nullable=False)  # ej. 1 (Fact A), 6 (Fact B), 3 (NC A), 11 (Fact C), etc.
    nro_comprobante = Column(Integer, nullable=False)

    fecha_emision = Column(Date, nullable=False)
    concepto_arca = Column(Integer, nullable=False, default=2)  # 1: Productos, 2: Servicios, 3: Productos y Servicios
    fecha_servicio_desde = Column(Date, nullable=True)
    fecha_servicio_hasta = Column(Date, nullable=True)
    fecha_vencimiento_pago = Column(Date, nullable=True)

    # Datos del Receptor
    tipo_doc_receptor = Column(String(15), nullable=True, default="CUIT")
    cuit_cliente = Column(String(20), nullable=True)
    razon_social_receptor = Column(String(200), nullable=True)
    domicilio_receptor = Column(String(255), nullable=True)
    condicion_iva_receptor = Column(String(60), nullable=True)
    provincia_id = Column(Integer, ForeignKey("provincias.id"), nullable=True)

    # Comprobante asociado (para Notas de Crédito / Débito) y FCE
    comprobante_asociado_id = Column(Integer, ForeignKey("facturas.id"), nullable=True)
    comprobante_asociado_str = Column(String(100), nullable=True)
    cbu_emisor = Column(String(22), nullable=True)

    # Desglose de Importes e Impuestos
    importe_no_gravado = Column(Numeric(15, 2), nullable=False, default=0.0)
    importe_exento = Column(Numeric(15, 2), nullable=False, default=0.0)
    neto_gravado_0 = Column(Numeric(15, 2), nullable=False, default=0.0)
    neto_gravado_21 = Column(Numeric(15, 2), nullable=False, default=0.0)
    neto_gravado_105 = Column(Numeric(15, 2), nullable=False, default=0.0)
    neto_gravado_27 = Column(Numeric(15, 2), nullable=False, default=0.0)
    iva_21 = Column(Numeric(15, 2), nullable=False, default=0.0)
    iva_105 = Column(Numeric(15, 2), nullable=False, default=0.0)
    iva_27 = Column(Numeric(15, 2), nullable=False, default=0.0)
    percepcion_iva = Column(Numeric(15, 2), nullable=False, default=0.0)
    percepcion_iibb = Column(Numeric(15, 2), nullable=False, default=0.0)
    otros_impuestos = Column(Numeric(15, 2), nullable=False, default=0.0)
    importe_total = Column(Numeric(15, 2), nullable=False)

    cae = Column(String(50), nullable=True)
    vencimiento_cae = Column(Date, nullable=True)
    condicion_iva_receptor_id = Column(Integer, nullable=True)
    estado_arca = Column(String(30), nullable=True, default="MOCK")

    items_detalle = Column(JSON, nullable=True)
    observaciones = Column(String(500), nullable=True)

    # Audit
    creado_en = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    cobranza = relationship("Cobranza", back_populates="factura")
    provincia = relationship("Provincia")
    comprobante_asociado = relationship("Factura", remote_side=[id])

    def __repr__(self):
        return f"<Factura(pv={self.punto_venta}, tipo={self.tipo_comprobante}, comp={self.nro_comprobante}, cae={self.cae})>"


def ensure_facturas_schema(engine) -> None:
    """
    Asegura de forma idempotente que la tabla `facturas` existente cuente con las
    columnas requeridas para la emisión individual de ARCA en Finanzas y que
    `cobranza_id` permita NULL.
    """
    try:
        inspector = inspect(engine)
        if not inspector.has_table("facturas"):
            return

        existing_cols = {col["name"]: col for col in inspector.get_columns("facturas")}
        dialect = engine.dialect.name

        new_columns_sql = [
            ("origen", "VARCHAR(30) NOT NULL DEFAULT 'COBRANZA'"),
            ("concepto_arca", "INTEGER NOT NULL DEFAULT 2"),
            ("fecha_servicio_desde", "DATE NULL"),
            ("fecha_servicio_hasta", "DATE NULL"),
            ("fecha_vencimiento_pago", "DATE NULL"),
            ("tipo_doc_receptor", "VARCHAR(15) NULL DEFAULT 'CUIT'"),
            ("razon_social_receptor", "VARCHAR(200) NULL"),
            ("domicilio_receptor", "VARCHAR(255) NULL"),
            ("condicion_iva_receptor", "VARCHAR(60) NULL"),
            ("provincia_id", "INTEGER NULL"),
            ("comprobante_asociado_id", "INTEGER NULL"),
            ("comprobante_asociado_str", "VARCHAR(100) NULL"),
            ("cbu_emisor", "VARCHAR(22) NULL"),
            ("importe_no_gravado", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("importe_exento", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("neto_gravado_0", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("neto_gravado_21", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("neto_gravado_105", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("neto_gravado_27", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("iva_21", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("iva_105", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("iva_27", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("percepcion_iva", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("percepcion_iibb", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("otros_impuestos", "NUMERIC(15, 2) NOT NULL DEFAULT 0.00"),
            ("condicion_iva_receptor_id", "INTEGER NULL"),
            ("estado_arca", "VARCHAR(30) NULL DEFAULT 'MOCK'"),
            ("items_detalle", "JSON NULL"),
            ("observaciones", "VARCHAR(500) NULL"),
        ]

        with engine.begin() as conn:
            if dialect == "postgresql":
                cob_col = existing_cols.get("cobranza_id")
                if cob_col and not cob_col.get("nullable", True):
                    conn.execute(text("ALTER TABLE facturas ALTER COLUMN cobranza_id DROP NOT NULL"))

            for col_name, col_def in new_columns_sql:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE facturas ADD COLUMN {col_name} {col_def}"))
    except Exception as exc:
        print(f"⚠️ Warning al verificar esquema de facturas: {exc}")
