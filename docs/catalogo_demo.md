# Catálogo demo (productos que el modelo de visión reconoce)

Los 11 productos que el equipo tiene físicamente para fotografiar y para la demo. Precios aproximados en MXN, solo ilustrativos para datos de prueba; ajustarlos al precio real. Lo de granel (tortillas, huevo, jitomate) va por texto/voz con el asistente.

El orden y los nombres de `clase_vision` deben coincidir con `vision/clases.txt`.

| # | clase_vision | Producto | Empaque | Categoría | Precio aprox. | Caduca |
|---|---|---|---|---|---|---|
| 1 | agua_1l | Agua Ciel 1 L | Botella PET | Bebidas | 15 | no |
| 2 | doritos | Doritos (Nacho o Pizzerola, mismo precio) | Bolsa | Botanas | 20 | sí |
| 3 | emperador_vainilla | Galletas Emperador vainilla | Paquete | Galletas | 20 | sí |
| 4 | chokis | Galletas Chokis | Paquete | Galletas | 20 | sí |
| 5 | papas_chidas_limon | Papas Chidas limón | Bolsa | Botanas | 15 | sí |
| 6 | sprite_chica | Sprite presentación chica (tamaño por confirmar) | Botella | Bebidas | 15 | no |
| 7 | coca_cola | Coca-Cola (tamaño por confirmar) | Botella | Bebidas | 20 | no |
| 8 | te_helado | Té helado en polvo Lagg's frutos rojos | Sobre | Bebidas | 18 | sí |
| 9 | fritos_salados | Fritos salados | Bolsa | Botanas | 18 | sí |
| 10 | agua_members_mark | Agua Member's Mark | Botella PET | Bebidas | 10 | no |
| 11 | agua_bonafont | Agua Bonafont | Botella PET | Bebidas | 15 | no |

Pares que el modelo puede confundir (revisarlos en la matriz de confusión):
- `agua_1l` ↔ `agua_bonafont` ↔ `agua_members_mark`: botellas transparentes; solo cambian etiqueta y tapa.
- `emperador_vainilla` ↔ `chokis`: misma marca (Gamesa).
- `fritos_salados` ↔ `doritos` ↔ `papas_chidas_limon`; `te_helado` (sobre rojo/naranja) ↔ `doritos`.

Fuera del modelo (2026-11-20): Electrolit, agua Tehuacán y manzana. Doritos Nacho y Pizzerola se unieron en `doritos` porque cuestan lo mismo.

Notas para el dataset de visión:
- 80–120 fotos por producto. Se grabaron 2 sesiones (una por iluminación): s1 = train (+ val con el final de cada video), s2 = test. Ver `vision/README.md`.
- Más fotos de los pares que se confunden, sobre todo del lado que muestra la diferencia (color, sabor).
- Fotos con varios productos juntos (cobro) y fotos de fondo sin producto.
- Marcas reales: se usan solo como datos de prueba de la demo; no mostrar información personal ni de terceros.

> Pendiente: el catálogo de los agentes (`enjambre_agentes/tools_bridge.py`) y los datos del asistente aún usan la lista anterior de 15 productos. Hay que alinearlos con esta tabla para que el SKU que detecta la visión exista en el inventario.
