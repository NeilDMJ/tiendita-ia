---
titulo: "¿Qué es y cómo funciona el SPEI? (presentación de Banco de México)"
descripcion: "Explicación breve del SPEI y de los 5 pasos de una transferencia."
fuente: "info/SPEI_funcionamiento.pdf"
tipo: "presentacion"
tema: "SPEI"
relevancia: "alta"
fecha_documento: "2018-05"
nota: "Documento de 2018; puede estar desactualizado en cifras o participantes."
fecha_ingesta: "2026-11-19"
---
# ¿Qué es y cómo funciona el SPEI? (presentación de Banco de México)

## ¿Qué es el SPEI?

- El Sistema de Pagos Electrónicos Interbancarios (SPEI) es la infraestructura de pagos del Banco de México que permite a sus participantes, (bancos, casas de bolsa, sofipos y otras entidades financieras reguladas) enviar y recibir pagos entre si para poder brindar a sus clientes finales el servicio de transferencias electrónicas en tiempo real.

- El SPEI puede conceptualizarse como una tubería central a la que se conectan los participantes, sobre la cual, de manera eficiente y segura se cargan y abonan las cuentas de los participantes (e.g. bancos) con el Banco de México para poder liquidar las operaciones entre participantes, ya sea que hayan sido enviadas por cuenta propia o por cuenta de sus clientes.

- Para realizar esa conexión con el SPEI los participantes realizan desarrollos propios o contratan a terceros para que les brinden ese servicio.

## ¿Cómo funciona el SPEI?

1. El cliente final (cuentahabiente) instruye desde su banca electrónica o aplicación móvil a su institución participante los pagos que desea realizar. Esto se hace siguiendo rigurosos controles de seguridad como contraseñas, elementos dinámicos (tokens) y pruebas de posesión de dispositivos (como mensajes a teléfonos móviles pre registrados), entre otros.

2. El participante valida los elementos de seguridad de la instrucción y guarda evidencia de que realizó esta validación.

3. El participante prepara las instrucciones de sus clientes, les incluye elementos de seguridad adicionales (sujeto a la circular 14/2017), sobre los cuales únicamente ellos tienen el control, y los envían al SPEI de Banco de México. Esta es la etapa que,en el caso de algunos participantes fue vulnerada.

4. El Banco de México verifica las firmas electrónicas de los participantes, que dan certeza de la integridad de la instrucción de pago, y procede a su procesamiento y posterior liquidación al participante receptor del pago.

5. Se informa a los participantes involucrados en la transferencia de recursos de la liquidación y el participante receptor del pago acredita los fondos en la cuenta de su cliente y envía al Banco de México la información para generar el Comprobante Electrónico de Pago (CEP).

## Cuándo se rechaza o se retiene un pago (según el diagrama de flujo original)

- Se **rechaza** el pago si el formato de la instrucción no es válido.
- Se **rechaza** el pago si la firma de la instrucción no es válida.
- Se **rechaza** el pago si los fondos de la cuenta del cliente no son suficientes.
- Si la instrucción es válida, se envía un acuse de recibo al emisor y la instrucción pasa a la cola de pagos por liquidar.
- Si el pago aún no se liquida, **permanece en cola**.
- Cuando el pago se liquida, la institución emisora y la receptora son notificadas, y la receptora acredita los recursos en la cuenta del beneficiario.
