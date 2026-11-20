# Catálogo demo (productos básicos de una tiendita)

Precios aproximados en MXN, solo ilustrativos para datos de prueba; ajustar a los productos que el equipo consiga fotografiar. Se eligen productos **empacados y con diseño distinguible** (el detector los reconoce mejor). Lo de granel (tortillas, huevo, jitomate) va por texto/voz con el asistente.

| # | clase_vision | Producto | Categoría | Precio aprox. | Caduca |
|---|---|---|---|---|---|
| 1 | coca_600 | Coca-Cola 600 ml | Bebidas | 20 | no |
| 2 | agua_1l | Agua embotellada 1 L | Bebidas | 15 | no |
| 3 | jugo_boing | Jugo Boing 500 ml | Bebidas | 15 | sí |
| 4 | leche_1l | Leche Lala 1 L | Lácteos | 29 | sí |
| 5 | pan_caja | Pan de caja Bimbo | Panadería | 45 | sí |
| 6 | gansito | Gansito Marinela | Botanas/dulces | 18 | sí |
| 7 | sabritas | Sabritas Original 45 g | Botanas | 20 | sí |
| 8 | takis | Takis Fuego 56 g | Botanas | 20 | sí |
| 9 | galletas_marias | Galletas Marías Gamesa | Galletas | 16 | sí |
| 10 | sopa_maruchan | Sopa Maruchan | Despensa | 17 | sí |
| 11 | atun_lata | Atún Dolores en lata | Despensa | 24 | sí |
| 12 | frijoles_lata | Frijoles La Sierra | Despensa | 22 | sí |
| 13 | aceite_1l | Aceite 1-2-3 1 L | Despensa | 45 | no |
| 14 | papel_higienico | Papel higiénico (rollo) | Limpieza | 10 | no |
| 15 | jabon_zote | Jabón Zote | Limpieza | 20 | no |

Notas para el dataset de visión:
- ~100 fotos por producto, 3 o más "sesiones" (fondo/luz/ángulo distintos); dividir train/val/test **por sesión**.
- Añadir fotos con varios productos juntos (para detección en cobro más adelante) y una clase `otro` / fondo sin producto.
- Marcas reales: se usan solo como datos de prueba de la demo; no mostrar información personal ni de terceros.
