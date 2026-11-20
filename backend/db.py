"""SQLite: esquema mínimo del catálogo (idea.md §6)."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("tiendita.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    clase_vision TEXT,
    precio REAL NOT NULL DEFAULT 0,
    costo REAL,
    stock INTEGER NOT NULL DEFAULT 0,
    caducidad TEXT
);
CREATE TABLE IF NOT EXISTS movimientos_inventario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    tipo TEXT NOT NULL CHECK (tipo IN ('entrada','salida','merma')),
    cantidad INTEGER NOT NULL,
    fecha TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL DEFAULT (datetime('now')),
    total REAL NOT NULL,
    metodo_pago TEXT NOT NULL CHECK (metodo_pago IN ('efectivo','transferencia','qr','tarjeta')),
    estado TEXT NOT NULL DEFAULT 'pagada'
);
CREATE TABLE IF NOT EXISTS venta_detalle (
    venta_id INTEGER NOT NULL REFERENCES ventas(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    cantidad INTEGER NOT NULL,
    precio REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venta_id INTEGER NOT NULL UNIQUE REFERENCES ventas(id),
    tipo TEXT NOT NULL,
    referencia TEXT,
    monto REAL,
    estado TEXT NOT NULL CHECK (estado IN ('pendiente','enviado','recibido','conciliado')),
    comprobante TEXT
);
CREATE TABLE IF NOT EXISTS gastos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL DEFAULT (datetime('now')),
    concepto TEXT NOT NULL,
    monto REAL NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'gasto',
    ticket TEXT
);
CREATE TABLE IF NOT EXISTS reportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    periodo TEXT NOT NULL,
    contenido TEXT NOT NULL,
    generado_por TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)
