
"""
SIGA - Sistema de Inventario y Gestion Agricola
Interfaz grafica (Streamlit) construida sobre el esquema SQL de siga_referencia.py

Ejecutar localmente:
    pip install streamlit
    streamlit run app.py

Desplegar con enlace publico compartible:
    Ver README.md (Streamlit Community Cloud, gratis, ~5 minutos)
"""

import sqlite3
from datetime import date

import pandas as pd
import streamlit as st

DB_PATH = "siga_inventario.db"

st.set_page_config(page_title="SIGA - Inventario", page_icon="🌱", layout="wide")


# ------------------------------------------------------------------
# CONEXION Y ESQUEMA (mismo modelo de siga_referencia.py)
# ------------------------------------------------------------------
@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_esquema(conn):
    ya_existe = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='productos'"
    ).fetchone()
    if ya_existe:
        return

    conn.executescript("""
    CREATE TABLE proveedores (
        id_proveedor    INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT NOT NULL,
        telefono        TEXT,
        ciudad          TEXT
    );
    CREATE TABLE clientes (
        id_cliente      INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT NOT NULL,
        telefono        TEXT,
        ciudad          TEXT
    );
    CREATE TABLE productos (
        id_producto     INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre          TEXT NOT NULL,
        categoria       TEXT NOT NULL,
        unidad_medida   TEXT NOT NULL,
        precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
        stock_minimo    INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE movimientos (
        id_movimiento   INTEGER PRIMARY KEY AUTOINCREMENT,
        id_producto     INTEGER NOT NULL,
        tipo            TEXT NOT NULL CHECK (tipo IN ('entrada', 'salida')),
        cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
        fecha           TEXT NOT NULL,
        id_proveedor    INTEGER,
        id_cliente      INTEGER,
        observacion     TEXT,
        FOREIGN KEY (id_producto)  REFERENCES productos(id_producto),
        FOREIGN KEY (id_proveedor) REFERENCES proveedores(id_proveedor),
        FOREIGN KEY (id_cliente)   REFERENCES clientes(id_cliente)
    );
    CREATE VIEW vw_inventario_actual AS
    SELECT
        p.id_producto, p.nombre, p.categoria, p.unidad_medida, p.stock_minimo,
        COALESCE((SELECT SUM(cantidad) FROM movimientos
                  WHERE id_producto = p.id_producto AND tipo = 'entrada'), 0)
        -
        COALESCE((SELECT SUM(cantidad) FROM movimientos
                  WHERE id_producto = p.id_producto AND tipo = 'salida'), 0)
        AS stock_actual
    FROM productos p;
    """)

    conn.executemany(
        "INSERT INTO proveedores (nombre, telefono, ciudad) VALUES (?, ?, ?)",
        [
            ("Agroinsumos del Valle", "3201234567", "Palmira"),
            ("Semillas y Fertilizantes SAS", "3179876543", "Cali"),
        ],
    )
    conn.executemany(
        "INSERT INTO clientes (nombre, telefono, ciudad) VALUES (?, ?, ?)",
        [
            ("Finca La Esperanza", "3115556677", "Buga"),
            ("Cooperativa Cañicultores del Sur", "3123334455", "Florida"),
        ],
    )
    conn.executemany(
        """INSERT INTO productos (nombre, categoria, unidad_medida,
                                   precio_unitario, stock_minimo)
           VALUES (?, ?, ?, ?, ?)""",
        [
            ("Urea 46%", "Fertilizante", "bulto 50kg", 145000, 10),
            ("Glifosato", "Agroquimico", "litro", 38000, 20),
            ("Semilla de caña V-CP01", "Semilla", "bulto", 52000, 15),
            ("Cal agricola", "Enmienda", "bulto 40kg", 21000, 30),
        ],
    )
    conn.executemany(
        """INSERT INTO movimientos (id_producto, tipo, cantidad, fecha,
                                     id_proveedor, id_cliente, observacion)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (1, "entrada", 40, "2026-08-01", 1, None, "Compra inicial"),
            (2, "entrada", 60, "2026-08-01", 2, None, "Compra inicial"),
            (3, "entrada", 30, "2026-08-02", 1, None, "Compra inicial"),
            (1, "salida", 15, "2026-08-10", None, 1, "Aplicacion lote 4"),
            (2, "salida", 25, "2026-08-12", None, 2, "Control de malezas"),
            (3, "salida", 10, "2026-08-15", None, 1, "Siembra nueva suerte"),
            (4, "entrada", 50, "2026-08-03", 2, None, "Compra inicial"),
            (4, "salida", 45, "2026-08-20", None, 2, "Correccion de pH suelo"),
        ],
    )
    conn.commit()


conn = get_connection()
inicializar_esquema(conn)


# ------------------------------------------------------------------
# FUNCIONES QUE ENVUELVEN EL SQL (igual que en siga_referencia.py,
# TEMA 11 - cada una alimenta un boton o formulario de la interfaz)
# ------------------------------------------------------------------
def registrar_entrada(id_producto, cantidad, id_proveedor, obs=""):
    conn.execute(
        """INSERT INTO movimientos (id_producto, tipo, cantidad, fecha,
                                     id_proveedor, observacion)
           VALUES (?, 'entrada', ?, ?, ?, ?)""",
        (id_producto, cantidad, str(date.today()), id_proveedor, obs),
    )
    conn.commit()


def registrar_salida(id_producto, cantidad, id_cliente, obs=""):
    conn.execute(
        """INSERT INTO movimientos (id_producto, tipo, cantidad, fecha,
                                     id_cliente, observacion)
           VALUES (?, 'salida', ?, ?, ?, ?)""",
        (id_producto, cantidad, str(date.today()), id_cliente, obs),
    )
    conn.commit()


def df(query, params=()):
    return pd.read_sql_query(query, conn, params=params)


# ------------------------------------------------------------------
# INTERFAZ - LANDING / PESTAÑAS
# ------------------------------------------------------------------
st.markdown(
    """
    <style>
    .siga-hero {padding: 1.5rem 0 1rem;}
    .siga-hero h1 {font-size: 2.2rem; margin-bottom: 0.2rem;}
    .siga-hero p {color: #5f5e5a; font-size: 1.05rem;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="siga-hero">
        <h1>🌱 SIGA — Sistema de Inventario y Gestión Agrícola</h1>
        <p>Proyecto de Programación 2 · Registro y análisis de entradas y salidas de inventario</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_inicio, tab_formulario, tab_dashboard = st.tabs(
    ["🏠 Inicio", "📝 Registrar movimiento", "📊 Inventario y análisis"]
)

# --------------------------- TAB: INICIO ---------------------------
with tab_inicio:
    inventario = df("SELECT * FROM vw_inventario_actual")
    alertas = inventario[inventario["stock_actual"] < inventario["stock_minimo"]]

    c1, c2, c3 = st.columns(3)
    c1.metric("Productos registrados", len(inventario))
    c2.metric("Unidades en inventario", int(inventario["stock_actual"].sum()))
    c3.metric("Alertas de stock bajo", len(alertas))

    st.markdown("---")
    st.subheader("¿Qué puedes hacer aquí?")
    st.markdown(
        """
        - **Registrar movimiento**: simula una compra (entrada) o una venta/consumo (salida) llenando un formulario simple.
        - **Inventario y análisis**: revisa el stock actual calculado en tiempo real y las alertas de productos por debajo del mínimo.

        Esta app corre sobre la misma lógica SQL vista en clase (`siga_referencia.py`):
        cada acción del formulario ejecuta una de las funciones del Tema 11.
        """
    )

# --------------------------- TAB: FORMULARIO ---------------------------
with tab_formulario:
    st.subheader("Registrar entrada o salida de inventario")

    productos_df = df("SELECT id_producto, nombre FROM productos")
    proveedores_df = df("SELECT id_proveedor, nombre FROM proveedores")
    clientes_df = df("SELECT id_cliente, nombre FROM clientes")

    tipo = st.radio("Tipo de movimiento", ["Entrada (compra)", "Salida (venta/consumo)"], horizontal=True)

    with st.form("form_movimiento", clear_on_submit=True):
        producto_nombre = st.selectbox("Producto", productos_df["nombre"])
        cantidad = st.number_input("Cantidad", min_value=1, step=1)

        if tipo.startswith("Entrada"):
            tercero_nombre = st.selectbox("Proveedor", proveedores_df["nombre"])
        else:
            tercero_nombre = st.selectbox("Cliente", clientes_df["nombre"])

        observacion = st.text_input("Observación (opcional)")
        enviado = st.form_submit_button("Registrar")

        if enviado:
            id_producto = int(
                productos_df.loc[productos_df["nombre"] == producto_nombre, "id_producto"].iloc[0]
            )
            if tipo.startswith("Entrada"):
                id_proveedor = int(
                    proveedores_df.loc[proveedores_df["nombre"] == tercero_nombre, "id_proveedor"].iloc[0]
                )
                registrar_entrada(id_producto, int(cantidad), id_proveedor, observacion)
            else:
                id_cliente = int(
                    clientes_df.loc[clientes_df["nombre"] == tercero_nombre, "id_cliente"].iloc[0]
                )
                registrar_salida(id_producto, int(cantidad), id_cliente, observacion)
            st.success(f"Movimiento registrado: {cantidad} unidades de {producto_nombre}.")
            st.rerun()

    st.markdown("---")
    st.caption("Últimos movimientos registrados")
    ultimos = df(
        """SELECT m.fecha, p.nombre AS producto, m.tipo, m.cantidad, m.observacion
           FROM movimientos m JOIN productos p ON p.id_producto = m.id_producto
           ORDER BY m.id_movimiento DESC LIMIT 8"""
    )
    st.dataframe(ultimos, use_container_width=True, hide_index=True)

# --------------------------- TAB: DASHBOARD ---------------------------
with tab_dashboard:
    st.subheader("Inventario actual")
    inventario = df("SELECT * FROM vw_inventario_actual")
    st.dataframe(
        inventario.rename(
            columns={
                "nombre": "Producto",
                "categoria": "Categoría",
                "unidad_medida": "Unidad",
                "stock_minimo": "Stock mínimo",
                "stock_actual": "Stock actual",
            }
        )[["Producto", "Categoría", "Unidad", "Stock mínimo", "Stock actual"]],
        use_container_width=True,
        hide_index=True,
    )

    st.bar_chart(inventario.set_index("nombre")[["stock_actual", "stock_minimo"]])

    alertas = inventario[inventario["stock_actual"] < inventario["stock_minimo"]]
    if len(alertas):
        st.warning(f"⚠️ {len(alertas)} producto(s) por debajo del stock mínimo:")
        st.dataframe(alertas[["nombre", "stock_actual", "stock_minimo"]], use_container_width=True, hide_index=True)
    else:
        st.success("Todos los productos están por encima de su stock mínimo.")
