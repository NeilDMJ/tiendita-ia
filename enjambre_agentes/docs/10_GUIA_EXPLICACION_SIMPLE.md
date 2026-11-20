# Guía en Lenguaje Simple: Qué es Tiendita IA, Qué Hace LoRA y Cómo Usamos NVIDIA

> **¿Para quién es este documento?** Para explicar el proyecto a **cualquier persona** (dueños de tiendas, clientes, jueces, profesores, inversionistas o familiares) usando palabras cotidianas y **sin tecnicismos**.

---

## 1. ¿Qué problema resuelve Tiendita IA?

El dueño de una tiendita de abarrotes suele hacer el trabajo de muchas personas al mismo tiempo:
- Atender a los clientes y cobrar en mostrador.
- Revisar qué productos se están acabando o están a punto de caducar.
- Llevar las cuentas del día para saber cuánto dinero entró y cuánto se ganó de verdad.
- Pensar promociones para sacar rápido la mercancía que casi vence.
- Resolver dudas o fallas cuando un cliente quiere pagar con **CoDi, SPEI o DiMo** desde su celular.

**Tiendita IA** nació para quitarle esa carga de encima, dándole un **equipo digital de 7 ayudantes inteligentes** que trabajan juntos y conectados directamente a la caja registradora y al inventario real de su tienda.

---

## 2. Los 7 ayudantes digitales de la tienda

En lugar de usar un solo programa genérico que hace todo a medias, dividimos el trabajo como en un negocio bien organizado:

| Ayudante | Su papel en la tienda | Ejemplo de cómo ayuda |
|---|---|---|
| **1. El Coordinador** *(Supervisor)* | Escucha lo que pide el dueño (por texto, foto o desde la pantalla de cobro) y decide qué ayudante debe atenderlo. | Si le preguntas cuánto ganaste hoy, le pasa la pregunta al Contador; si hay un problema cobrando con QR, llama al Guía de Pagos. |
| **2. El Encargado de Bodega** *(Control)* | Vigila el inventario, revisa fechas de caducidad y prepara pedidos de mercancía. | Avisa que 5 paquetes de pan caducan esta semana y lee una foto de la factura del proveedor para dar de alta los productos. |
| **3. El Cajero** *(Vendedor)* | Arma la cuenta, revisa precios, sugiere complementos y registra las ventas. | Si un cliente compra botanas, puede sugerir un refresco, calcula el total y deja lista la venta para cobrarse. |
| **4. El Contador** *(Analista)* | Revisa únicamente los números reales de la tienda (nunca modifica nada por error). | Dice cuánto se vendió hoy, cuánto efectivo entró y qué productos dejan mejor ganancia. |
| **5. El Investigador de Mercado** *(Investigador)* | Consulta precios, tendencias y competencia fuera de la tienda. | Compara si el precio de la leche o el refresco está competitivo frente a otros comercios. |
| **6. El Creativo de Marketing** *(Publicista)* | Crea ideas de combos, mensajes listos para WhatsApp y guiones de video corto. | Si un producto está por caducar, diseña una oferta llamativa para venderlo hoy mismo y no perder dinero. |
| **7. El Guía de Pagos Digitales** *(Tutor UI)* | Ayuda paso a paso cuando algo falla al cobrar con **CoDi, SPEI o DiMo**. | Si el código QR se venció, responde en **dos frases cortas** exactamente qué hacer, sin pedir jamás contraseñas ni NIPs. |

---

## 3. ¿Qué lo hace seguro y práctico en la vida real?

1. **El dueño siempre tiene la última palabra:**
   Antes de cobrar una venta, dar de baja mercancía o confirmar un pedido, el sistema se detiene y pregunta: *"¿Apruebas hacer esto? Sí o No"*. Nunca toma decisiones delicadas a escondidas.
2. **Puede "ver" fotos reales:**
   El dueño puede tomarle foto a un estante, a productos en el mostrador o a un ticket de compra del proveedor, y el sistema reconoce los artículos y cantidades automáticamente.
3. **Protege la privacidad del negocio y del cliente:**
   El ayudante de mostrador tiene prohibido mostrar cuánto le costó al dueño comprar cada producto, y el guía de pagos nunca pide contraseñas, códigos de seguridad ni claves bancarias.
4. **Se puede usar desde cualquier celular o computadora:**
   Funciona desde la computadora de la tienda, desde otra computadora conectada al mismo Wi-Fi o incluso desde internet mediante un enlace seguro para probarlo a distancia.

---

## 4. ¿Qué es LoRA y para qué lo entrenamos? (Explicado con palabras sencillas)

Muchas personas escuchan "entrenar una inteligencia artificial" e imaginan edificios llenos de computadoras gigantes y millones de dólares. **LoRA** cambia eso por completo.

### La analogía de las "clases particulares"
Imagina a un estudiante recién graduado que ya sabe leer, escribir y hablar muy bien español, pero **nunca ha trabajado en una tiendita en México** ni conoce los problemas del día a día con CoDi, SPEI o DiMo.

- **Reentrenar todo desde cero** sería como mandarlo otra vez desde la primaria hasta la universidad: carísimo y lentísimo.
- **Usar LoRA** es darle un **cuaderno pequeño de clases particulares** enfocado únicamente en el oficio de la tiendita: cómo responder corto (máximo 2 oraciones), qué hacer si falla un cobro digital, qué palabras usar en México y qué datos jamás debe pedir.

### Qué hicimos exactamente en este proyecto con LoRA
1. **Preparamos 118 ejemplos reales de la tiendita:** combinamos guías oficiales de pagos digitales en México (CoDi, SPEI, DiMo), situaciones reales de mostrador e inventario, y reglas de seguridad.
2. **Entrenamos el cuaderno de especialidad en esta misma laptop:** en lugar de rentar servidores caros, usamos la tarjeta gráfica de esta computadora y el entrenamiento completo tomó **apenas 1 minuto (63 segundos)**.
3. **Medimos que realmente aprendió:** antes de las clases particulares, el modelo daba respuestas largas, confusas o demasiado generales. Después del entrenamiento, su nivel de error bajó más de un **62%** y empezó a contestar directo al grano, en dos frases claras.
4. **Lo guardamos listo para trabajar gratis dentro de la computadora:** empaquetamos ese conocimiento en un modelo propio llamado **`tiendita-lora-v1`** dentro del programa local **Ollama**.
   - **Resultado:** el guía de pagos puede responder en **menos de medio segundo**, **sin pagar por cada mensaje** y **sin depender de internet externo** para pensar su respuesta.

> **Resumen en una frase:** LoRA nos permitió tomar una inteligencia artificial general y darle "clases particulares" en nuestra propia computadora durante un minuto, para convertirla en un asistente especialista en tienditas mexicanas que trabaja rápido y sin costo por consulta.

---

## 5. ¿Cómo se usó la tecnología de NVIDIA?

La tecnología de **NVIDIA** es el motor que impulsa casi todo el sistema, tanto en la nube como directamente en la computadora local. Se utilizó en **cinco partes concretas**:

1. **Los "cerebros" principales del equipo (modelos NVIDIA Nemotron):**
   De fábrica, los 7 ayudantes trabajan con modelos de inteligencia artificial de NVIDIA:
   - Un cerebro grande y profundo para las tareas que exigen más análisis (coordinar al equipo, revisar finanzas e investigar el mercado).
   - Un cerebro más ágil y rápido para el trabajo inmediato de mostrador, bodega, promociones y ayuda en pantalla.
   *(Además, el sistema tiene respaldo automático: si en algún momento falla la conexión a la nube, cambia solo a otro proveedor para que la tienda nunca se quede sin servicio).*

2. **Los "ojos" del sistema (Visión de NVIDIA):**
   Cuando el dueño sube una foto de productos, un estante o un ticket de proveedor, un modelo visual de NVIDIA analiza la imagen e identifica qué artículos aparecen para cargarlos a la caja o al inventario.

3. **La "biblioteca inteligente" de pagos digitales (Búsqueda con NVIDIA):**
   Las guías oficiales de CoDi, SPEI y DiMo del Banco de México se convirtieron en una biblioteca de búsqueda inteligente usando tecnología de NVIDIA. Así, cuando aparece un error en la pantalla de cobro, el sistema encuentra en milisegundos el dato exacto que lo resuelve, sin inventar respuestas.

4. **Reglas de seguridad y mejora continua (Ecosistema NVIDIA NeMo):**
   - **Seguridad:** inspirados en **NVIDIA Guardrails**, pusimos barreras claras para que ningún asistente revele los costos privados del dueño ni solicite información bancaria confidencial.
   - **Aprendizaje continuo:** cada vez que el dueño aprueba o corrige una propuesta del asistente, el sistema guarda ese aprendizaje en el formato oficial de **NVIDIA NeMo**, listo para seguir perfeccionando los modelos con el uso real de la tienda.

5. **Entrenamiento e inteligencia local en la laptop (Tarjeta gráfica NVIDIA RTX 5060):**
   La tarjeta gráfica **NVIDIA RTX 5060** de esta computadora hizo dos trabajos clave en el mundo real:
   - **Entrenó nuestro LoRA propio** en poco más de un minuto usando aceleración gráfica de NVIDIA.
   - **Ejecuta hoy el modelo entrenado (`tiendita-lora-v1`)** de forma local a casi 100 palabras/fragmentos por segundo, demostrando que una tiendita puede tener su propia inteligencia artificial especializada sin pagar cuotas por cada consulta.

---

## 6. Explicación de 30 segundos (para presentar el proyecto en vivo)

> *"Tiendita IA es un equipo digital de 7 ayudantes inteligentes que apoya al dueño de una tiendita de abarrotes con su inventario, sus ventas, sus cuentas, sus promociones y sus cobros digitales con CoDi, SPEI y DiMo. Todo está conectado a la base de datos real de la tienda, puede leer fotos de productos o facturas y siempre pide permiso al dueño antes de hacer cambios importantes. Usamos tecnología de NVIDIA como motor principal —desde los modelos de razonamiento y visión hasta las reglas de seguridad— y además aprovechamos la tarjeta gráfica NVIDIA de esta computadora para entrenar nuestro propio asistente especializado con LoRA en solo un minuto, logrando que responda en menos de medio segundo, en español claro y sin costo por mensaje."*

---

*Si buscas el detalle técnico con métricas exactas, código y arquitectura, consulta:*
- [08_DIAGRAMA_INTERACCION_AGENTES.md](./08_DIAGRAMA_INTERACCION_AGENTES.md) — Mapa visual de cómo interactúan los 7 agentes.
- [09_REPORTE_TECNICO_LORA.md](./09_REPORTE_TECNICO_LORA.md) — Reporte técnico y métricas reales del entrenamiento LoRA y registro en Ollama.
- [05_STACK_NVIDIA_Y_RESILIENCIA.md](./05_STACK_NVIDIA_Y_RESILIENCIA.md) — Detalle técnico de toda la pila de NVIDIA NIM y NeMo.
