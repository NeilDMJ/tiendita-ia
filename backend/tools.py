"""Herramientas del agente Control (catálogo). El LLM solo propone llamadas;
el backend las valida y las ejecuta únicamente tras confirmación del usuario."""
from . import db

ESQUEMAS = {
    "crear_producto": {"nombre": str, "precio": (int, float), "costo": (int, float, type(None)),
                       "stock": int, "caducidad": (str, type(None)), "clase_vision": (str, type(None))},
    "actualizar_precio": {"nombre": str, "precio": (int, float)},
    "consultar_inventario": {"nombre": (str, type(None))},
    "ajustar_stock": {"nombre": str, "cantidad": int, "tipo": str},
}
REQUERIDOS = {
    "crear_producto": ["nombre", "precio", "stock"],
    "actualizar_precio": ["nombre", "precio"],
    "consultar_inventario": [],
    "ajustar_stock": ["nombre", "cantidad", "tipo"],
}


def validar(tool: str, args: dict) -> list[str]:
    """Devuelve lista de errores (vacía si es válida) o los campos que faltan."""
    if tool not in ESQUEMAS:
        return [f"herramienta desconocida: {tool}"]
    errs = [f"falta {k}" for k in REQUERIDOS[tool] if args.get(k) is None]
    for k, v in args.items():
        if k not in ESQUEMAS[tool]:
            errs.append(f"argumento no permitido: {k}")
        elif v is not None and not isinstance(v, ESQUEMAS[tool][k]):
            errs.append(f"tipo inválido en {k}")
    return errs


def ejecutar(tool: str, args: dict) -> dict:
    errs = validar(tool, args)
    if errs:
        raise ValueError("; ".join(errs))
    with db.conn() as c:
        if tool == "crear_producto":
            cur = c.execute(
                "INSERT INTO productos(nombre,clase_vision,precio,costo,stock,caducidad) VALUES(?,?,?,?,?,?)",
                (args["nombre"], args.get("clase_vision"), args["precio"], args.get("costo"),
                 args["stock"], args.get("caducidad")))
            if args["stock"]:
                c.execute("INSERT INTO movimientos_inventario(producto_id,tipo,cantidad) VALUES(?,?,?)",
                          (cur.lastrowid, "entrada", args["stock"]))
            return {"ok": True, "id": cur.lastrowid}
        if tool == "actualizar_precio":
            cur = c.execute("UPDATE productos SET precio=? WHERE nombre=? COLLATE NOCASE",
                            (args["precio"], args["nombre"]))
            if not cur.rowcount:
                raise ValueError("producto no encontrado")
            return {"ok": True}
        if tool == "consultar_inventario":
            n = args.get("nombre")
            rows = c.execute("SELECT * FROM productos WHERE (? IS NULL OR nombre LIKE ?)",
                             (n, f"%{n}%")).fetchall()
            return {"ok": True, "productos": [dict(r) for r in rows]}
        if tool == "ajustar_stock":
            if args["tipo"] not in ("entrada", "salida", "merma"):
                raise ValueError("tipo debe ser entrada, salida o merma")
            p = c.execute("SELECT id, stock FROM productos WHERE nombre=? COLLATE NOCASE",
                          (args["nombre"],)).fetchone()
            if not p:
                raise ValueError("producto no encontrado")
            delta = args["cantidad"] if args["tipo"] == "entrada" else -args["cantidad"]
            if p["stock"] + delta < 0:
                raise ValueError("el stock no puede quedar negativo")
            c.execute("UPDATE productos SET stock=stock+? WHERE id=?", (delta, p["id"]))
            c.execute("INSERT INTO movimientos_inventario(producto_id,tipo,cantidad) VALUES(?,?,?)",
                      (p["id"], args["tipo"], args["cantidad"]))
            return {"ok": True}
