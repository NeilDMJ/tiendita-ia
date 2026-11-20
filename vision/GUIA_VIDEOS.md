# Guía para grabar los videos del dataset

Cada video se convierte en ~70 fotos (1 cada 0.5 s). El nombre del archivo dice qué producto es, así que **no hay que etiquetar a mano**. Por eso las reglas de abajo importan: si un video tiene otro producto o se llama mal, el modelo aprende algo equivocado.

## 1. Configurar el celular (una vez)

- Resolución **1080p a 30 fps**. No 4K: los archivos pesan 4 veces más y no mejora el modelo.
- iPhone: Ajustes → Cámara → Formatos → **"Más compatible"** (si no, el video sale en HEVC y puede no leerse).
- Lente normal **1x**, sin zoom ni modo retrato, sin filtros ni efectos.
- **Celular vertical**, igual que lo usará el tendero en la app.
- Limpia el lente.

## 2. Las sesiones

Una **sesión** = un lugar + una luz. Cada integrante graba **una sesión completa** con su celular: así cambian lugar, luz y cámara a la vez.

El equipo grabó **2 sesiones**, una por iluminación:

| Sesión | Uso | Luz |
|---|---|---|
| `s1` | Entrenamiento (+ validación con el final de cada video) | Iluminación 1 |
| `s2` | Prueba (el modelo nunca la ve al entrenar) | Iluminación 2 |

Si hay tiempo, una sesión más en **otro lugar** (`s3`) mejora la validación y la métrica.

- **No repitan lugar entre sesiones.**
- **Guarden un quinto lugar sin usar** para la demo en vivo ante el jurado.

## 3. Qué grabar en cada sesión: 12 videos

| Archivo | Contenido |
|---|---|
| `s1_agua_1l.mp4` | Solo el agua Ciel 1 L |
| `s1_doritos.mp4`, `s1_doritos_2.mp4` | Doritos Nacho y Doritos Pizzerola (misma clase: mismo precio) |
| `s1_emperador_vainilla.mp4` | Solo Emperador vainilla |
| `s1_chokis.mp4` | Solo Chokis |
| `s1_papas_chidas_limon.mp4` | Solo Papas Chidas limón |
| `s1_sprite_chica.mp4` | Solo la Sprite |
| `s1_coca_cola.mp4` | Solo la Coca-Cola |
| `s1_te_helado.mp4` | Solo el té helado |
| `s1_fritos_salados.mp4` | Solo Fritos salados |
| `s1_agua_members_mark.mp4` | Solo el agua Member's Mark |
| `s1_agua_bonafont.mp4` | Solo el agua Bonafont |
| `s1_fondo.mp4` | **Ningún** producto: el lugar vacío, la mano sin nada, objetos que no son de los 11 |

Graben **~60 s** por video: los de 15–30 s dejan muy pocas fotos y esa clase sale mal en la prueba.
Cambien `s1` por su sesión. Los nombres deben ser **exactamente** los de `clases.txt` (minúsculas, guion bajo, sin acentos).

## 4. Cómo grabar cada video (30–40 s)

Muévanse **despacio**: un movimiento rápido deja fotos borrosas que no sirven.

| Segundos | Qué hacer |
|---|---|
| 0–10 | Producto sobre la superficie. Rodéenlo con el celular o gírenlo despacio para que se vean **todos sus lados**. |
| 10–20 | Acérquense y aléjense (de ~20 cm a ~80 cm). Cambien la altura: de frente, desde arriba, inclinado a 45°. |
| 20–30 | **En la mano**, como en el cobro: pásenlo frente a la cámara, con los dedos tapando un poco, inclinado. |
| 30–40 | Acostado, de cabeza, de lado, de espaldas (la parte de atrás también cuenta). |

El video de `fondo`: 30 s recorriendo el lugar vacío, la mano abierta frente a la cámara y objetos cualquiera (llaves, taza, cuaderno).

## 5. Reglas que no se pueden romper

1. **Un solo producto de los 11 por video.** Si aparece otro, aunque sea al fondo, esas fotos quedan mal etiquetadas.
2. **Nada de caras, pantallas con datos, documentos o tickets** (bases §10). Si alguien entra al cuadro, corten y repitan.
3. **El producto debe verse en todo el video**, salvo en el de `fondo`.
4. El audio no importa: se descarta.

## 6. Pares que se confunden: un poco más de cuidado

- **Las 3 aguas (Ciel, Bonafont, Member's Mark)**: enfoquen **etiqueta y tapa** de cerca y desde varios ángulos.
- **Emperador ↔ Chokis**: frente y costados del paquete.
- **Fritos ↔ Doritos ↔ Papas Chidas**, y **té helado ↔ Doritos**: el frente de la bolsa con el logo.

## 7. Pasar los videos a la computadora

- **No por WhatsApp**: comprime los videos y baja mucho la calidad.
- Usen **cable USB o Google Drive**.
- Una carpeta por sesión: `videos/s1/`, `videos/s2/`, …
- Peso esperado: ~60–80 MB por video, ~2.5 GB en total. Las fotos se extraen en la laptop y solo esas se suben al DLI.

## Checklist por integrante

- [ ] Celular en 1080p 30 fps, vertical, 1x.
- [ ] 12 videos de ~60 s (11 productos, Doritos en 2 videos, + fondo).
- [ ] Nombres `sN_<clase>.mp4` exactos.
- [ ] Un solo producto por video, sin caras ni datos personales.
- [ ] Videos copiados por cable o Drive a `videos/sN/`.
