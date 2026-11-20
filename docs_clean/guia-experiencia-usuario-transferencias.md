---
titulo: "Guías para la homologación de la experiencia de usuario en transferencias electrónicas desde dispositivos móviles (v1.0)"
descripcion: "Cómo deben verse y comportarse las apps al transferir: datos requeridos, confirmaciones, notificaciones; flujos de transferencia básica, Dimo y CoDi."
fuente: "https://www.banxico.org.mx/marco-normativo/normativa-emitida-por-el-banco-de-mexico/circular-14-2017/%7B470203D9-2C3C-1E33-A51E-3AE1DE2DE6FF%7D.pdf"
tipo: "pdf"
tema: "Experiencia de usuario, Dimo, CoDi, SPEI"
relevancia: "alta"
fecha_documento: "2026-06-16"
nota: "Publicado el 16-jun-2026; entra en vigor el 14-dic-2026."
fecha_ingesta: "2026-11-19"
---
# Guías para la homologación de la experiencia de usuario en transferencias electrónicas desde dispositivos móviles (v1.0)

## I. Introducción

**El Banco de México busca fomentar un ecosistema en donde los usuarios accedan a nuevas y mejores soluciones de pago** , en línea con sus finalidades de promover el sano desarrollo del sistema financiero y propiciar el buen funcionamiento de los sistemas de pagos. Como se ha observado en diversas implementaciones de infraestructuras de pago alrededor del mundo, la experiencia de uso puede fungir como una herramienta que optimice e impulse el uso de transferencias electrónicas.

**Al respecto, este Instituto Central determinó relevante establecer principios que deberán seguir las instituciones financieras en el diseño de los flujos de instrucción de transferencias.** Estos principios tienen como objetivo simplificar el proceso de instrucción de transferencias entre los proveedores de estos servicios, de forma que disminuyan las complejidades existentes de cara a los usuarios. Además, mantener uniformidad en el proceso de instrucción en todas las aplicaciones móviles que ofrezcan los servicios de transferencias permitirá que los usuarios elijan al proveedor de servicios financieros que más se ajuste a sus necesidades, sin que la complejidad en el envío de una transferencia sea un factor en la decisión de contratar un servicio financiero.

**El presente documento detalla los principios para lograr la estandarización del proceso de instrucción de transferencias, los requerimientos mínimos que deben estar presentes en la experiencia de los usuarios y el flujo de instrucción para los casos de negocio identificados.** El objetivo que se persigue es reducir las fricciones que existen en el envío de transferencias y asegurar que estas ocurran de manera intuitiva, fácil y rápida.

## II. Alcance

**Las especificaciones a que refieren las presentes Guías fueron establecidas mediante la Circular 9/2026** , que modifica las Reglas del SPEI, contenidas en la Circular 14/2017, y **la Circular 10/2026** , que modifica la Circular 3/2012, todas emitidas por el Banco de México.

**Las especificaciones contenidas en estas Guías serán aplicables a la transferencia electrónica que se realiza desde una cuenta de depósito o de fondos de pago electrónico, y que se dirige a una cuenta dentro de la misma Entidad**[**1**] **(intra institución) o a una cuenta en una Entidad diferente (inter institución), efectuadas desde aplicaciones móviles** y que están reconocidas en las siguientes Circulares:

- a) Órdenes de transferencia a que refiere la Circular 14/2017 y sus modificaciones;

- b) Transferencias electrónicas de fondos a que refiere la Circular 3/2012, y sus modificaciones;

Que se realizan por alguno de los siguientes sujetos:

- c) Entidades que actúan con el carácter de participantes en el SPEI, de conformidad con lo establecido en la Circular 14/2017, que ofrecen el servicio de envío de transferencias;

- d) Entidades que tienen el carácter de participante indirecto[2] , de conformidad con la Circular 14/2017, que ofrecen el servicio de envío de transferencias.

Estas especificaciones son aplicables a cualquier Aplicación para dispositivo móvil mediante la cual una Entidad provea los servicios indicados en los incisos a) y b) a personas físicas que envíen transferencias electrónicas, sin menoscabo de que dichas operaciones puedan ser realizadas por

1 Las operaciones entre diversos productos financieros de un mismo cliente, en la misma institución financiera, no serán sujetas del alcance de estas Guías.

2 Véase la 2a., fracción XXXVII Bis, de las Reglas del SPEI, contenidas en la Circular 14/2017 y sus modificaciones.

personas distintas a las antes mencionadas. Lo anterior, sin importar las relaciones contractuales que la institución financiera pudiera tener con terceros que ofrezcan dichas aplicaciones o programas informáticos.

## III. Definiciones

Para la debida aplicación e interpretación de las presentes Guías, cuando se haga referencia, en singular o plural, a los conceptos que a continuación se citan, se entenderá su respectivo significado al tenor siguiente y a lo establecido en la Regla 2a., de la Circular 14/2017, y al Artículo 2°, de la Circular 3/2012:

- **_<u>Aplicación</u>_** _<u>.</u>_ Al conjunto de instrucciones lógicas codificadas en un lenguaje de programación capaz de realizar operaciones específicas ejecutado en dispositivos móviles con sistemas operativos tales como _Android_ , _iOS_ o _HarmonyOS_ .

- **_<u>Elemento Interactivo</u>_** _<u>.</u>_ Componente de una Interfaz de Usuario que recibe información del usuario y genera un resultado en función de la información proporcionada. Los elementos interactivos pueden modificar, mostrar o consultar contenidos, detonar un proceso, entre otras acciones.

- **_<u>Entidad</u>_** . A cualquiera de los sujetos a que refiere la sección II, incisos c) y d), del presente documento.

- **_<u>Interfaz de Usuario.</u>_** Conjunto de elementos visuales, y de comunicación que permiten al usuario interactuar con una Aplicación.

## IV. Principios para la definición de la experiencia de uso de transferencias electrónicas

**Como se mencionó en las secciones anteriores, este documento tiene el objetivo de simplificar y estandarizar el flujo de instrucción de transferencias**[**3**] **en las Aplicaciones a través de las cuáles se ofrezca a personas físicas el servicio de envío de transferencias desde cuentas de depósito o cuentas de fondo de pago electrónico.** Para ello, se definieron tres principios en el desarrollo de la experiencia de uso de transferencias electrónicas: usabilidad, comunicación y estandarización.

**La usabilidad**[**4**] **se centra en los aspectos de facilidad y eficiencia que deben existir en el proceso de instrucción de transferencias.** La incorporación de este elemento genera procesos sencillos, que reducen la complejidad en el envío de transferencias, al mismo tiempo que integran elementos de simplicidad en el primer uso y en los usos subsecuentes de la funcionalidad. El aspecto de eficiencia asegura la optimización del proceso sin comprometer la seguridad de las transferencias electrónicas.

**La comunicación se centra en el lenguaje y los mensajes que se tienen hacia los usuarios** . Un lenguaje sencillo con mensajes claros y homologados, permite un mayor acercamiento del servicio de envío de transferencias electrónicas al público en general, sin que esto implique un reto cognitivo o restrinja la participación en el esquema de personas que no cuenten con conocimientos técnicos. La instrumentación de este elemento simplifica el uso de los servicios de transferencias para la población en general.

**La estandarización busca uniformidad en el flujo operativo de una transferencia, sin importar el caso de negocio o tipo de transacción que el usuario desea realizar.** Un proceso estandarizado genera confianza en el usuario, sin necesidad de que este se adapte a la experiencia de cada aplicación para el envío de transferencias que utilice.

La instrumentación de estos principios es la siguiente:

3 Cabe destacar que estos principios no eximen del cumplimiento a la diversa normatividad aplicable a las Entidades, ni habilita la operación de servicios que no se encuentran en el catálogo de productos de la Entidad que corresponda.

4 Usabilidad es un término comúnmente utilizado en el ámbito de la experiencia de usuario y diseño de aplicaciones e interfaces.

### A. Usabilidad

**El cliente de las Entidades interactúa un máximo de cuatro etapas para enviar una transferencia** . Estas etapas incluyen: la autenticación del usuario, el ingreso de la información de la transferencia, la verificación de la información, y la notificación del estado de la transferencia.

**Cabe destacar que lo anterior no restringe a que en caso de que las Entidades deban instrumentar procesos adicionales para realizar el envío de la transferencia, en cumplimiento de la normatividad aplicable**[**5**] **, el usuario sea dirigido al apartado correspondiente que permita atender y solventar dicho elemento.** En este sentido, las Entidades deberán habilitar la posibilidad de que el usuario continúe el flujo de la transferencia desde el punto en que se interrumpió el proceso.

**Las Aplicaciones deben mostrar un “atajo” que permita iniciar el proceso de instrucción de transferencia en la pantalla de inicio de sesión, así como en la pantalla principal de las Aplicaciones**[**6**] . El “atajo” deberá ubicarse consistentemente en la misma ubicación de todas las pantallas en las que aparezca, con el propósito de facilitar la localización de la opción.

### B. Comunicación

**La información que se presenta en las Interfaces de Usuario debe ser directa, comprensible y libre de ambigüedades.** Es deseable que las Entidades empleen una terminología uniforme, evitando así variaciones que puedan generar confusión en el usuario. Se precisa que los términos utilizados en el presente documento se encuentran alineados con los usados en la normatividad. Sin perjuicio de ello, las Entidades podrán utilizar los términos que estimen pertinentes, siempre que dichos términos mantengan el sentido y no alteren su propósito o interpretación general.

> 5 Ejemplos de estos procesos adicionales son los límites transaccionales previamente definidos por los usuarios, enrolamientos o consentimientos requeridos.

> 6 Esta pantalla normalmente corresponde a la Interfaz de Usuario que se muestra después de que ocurre el inicio de sesión.

**Utilizar un lenguaje cotidiano y accesible favorece el entendimiento del flujo de transferencias.** Debe fomentarse el uso de frases cortas y estructuras simples que faciliten la lectura rápida.

**Los íconos asociados a los Elementos Interactivos deben ser fácilmente ubicables y mantener dimensiones que faciliten a los usuarios su selección.** Un tamaño adecuado de los Elementos Interactivos, además de permitir la selección con mayor facilidad, refuerza la percepción sobre la simplicidad de uso.

**Podrá existir diferenciación en la experiencia de usuario para aquellos casos que, por el cumplimiento a las disposiciones aplicables, se deba realizar el registro de la cuenta o una verificación de la transacción** . Estas situaciones deben hacerse del conocimiento del usuario de forma que no perciba una desviación en el proceso normal para instruir transferencias.

- **C. Estandarización**

**La familiaridad en el flujo operativo de una transferencia es clave para facilitar la interacción del usuario con la Interfaz, reduciendo el esfuerzo mental requerido para realizar una transferencia, con ello, favoreciendo el procesamiento exitoso de las transferencias en distintas Aplicaciones.** Derivado de lo anterior, el usuario no debe percibir experiencias de uso de transferencias distintas si se trata de una transferencia de dos clientes de la misma institución (intra institución), o si se trata de una transferencia entre clientes de instituciones distintas (inter institución), por lo que deben mostrarse los mismos campos a completar tratándose de cualquiera de estos tipos de transferencias. Un proceso simple y homologado favorece la comprensión del flujo de la transferencia; la presencia de pantallas innecesarias, múltiples posibilidades para ejecutar el mismo proceso o un exceso de información pueden dificultar la instrucción de una transferencia.

## V. Requerimientos mínimos en la experiencia de usuarios de transferencias

**Los principios buscan impulsar un flujo operativo fácilmente identificable y homogéneo en el procesamiento de las transferencias electrónicas** . **La implementación de los principios se debe reflejar en el flujo de iniciación de transferencias que comprenderá desde el acceso a los servicios en las Aplicaciones, hasta la notificación del estado de la operación** .  El procesamiento de una transferencia en una Interfaz de Usuario deberá realizarse en una serie de cuatro etapas predefinidas, sin importar si se trata de una transferencia inter o intra institución.

### A. Primera etapa: inicio

Las Entidades deben habilitar un Elemento Interactivo que detone el proceso de instrucción de transferencia, de fácil acceso y visualización, considerando los siguientes escenarios:

**Figura 1. Primera etapa**

Si se tiene una pantalla de inicio de sesión en la Aplicación que el cliente debe accionar para realizar su inicio de operaciones:

1. En la pantalla de inicio de sesión de la Interfaz de Usuario, debe mostrarse un Elemento Interactivo que detone el proceso de instrucción de transferencia.

2. El Elemento Interactivo debe identificarse con el texto “ **Transferencias** ” y, en su caso, el logo que se defina como imagen de los servicios de transferencias.

3. En la pantalla de inicio el Elemento Interactivo debe detonar el proceso de inicio de sesión, previo a redirigir a la siguiente etapa sobre ingreso de información de la transferencia.

Si el inicio de sesión se realiza de manera automática al abrir la Aplicación:

4. En la pantalla principal de la Interfaz del Usuario, debe mostrarse un Elemento Interactivo que detone el proceso de instrucción de transferencia.

5. El Elemento Interactivo debe identificarse con el texto “ **Transferencias** ” y, en su caso, el logo que se defina como imagen de los servicios de transferencias.

- Información de acceso público. Página **9** de **52**

En adición a lo anterior, las Entidades pueden incluir los Elementos Interactivos que desencadenen la instrucción de la transferencia en los apartados o vistas que estimen convenientes.

### B. Segunda etapa:  ingreso de información

La segunda etapa está diseñada para que el usuario ingrese la información de sus transferencias en tres momentos: 1) información del ordenante; 2) información del beneficiario y, 3) información de la transferencia. Las Entidades deberán mantener el orden de los rubros y de los campos, conforme a lo que se indica en la presente sección y en la sección VI de estas Guías, con excepción de aquellos flujos que inician con la lectura de un QR o desde una notificación. A continuación, se detallan los requisitos mínimos que deben cubrirse en cada momento.

#### Momento 1: información del ordenante

1. La Interfaz del Usuario debe mostrar la cuenta desde la cual se tomarán los recursos para realizar el envío de la transferencia. En el supuesto de que el usuario disponga de más de una cuenta abierta en la Entidad desde la cual pueda enviar recursos, y no haya elegido alguna como predeterminada o favorita, la Interfaz de Usuario debe permitir al usuario seleccionar la cuenta a la que se cargarán los recursos.

2. La Interfaz del Usuario podrá mostrar el saldo del ordenante.

#### Momento 2: información del beneficiario

3. La Interfaz de Usuario debe permitir la captura de la información del beneficiario a través de los siguientes mecanismos:

   - Ingreso de cualquiera de los datos de identificación de la cuenta beneficiaria: CLABE, dígitos de la tarjeta, número de celular o número de cuenta (para operaciones intra institución);

   - Selección de información de contactos del usuario del teléfono o de cuentas registradas, y

   - Acceso a la cámara que permita la lectura de códigos QR.

**Figura 2. Segunda etapa**

4. La Interfaz de Usuario debe mostrar la Entidad Participante en el SPEI asociada a los datos de identificación de la cuenta beneficiaria, de conformidad con lo siguiente:

   - a. Cuando se use una CLABE, la Entidad debe mostrar el nombre del Participante Receptor asociado a dicha CLABE, sin solicitar al usuario que ingrese esta información. En el caso de que la cuenta beneficiaria corresponda a un Participante Indirecto, este campo mostrará el nombre del Participante en el SPEI que ofrece los Servicios de Participación Indirecta asociados a dicha CLABE.

   - b. Para el resto de los identificadores de cuenta, en caso que la Entidad tenga información que le permita identificar al Participante Receptor, debe mostrarla al usuario. No obstante, el usuario debe estar en posibilidad de modificar este campo.

   - c. Tratándose de operaciones donde el identificador de la cuenta sea un número de celular donde las Entidades obtengan del Administrador el dato del Participante Receptor, las Entidades no deben permitir al usuario modificar dicho campo.

#### Momento 3: información de la transferencia

5. La Interfaz de Usuario debe permitir el ingreso del monto, concepto y referencia numérica, excepto en los casos en los que dicha información esté prellenada por tratarse de una operación con un mensaje de cobro que incluya estos datos.

6. La Interfaz de Usuario debe habilitar un Elemento Interactivo para que el usuario pueda confirmar la información provista y continuar al siguiente paso.

#### Otras especificaciones:

La Interfaz de Usuario debe permitir las acciones de “copiar y pegar” los datos directamente en el campo de identificación de la cuenta.

La Interfaz de Usuario puede desplegar en la pantalla ejemplos visibles o guías visuales para el llenado de los campos, que ayuden al usuario a entender los datos que debe ingresar.

Las Entidades deberán informar a sus clientes sobre validaciones no exitosas de aspectos relacionados con: la disponibilidad de saldo, validaciones del número de teléfono en Dimo, así como solicitar el registro previo de las cuentas, cuando aplique.

### C. Tercera etapa: consistencia e integridad

1. La Interfaz de Usuario deberá mostrar los datos de la operación para que el usuario verifique la operación. Al menos deberá mostrar los siguientes:

   - Monto

   - Nombre del beneficiario (puede o no estar enmascarado)

   - Cuenta del beneficiario

   - Participante Receptor

   - Cuenta origen de los recursos (enmascarada o mostrando los últimos dígitos)

2. La Interfaz de Usuario debe adicionar un Elemento Interactivo mediante el cual el usuario acepte el envío de la transferencia. Con esa confirmación, la Entidad puede proceder con los procesos de autorización y autenticación que correspondan.

De requerirlo, la Entidad puede incluir procesos de verificación y confirmación de identidad adicionales que permitan realizar la instrucción de transferencias conforme al marco normativo que corresponda. Así como realizar las validaciones sobre aspectos relacionados con: límites transaccionales, comprobaciones de formato, seguridad, comprobaciones regulatorias aplicables y cualquier otro.

**Figura 3. Tercera etapa**

### D. Cuarta etapa: notificación

1. La Interfaz de Usuario debe mostrar los siguientes datos:

   - Estado de la operación (enviado, rechazado, en revisión, entre otros)

   - Monto

   - Concepto del pago (cuando aplique)

   - Referencia numérica (cuando aplique)

   - Los datos del beneficiario: nombre enmascarado, identificador de cuenta, institución en la que se encuentra la cuenta del beneficiario

2. Tratándose de operaciones inter institución, se debe mostrar:

   - Clave de rastreo

   - Vínculo para la descarga del comprobante electrónico de pagos (CEP)

3. Tratándose de operaciones intra institución, se debe mostrar:

   - Folio o número de autorización

**Figura 4. Cuarta etapa**

### E. Misceláneos

1. Las Entidades pueden adicionar otros Elementos Interactivos que le permitan al usuario una mejor navegación entre las etapas, como lo son indicadores para regresar a la pantalla anterior o compartir la información de la operación, por mencionar algunos.

2. La Entidades pueden establecer, dentro de las diversas secciones de su Aplicación, tantos Elementos Interactivos adicionales que inicien el proceso de transferencia como consideren, siempre y cuando una vez que estos sean detonados, se mantenga la misma ruta definida para el flujo de instrucción de una transferencia. Es decir, sin generar pasos o fricciones adicionales al usuario.

#### Respecto a los íconos asociados a un Elemento Interactivo:

3. Deben tener un tamaño adecuado para ser seleccionados de manera precisa y destacar sobre otros íconos o botones.

4. Deben estar localizados en zonas de la Aplicación de fácil acceso y ubicación.

#### Respecto a los elementos de lenguaje y comunicación:

5. Pueden utilizarse los términos establecidos en las imágenes ilustrativas de la sección VI del documento o similares.

6. Los mensajes de error, rechazo y cancelación deben ser precisos y claros, de forma que notifiquen claramente al usuario de la situación que ocurrió.

## VI. Flujo de instrucción de transferencia electrónica

**El flujo básico que debe seguir la instrucción de transferencias electrónicas comprende cuatro etapas principales** : el inicio, el ingreso de la información, la consistencia e integridad de la operación y la notificación del estado de la transferencia.

**No obstante, existen diferentes casos de uso que pueden requerir que la Interfaz de Usuario se adapte a flujos de transacción específicos.** En las siguientes subsecciones se detallan los flujos que se deben implementar para los casos de uso identificados. Cabe señalar que el usuario no requiere saber el tipo de transferencia o el caso de uso que está realizando, esa identificación debe ser ejecutada por la Entidad mediante la implementación de los esquemas detallados en el presente documento y la información proporcionada por el usuario.

### A. Transferencia electrónica básica

Una vez iniciada la solicitud de transferencia, se facilitará al cliente el ingreso de la información necesaria para su trámite. En una etapa subsiguiente, tanto el cliente como la Entidad deben verificar la consistencia e integridad de los datos operativos. El proceso concluye con la notificación formal del estatus de la operación.

**Figura 5. Flujo de usuario de una transferencia electrónica básica**

### a. Inicio

Las Entidades deben facilitar la iniciación de transferencias tanto en la pantalla de inicio de sesión, como en la pantalla principal de la Aplicación. Cuando la solicitud se origine en la pantalla de inicio de sesión, será necesario completar dicho proceso bajo los criterios de seguridad definidos por la Entidad para sus servicios.

Las Entidades deben habilitar un Elemento Interactivo en la pantalla de inicio de sesión y en la pantalla principal para activar el flujo de transferencias, mismo que deberá identificarse con el texto “ **Transferencias** ” y, en su caso, el logo que se defina como imagen de los servicios de transferencias. La posición del ícono debe permanecer visible en la pantalla sin necesidad de desplazamiento o búsqueda dentro de menús por parte del usuario.

**Figura 6. Imágenes ilustrativas del acceso directo “Transferencias” en la pantalla de inicio y pantalla principal.**

### b. Ingreso de información

La fase de entrada de datos de la transferencia consiste en la recopilación, en orden sucesivo, de la información del ordenante, del beneficiario y de la operación misma. Se sugiere emplear tres pantallas para realizar esta captura, respetando la secuencia indicada.

#### 1) Información del ordenante

Si el usuario tiene registradas varias cuentas dentro de la Aplicación, se le debe permitir seleccionar aquella de la cual se cargarán los recursos, entre aquellas cuentas que le permitan el envío de transferencias. En caso de contar con una sola cuenta para el envío de transferencias o una cuenta configurada como predeterminada o favorita, esta se deberá establecer automáticamente como la cuenta origen de la transferencia sin intervención adicional del usuario.

#### 2) Información del beneficiario

Posterior al ingreso de los datos del ordenante, se deben mostrar los campos para el llenado o selección de la cuenta del beneficiario. Para ello, se deben mostrar las cuentas beneficiarias predefinidas (favoritas, recientes, frecuentes o guardadas) y mostrar los campos para la captura de información del receptor:

#### a) <u>Lista de contactos telefónicos</u>

Se debe incluir un ícono que refiera a la opción de desplegar la libreta de contactos del usuario. Una vez desplegada, el usuario podrá seleccionar, desde la libreta, el contacto al que busca enviarle la transferencia.

#### b) <u>Cuentas registradas</u>

**Figura 7. Flujo de usuario de ingreso de información.**

Se debe incluir un ícono que permita desplegar la lista de cuentas registradas previamente por el usuario en su Aplicación. Una vez desplegada, el usuario debe seleccionar la cuenta a la que busca enviarle la transferencia.

#### c) <u>Captura de identificador de cuenta</u>

Se debe facilitar la captura de la información de manera manual, mediante las opciones copiar o pegar la información de los identificadores de cuenta: CLABE, número de tarjeta número de teléfono o número de cuenta (para transferencias intra institución).

#### d) <u>Lectura de QR</u>

Se debe facilitar la lectura de QR con la información de cuenta.

Las instituciones están obligadas a gestionar el alta de nuevas cuentas sujetándose a las disposiciones aplicables.

#### 3) Información de la transferencia

Durante el ingreso de datos, se debe facilitar la captura del monto de la transferencia con la visualización del saldo disponible. Se debe permitir al usuario el ingreso del concepto del pago, así como la referencia numérica; no obstante, la Entidad podrá completar dicha información en caso de que el usuario no hubiera ingresado dato alguno. Durante el ingreso de los datos podrá realizarse la validación del monto, formatos de los campos concepto del pago y referencia numérica.

Las Entidades deberán informar a sus clientes sobre validaciones no exitosas de aspectos relacionados con: la disponibilidad de fondos, falta de correspondencia del número de teléfono con alguna cuenta, así como solicitar el registro de las cuentas, cuando aplique.

Con fines ilustrativos, la Figura 8 muestra ejemplos de las vistas de usuario asociadas a la etapa de entrada de datos. Este flujo incluye la captura secuencial de la información del ordenante, el beneficiario y los atributos operativos de la transferencia.

**Figura 8. Imágenes ilustrativas del flujo de instrucción de una transferencia electrónica básica en la etapa 2.**

### c. Consistencia e integridad

La fase sobre consistencia e integridad tiene por objeto que el usuario revise los datos de la transferencia y que la Entidad valide las características de la operación, procediendo, en su caso, a la autorización del usuario. Las Entidades podrán emplear dos pantallas para este fin, sujetándose al orden de la secuencia indicada más adelante.

#### 1) Revisión de usuario

Posterior al ingreso de la información de la transferencia, se mostrará un resumen de la operación con el fin de que el usuario valide la información. Si se requieren modificaciones, éstas deberán poder realizarse en ese momento, sin la necesidad de reiniciar el proceso de instrucción de la transferencia. Se deben desplegar los siguientes campos en la Interfaz del Usuario:

- Monto. Un campo con el texto “Monto” donde se despliegue el monto de la operación.

- Nombre del beneficiario. El nombre podrá mostrarse enmascarado. Cuando el usuario haya ingresado este dato manualmente, podrá señalarse que el nombre no es validado por la Entidad. La Interfaz del Usuario debe incluir este campo con el texto “Beneficiario”.

- Cuenta. Un campo con el texto “Cuenta” donde se incluya el Identificador de la cuenta beneficiaria.

- Institución. Un campo con el texto “Institución” donde se incluya el nombre de la Entidad beneficiaria.

- Referencia. Un campo con el texto “Referencia” donde se incluya la referencia numérica ingresada por el usuario.

- Concepto. Un campo con el texto “Concepto” donde se incluya el concepto de la transferencia ingresado por el usuario.

**Figura 9. Flujo de usuario de consistencia e integridad**

- Desde. Un campo con el texto “Desde” donde se incluya el nombre de la Entidad desde la cual el usuario envía la operación.

Finalmente, se deberá habilitar un ícono que permita al usuario continuar con la operación y otro para cancelar la operación en caso de que el usuario no desee continuar.

- **2) Validación del participante**

Posterior a la revisión del usuario, la Entidad realizará las comprobaciones de formato, seguridad y cualesquiera comprobaciones regulatorias aplicables. Si fuera necesario realizar algún paso adicional relacionado con el cumplimiento de las disposiciones aplicables, o completar información, se habilitará el proceso correspondiente para atender dicho requerimiento.

#### 3) Autorización del usuario

Posterior a la validación de la información por el usuario y a las comprobaciones de la Entidad, el cliente procederá, en su caso, a autorizar la transferencia utilizando el factor de autenticación designado.

Con fines ilustrativos, la Figura 10 muestra ejemplos de las vistas de usuario asociadas a la etapa sobre consistencia e integridad. Este flujo incluye la información a mostrar.

**Figura 10. Imágenes ilustrativas del flujo de instrucción de una transferencia electrónica básica en la etapa 3.**

### d. Notificación

La fase de notificación consiste en mostrar al usuario los detalles de su operación, así como su estado (enviado, rechazado, en revisión, entre otros) y en operaciones inter instituciones el vínculo para la descarga del Comprobante Electrónico de Pagos (CEP).

La Interfaz del Usuario debe mostrar un texto que informe al usuario del estado de la operación. Los textos sugeridos son los siguientes:

- Si el envío de la transferencia se realizó de manera correcta, el texto puede ser “¡Transferencia enviada!” o alguno similar.

- Si la operación se está siendo sujeta a validaciones adicionales, el texto puede ser “Transferencia en validación” o alguno similar. Se sugiere indicar la causa de la validación y el tiempo máximo en el que se concretará la verificación de la operación.

- Si la operación se rechazó, el texto puede ser “Transferencia rechazada” o alguno similar.

Solo en caso que la transferencia haya sido enviada, se deben mostrar los siguientes datos (con excepción del campo folio, que debe mostrarse en todos los escenarios del estado de la operación):

- Estampa de tiempo. Se debe mostrar la fecha y hora del envío de la transferencia.

- Monto. La Interfaz del Usuario debe incluir un campo con el texto “Monto”. En seguida, se debe mostrar la cifra que ingresó el usuario en la orden de transferencia. Este campo debe ser predominante visualmente respecto del resto de los campos.

- Concepto del pago. La Interfaz del Usuario debe incluir un campo con el texto “Concepto del pago”. En seguida, se debe mostrar el concepto del pago que se incluyó en la orden de transferencia.

**Figura 11. Imágenes ilustrativas del flujo de instrucción de una transferencia electrónica básica en la etapa 4.**

- Información del emisor. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”. En seguida se debe mostrar el número de la cuenta origen de forma enmascarada, dejando visibles sólo los últimos 4 dígitos.

- Información del beneficiario. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”, un campo con el texto “Participante” y un campo con el campo “Beneficiario”. En seguida se debe mostrar la siguiente información: el identificador de la cuenta CLABE, tarjeta, número telefónico o número de cuenta (para transferencias intra institución), dejando visibles sólo los últimos 4 dígitos, junto al texto “CLABE”, “Número de tarjeta”, “Número telefónico” o “Número de cuenta”. Se debe incluir el nombre corto del participante receptor junto al campo “Participante”. Para el caso del campo “Beneficiario”: i) en caso que se cuente con el nombre del beneficiario, este campo debe mostrarlo junto al texto “Beneficiario” o ii) si no se cuenta con la información del beneficiario, este campo debe indicar el texto “No disponible”, junto al texto ““Beneficiario”.

- Referencia numérica. La Interfaz del Usuario debe incluir un campo con el texto “Referencia numérica”. En seguida, se debe mostrar la referencia numérica que ingresó el usuario en la orden de transferencia.

- Clave de rastreo. Para operaciones inter institución, la Interfaz del Usuario debe incluir un campo con el texto “Clave de rastreo”. En seguida, se debe mostrar la clave de rastreo que la Entidad emisora asigne a la orden de transferencia.

- Folio. La Interfaz del Usuario debe incluir un campo con el texto “Folio”. En seguida, se debe mostrar el folio o número de autorización de la transferencia. Este campo debe mostrarse en todos los escenarios del estado de operación.

- Vínculo al CEP. Para operaciones inter institución, la Interfaz del Usuario deberá incluir un vínculo para la descarga del comprobante electrónico de pagos (CEP).

Adicionalmente, las Entidades deben facilitar el intercambio de un comprobante que detalle las condiciones específicas en que se llevó a cabo la autorización de la transferencia.

### B. Transferencia electrónica utilizando sólo el número de teléfono (Dimo)

Este esquema considera que el usuario ingresa el número de teléfono celular como identificador de la cuenta beneficiaria, considerando su ingreso manual o de manera automática mediante la lectura de un código QR que contenga como identificador de la cuenta beneficiaria el número de teléfono celular.

**Figura 12. Flujo de usuario de una transferencia utilizando sólo el número de teléfono (Dimo).**

### a. Inicio

Las Entidades deben facilitar la iniciación de transferencias tanto en la pantalla de inicio de sesión como en la pantalla principal de la Aplicación. Cuando la solicitud se origine en la pantalla de inicio de sesión, será necesario completar dicho proceso bajo los criterios de seguridad definidos por la Entidad.

Las Entidades deben incluir un Elemento Interactivo en la pantalla de inicio de sesión y en la pantalla principal para activar el flujo de transferencias, mismo que deberá identificarse con el texto “ **Transferencia** s” y, en su caso, el logo que se defina como imagen de los servicios de transferencias. El Elemento Interactivo debe permanecer visible en la pantalla sin necesidad de desplazamiento en la pantalla o dentro de menús en los que deba buscar el usuario.

**Figura 13. Imágenes ilustrativas del inicio de una transferencia utilizando número de celular (Dimo)**

### b. Ingreso de información

La fase de ingreso de datos de la transferencia consiste en la recopilación, en orden sucesivo, de la información del ordenante, del beneficiario y de la operación misma. Se sugiere emplear hasta cuatro pantallas para realizar esta captura, respetando siempre la secuencia indicada.

#### 1) Información del ordenante

Si el usuario tiene registradas varias cuentas dentro de la Aplicación, se le debe permitir seleccionar aquella de la cual se tomarán los recursos, entre aquellas cuentas que le permitan el envío de transferencias. En caso de contar con una sola cuenta para el envío de transferencias o una cuenta configurada como predeterminada o favorita, ésta se deberá establecer automáticamente como la cuenta origen de la transferencia sin intervención adicional del usuario.

#### 2) Información del beneficiario

Posterior al ingreso de la información del ordenante, se deben mostrar las cuentas beneficiarias predefinidas (favoritas, recientes, frecuentes o guardadas). Para cuentas no registradas, se debe permitir la captura manual del número de teléfono celular como identificador de la cuenta beneficiaria, o bien, su obtención automática mediante la lectura de un código QR que contenga como identificador el número de teléfono celular.

En este flujo el identificador de la cuenta beneficiaria corresponde al número de teléfono. Bajo este supuesto la Entidad debe realizar siempre una consulta a los servicios del Administrador, incluso si la cuenta se encuentra previamente registrada por el cliente emisor.  En caso de que el resultado de la consulta señale que el número de teléfono celular se encuentra registrado en la base de datos

**Figura 14. Flujo de usuario de ingreso de información.**

administrada por Banco de México, la Entidad deberá desplegar la información obtenida según lo señalado en la 12a. Bis de la Circular 14/2017. No obstante, si no se cuenta con la información del beneficiario, el flujo debe terminar.

Posteriormente, la Entidad deberá permitir al usuario modificar el número de teléfono celular, en caso de que al revisar el nombre enmascarado identifique un error y requiera modificarlo. En este caso, la Entidad debe repetir el procedimiento de consulta descrito en el párrafo anterior.

Las Entidades están obligadas a gestionar el alta de nuevas cuentas beneficiarias sujetándose a los términos y condiciones fijados por las distintas disposiciones y ordenamientos que les sean aplicables.

- **3) Información de la transferencia**

Durante el ingreso de datos, se debe facilitar la captura del monto de la transferencia con la visualización del saldo disponible. Se debe permitir al usuario el ingreso del concepto del pago, así como la referencia numérica; no obstante, la Entidad podrá completar dicha información de manera automática en caso de que el usuario no ingrese este dato. Durante el ingreso de los datos podrá realizarse la validación del monto, formatos y los campos concepto del pago y referencia numérica.

Con fines ilustrativos, la Figura 15 muestra ejemplos de las vistas de usuario asociadas a la etapa de ingreso de la información. Este flujo incluye la captura secuencial de la información del ordenante, el beneficiario y el resto de los datos de la transferencia.

**Figura 15. Imágenes ilustrativas del flujo de instrucción de una transferencia electrónica utilizando sólo el número de teléfono (Dimo) en la etapa 2.**

### c. Consistencia e integridad

La fase sobre consistencia e integridad tiene por objeto que el usuario verifique los datos de la transferencia y que la Entidad valide la operación, procediendo, en su caso, a la autorización del usuario. Se recomienda a la Entidad emplear hasta dos pantallas en esta etapa, sujetándose a la secuencia indicada más adelante.

- **1) Revisión del usuario**

Posterior al ingreso de la información de la transferencia, se debe mostrar un resumen de la operación para que el usuario valide la información. Si se requieren modificaciones, éstas deben poder realizarse directamente, sin necesidad de reiniciar el proceso de instrucción de la transferencia. Se deben desplegar los siguientes campos en la Interfaz del Usuario:

- Monto. Un campo con el texto “Monto” donde se despliegue el monto de la operación.

- Nombre del beneficiario. El nombre deberá mostrarse enmascarado de acuerdo a la información que haya recibido de la consulta realizada a los servicios del Banco de México. La Interfaz del Usuario debe incluir lo anterior en un campo con el texto “Beneficiario”. Este campo no podrá ser editado por el cliente.

- Cuenta. Un campo con el texto “Cuenta” donde se incluya el Identificador de la cuenta beneficiaria. Este campo no podrá ser editado por el cliente.

- Institución. Un campo con el texto “Institución” donde se incluya el nombre de la Entidad beneficiaria que haya recibido de la consulta realizada a los servicios del Banco de México. Este campo no podrá ser editado por el cliente.

- Referencia. Un campo con el texto “Referencia” donde se incluya la referencia numérica ingresada por el usuario.

- Concepto. Un campo con el texto “Concepto” donde se incluya el concepto de la transferencia ingresado por el usuario.

- Desde. Un campo con el texto “Desde” donde se incluya el nombre de la Entidad desde la cual se envía la operación.

**Figura 16.  Flujo de usuario de consistencia e integridad**

Finalmente, se deberá habilitar un ícono que permita al usuario continuar con la operación y otro para cancelar la operación en caso de que el usuario no desee continuar.

- **2) Validaciones de la Entidad**

Posterior a la revisión del usuario, la Entidad realizará las comprobaciones de formato, seguridad y cualesquiera comprobaciones regulatorias aplicables. Si fuera necesario realizar algún paso adicional relacionado con el cumplimiento de las disposiciones aplicables o completar información, se habilitará el proceso correspondiente para atender dicho requerimiento.

#### 3) Autorización del usuario

Posterior a la validación de la información por el usuario y a las comprobaciones pertinentes de la Entidad, el cliente procederá, en su caso, a autorizar la transferencia utilizando el factor de autenticación designado.

Con fines ilustrativos, la Figura 17 muestra ejemplos de las vistas de usuario asociadas a la etapa sobre consistencia e integridad. Este flujo incluye la información a mostrar.

**Figura 17. Imágenes ilustrativas del flujo de instrucción de una transferencia electrónica utilizando sólo número de teléfono (Dimo) en la etapa 3.**

### d. Notificación

La fase de notificación consiste en mostrar al usuario los detalles de su operación, así como su estado (enviado, rechazado, en revisión) y en operaciones entre instituciones el vínculo para la descarga del Comprobante Electrónico de Pago (CEP), en una sola pantalla.

La Interfaz del Usuario debe mostrar un texto que informe al usuario del estado de la operación. Los textos sugeridos son los siguientes:

- Si el envío de la transferencia se realizó de manera correcta, el texto puede ser “¡Transferencia enviada!” o alguno similar.

- Si la operación está siendo sujeta a validaciones adicionales, el texto puede ser “Transferencia en validación” o alguno similar. Se sugiere indicar la causa de la validación y el tiempo en el que se concretará la verificación de la operación.

- Si la operación se rechazó, el texto puede ser “Transferencia rechazada” o alguno similar.

Solo en caso que la transferencia haya sido enviada, se deben mostrar los siguientes datos (con excepción del campo folio, que debe mostrarse en todos los escenarios del estado de la operación):

- Estampa de tiempo. Se debe mostrar la fecha y hora del envío de la transferencia.

- Monto. La Interfaz del Usuario debe incluir un campo con el texto “Monto”. En seguida, se debe mostrar la cifra ingresó el usuario en la orden de transferencia. Este campo debe ser predominante visualmente respecto del resto de los campos.

- Concepto del pago. La Interfaz del Usuario debe incluir un campo con el texto “Concepto del pago”. En seguida, se debe mostrar el concepto del pago que se incluyó en la orden de transferencia.

**Figura 18. Imágenes ilustrativas de la notificación en Dimo.**

- Información del emisor. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”. En seguida se debe mostrar el número de la cuenta origen de forma enmascarada, dejando visibles sólo los últimos 4 dígitos.

- Información del beneficiario. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”, un campo con el texto “Participante” y un campo con el campo “Beneficiario”. En seguida se debe mostrar la siguiente información: la CLABE de la cuenta receptora enmascarada, dejando visibles sólo los últimos 4 dígitos, junto al texto “Cuenta”. Se debe incluir el nombre corto del participante receptor junto al campo “Participante”. Para el caso del campo “Beneficiario”, se debe mostrar el nombre enmascarado que haya recibido de la consulta realizada a los servicios del Banco de México; este campo debe mostrarlo junto al texto “Beneficiario”.

- Referencia numérica. La Interfaz del Usuario debe incluir un campo con el texto “Referencia numérica”. En seguida, se debe mostrar la referencia numérica que ingresó el usuario en la orden de transferencia.

- Clave de rastreo. Para operaciones inter institución, la Interfaz del Usuario debe incluir un campo con el texto “Clave de rastreo”. En seguida, se debe mostrar la clave de rastreo que la Entidad emisora asigne a la orden de transferencia.

- Folio. La Interfaz del Usuario debe incluir un campo con el texto “Folio”. Enseguida, se debe mostrar el folio o número de autorización de la transferencia. Este campo debe mostrarse en todos los escenarios del estado de operación.

- Vínculo al CEP. Para operaciones inter institución, la Interfaz del Usuario deberá incluir un vínculo para la descarga del comprobante electrónico de pagos (CEP).

Adicionalmente, las Entidades deberán facilitar el intercambio de un comprobante que detalle las condiciones específicas en que se llevó a cabo la autorización de la transferencia.

### C. Transferencia electrónica por lectura o carga de QR (CoDi)

El esquema CoDi[7] considera el envío de una transferencia a partir de los datos obtenidos de un QR que contiene la cuenta beneficiaria y participante del SPEI del beneficiario; asimismo, puede incluir otra información como el monto, concepto de pago, así como una referencia numérica predefinida. Se mantienen las etapas de verificación de la consistencia e integridad de los datos. El proceso concluye con la notificación del estatus de la operación.

**Figura 19. Flujo de usuario de una transferencia electrónica por lectura o carga de QR (CoDi).**

### a. Inicio

Las Entidades deben facilitar la iniciación de transferencias tanto en la pantalla de inicio como en la pantalla principal de la Aplicación. Cuando la solicitud se origine en la pantalla de inicio de sesión, será necesario completar el inicio de sesión bajo los criterios de seguridad definidos por la Entidad.

7 El detalle del uso del esquema de Cobro Digital (CoDi) se encuentra descrito en el “Apéndice AD” del Manual de Operación del SPEI, que es parte de las normas internas del SPEI (Circular 14/2017).

Las Entidades deben incluir un ícono en la pantalla de inicio de sesión y en la pantalla principal para activar el flujo de transferencias, mismo que deberá identificarse con el texto “Transferencias” y, en su caso, el logo que se defina como imagen de los servicios de transferencias. El ícono debe permanecer visible en la pantalla sin necesidad de desplazamiento en la pantalla o búsqueda dentro de menús en los que deba buscar el usuario.

**Figura 20. Imágenes ilustrativas del inicio de una trasferencia mediante la lectura o carga de QR (CoDi).**

### b. Ingreso de información

La fase de ingreso de datos de la transferencia consiste en la recopilación, en orden sucesivo, de la información del ordenante, del beneficiario y de la operación misma. Se sugiere emplear hasta tres pantallas para realizar esta captura, respetando la secuencia indicada. Para casos en los que

se hace la lectura o carga de un QR, la información del beneficiario ya no debe ser completada por el usuario. El QR puede o no incluir el monto y/o concepto de la transferencia.

#### 1) Información del ordenante

Si el usuario tiene registradas varias cuentas dentro de la Aplicación, se le debe permitir seleccionar aquella de la cual se tomarán los recursos, entre aquellas cuentas que le permitan el envío de transferencias. En caso de contar con una sola cuenta para el envío de transferencias o una cuenta configurada como predeterminada o favorita, ésta se deberá establecer automáticamente como la cuenta origen de la transferencia sin intervención adicional del usuario.

#### 2) Información del beneficiario

Posterior al ingreso de los datos del ordenante, se deberá mostrar la información del beneficiario que fue obtenida de forma automática mediante la lectura o carga del código QR que contenga el identificador correspondiente (CLABE, tarjeta o teléfono). Por lo que no se requerirán esfuerzos por parte del cliente ordenante en esta sección ni se deberá permitir la edición de la información extraída del QR.

#### 3) Información de transferencia

Dependiendo de la información extraída de forma automática del código QR en cuestión, es que se solicitarán o no, acciones por parte del cliente ordenante para efecto de completar la información de la transferencia.

Cuando el código QR contenga la información referente al monto y concepto de la operación, ésta deberá ser desplegada al cliente, únicamente para su revisión mas no para su edición.

**Figura 21. Flujo de usuario del ingreso de información**

En caso de que el código QR no contenga información sobre el monto y/o concepto de la operación, se deberá facilitar la captura de la información correspondiente a dichos campos, para el monto se deberá permitir establecer la cantidad exacta de la transferencia con la visualización del saldo disponible. Durante el ingreso de los datos podrá realizarse la validación del monto, formatos y los campos concepto del pago y referencia numérica.

Con fines ilustrativos, la Figura 22 muestra ejemplos de las vistas de usuario asociadas a la etapa de entrada de datos. Este flujo incluye la captura secuencial de la información del ordenante, el beneficiario y los atributos operativos de la transferencia.

**Figura 22. Imágenes ilustrativas del ingreso de información en una transferencia por lectura o carga de QR.**

### c. Consistencia e integridad

La fase sobre consistencia e integridad tiene por objeto que el usuario revise los datos de la transferencia y que la Entidad valide las características de la operación, procediendo finalmente a la autorización por parte del usuario. Las Entidades podrán emplear hasta dos pantallas para este fin, sujetándose al orden de la secuencia indicada más adelante.

#### 1) Revisión del usuario

Posterior al ingreso de la información de la transferencia, se mostrará un resumen de la transacción con el fin de que el usuario valide la información proporcionada. Si se requieren modificaciones, éstas deberán poder realizarse directamente, sin necesidad de reiniciar el proceso de instrucción de la transferencia.

NOTA IMPORTANTE: Para las operaciones derivadas de la lectura o carga de un código QR, no se permite editar los datos del beneficiario que fueron extraídos automáticamente del referido QR. Asimismo, para la información asociada al concepto y monto de la transferencia, únicamente se deberá permitir su edición, cuando esta información no haya estado contenida en el código QR leído o cargado.

#### 2) Validación del participante

Posterior a la verificación del usuario, la Entidad realizará las comprobaciones de formato, seguridad y cualesquiera comprobaciones regulatorias aplicables. Si fuera necesario realizar algún paso

**Figura 23. Flujo de usuario del ingreso de información**

adicional o completar información, se habilitará el proceso correspondiente para atender dicho requerimiento sin interrupción del flujo principal.

#### 3) Autorización del usuario

Posterior a la validación de la información por el usuario y a las comprobaciones de la Entidad, el cliente procederá, en su caso, a autorizar la transferencia utilizando el factor de autenticación designado.

Con fines ilustrativos, la Figura 24 muestra ejemplos de las vistas de usuario asociadas a la etapa sobre consistencia e integridad. Este flujo incluye la información a mostrar.

**Figura 24. Imágenes ilustrativas del flujo de instrucción de una transferencia por lectura o carga de QR en la etapa 3.**

### d. Notificación

La fase de notificación consiste en mostrar al usuario los detalles de su operación, así como su estado (enviado, rechazado, en revisión) y en operaciones entre instituciones el vínculo para la descarga del comprobante electrónico de pagos (CEP), en una sola pantalla.

La Interfaz del Usuario debe mostrar un texto que informe al usuario del estado de la operación, los textos sugeridos son los siguientes:

- Si el envío de la transferencia se realizó de manera correcta, el texto podrá indicar “¡Transferencia enviada!” o alguno similar.

- Si la operación está siendo sujeta a validaciones adicionales, el texto podrá indicar “Transferencia en validación” o alguno similar. Se sugiere indicar la causa de la validación y el tiempo en el que se concretará la verificación de la operación.

- Si la operación se rechazó, el texto podrá indicar “Transferencia rechazada” o alguno similar. Se sugiere indicar la causa del rechazo de operación.

Solo en caso de que la transferencia haya sido enviada, la Interfaz de Usuario debe mostrar los siguientes datos (con excepción del campo folio, que debe mostrarse en todos los escenarios del estado de la operación):

- Estampa de tiempo. Se debe mostrar la fecha y hora del envío de la transferencia

- Monto. La Interfaz del Usuario debe incluir un campo con el texto “Monto”. Enseguida, se debe mostrar la cifra que se incluyó en la orden de transferencia. Este campo debe ser predominante visualmente respecto del resto de los campos.

- Concepto del pago. La Interfaz del Usuario debe incluir un campo con el texto “Concepto del pago”. Enseguida, se debe mostrar el concepto del pago que se incluyó en la orden de transferencia.

**Figura 25. Imágenes ilustrativas de la notificación en transferencias por lectura o carga de QR.**

- Información del emisor. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”. En seguida se debe mostrar la siguiente información: se debe incluir la cuenta emisora de los recursos de forma en mascarada, dejando visibles sólo los últimos 4 dígitos.

- Información del beneficiario. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”, un campo con el texto “Participante” y un campo con el campo “Beneficiario”. Enseguida se debe mostrar la siguiente información: se debe incluir el identificador de la cuenta que corresponda a la CLABE, tarjeta o número telefónico, dejando visibles sólo los últimos 4 dígitos, junto al texto “CLABE”, “Número de tarjeta”, “Número telefónico”. Se debe incluir el nombre corto del participante receptor junto al campo “Participante”. Para el caso del campo “Beneficiario”, se debe mostrar el nombre del beneficiario junto al texto “Beneficiario”.

- Referencia numérica. La Interfaz del Usuario debe incluir un campo con el texto “Referencia numérica”. Enseguida, se debe mostrar la referencia numérica que se incluyó en la orden de transferencia.

- Clave de rastreo. Para operaciones inter institución, incluir un campo con el texto “Clave de rastreo”. Enseguida, se debe mostrar la clave de rastreo que la Entidad Emisora asigne a la orden de transferencia.

- Folio CoDi. La Interfaz del Usuario debe incluir un campo con el texto “Folio CoDi”. Enseguida, se debe mostrar el folio o número de autorización que corresponda al envío de la transferencia. Este campo debe mostrarse en todos los escenarios del estado de operación. En este caso, ya que la operación deriva de un QR generado a través del esquema CoDi, este dato corresponderá al Folio CoDi.

- Vínculo al CEP. Para operaciones inter institución, la Interfaz del Usuario deberá incluir un vínculo para la descarga del Comprobante Electrónico de Pago (CEP).

Adicionalmente, las Entidades deberán facilitar el intercambio de un comprobante que detalle las condiciones específicas en que se llevó a cabo la autorización de la transferencia.

### D. Notificación _push_ solicitando un pago (CoDi)

La persona que enviará la transferencia recibe una notificación del esquema[8] en su dispositivo móvil que, una vez iniciada la sesión, despliega los datos de la transferencia. En una etapa subsiguiente, tanto el cliente como la Entidad deberán verificar la consistencia e integridad de los datos operativos. El proceso concluye con la notificación formal del estatus de la operación.

### a. Inicio

Al usuario le debe llegar la notificación _push_ que contiene el Mensaje de Cobro, la referida notificación debe incluir un mensaje claro en el que se informe que se está solicitando un pago y con la información del nombre del beneficiario, así como el monto exacto por el cual se está solicitando el pago en cuestión.

**Figura 26. Flujo de usuario de una transferencia por notificación push.**

8 El detalle del uso del esquema de Cobro Digital (CoDi) se encuentra descrito en el “Apéndice AD” del Manual de Operación del SPEI vigente, que es parte de la regulación del SPEI (circular 14/2017).

El usuario debe seleccionar dicha notificación que lo llevará a la aplicación de su institución financiera en la cual realizará el pago. El usuario deberá seleccionar el Elemento Interactivo de inicio de sesión para ingresar a su aplicación y poder autorizar el pago.

**Figura 27. Imágenes ilustrativas del inicio de una trasferencia mediante una notificación push.**

### b. Ingreso de información

La fase de entrada de datos de la transferencia consiste en la recopilación, en orden sucesivo, de la información del ordenante, del beneficiario y de la operación misma. Para este caso, en donde a través de una notificación _push_ se está solicitando un pago, no se requieren acciones de ingreso de información, toda vez que la información de la transferencia ya fue incluida en la _push_ .

#### 1) Información ordenante

Si el usuario tiene registradas varias cuentas dentro de la Aplicación, se le debe permitir seleccionar aquella de la cual se tomarán los recursos, entre aquellas cuentas que le permitan el envío de transferencias. En caso de contar con una sola cuenta para el envío de transferencias o una cuenta configurada como predeterminada o favorita, ésta se deberá establecer automáticamente como la cuenta origen de la transferencia sin intervención adicional del usuario.

#### 2) Información del beneficiario

Se debe mostrar la información del beneficiario obtenida de forma automática de la notificación _push_ ; por lo que no se debe requerir intervención del cliente ordenante en esta sección, ni se le deberá permitir la edición de la información mostrada.

#### 3) Información de la transferencia

**Figura 28. Flujo de usuario del ingreso de información**

Se debe mostrar al menos la siguiente información de la transferencia: monto, concepto del pago y referencia numérica, que fueron obtenidos de forma automática de la notificación _push_ ; por lo que no se debe requerir intervención del cliente ordenante en esta sección, ni se le debe permitir la edición de la información mostrada.

### c. Consistencia e integridad

La fase sobre consistencia e integridad tiene por objeto que el usuario verifique los datos de la transferencia y que la Entidad valide las características de la operación, procediendo, en su caso, a la autorización por parte del usuario. Las Entidades podrán emplear dos pantallas para este fin, sujetándose a la secuencia indicada más adelante.

#### 1) Revisión del usuario

Posterior al ingreso de la información de la transferencia, se mostrará un resumen de la operación para que el usuario valide la información. Si se requieren modificaciones, estas deben poder realizarse directamente, sin necesidad de reiniciar el proceso de instrucción de la transferencia.

Para las operaciones derivadas de la aceptación de una notificación _push_ , no se debe permitir editar los datos del beneficiario que fueron extraídos automáticamente. Asimismo, para la información asociada al concepto del pago y monto de la transferencia, únicamente se debe permitir su edición cuando esta información no esté contenida en la notificación _push_ .

#### 2) Validación del participante

Posterior a la verificación del usuario, la Entidad realizará las comprobaciones de formato, seguridad y cualesquiera comprobaciones regulatorias aplicables. Si fuera necesario realizar algún paso adicional relacionado con el cumplimiento de las disposiciones aplicables o completar información, se habilitará el proceso correspondiente para atender dicho requerimiento.

#### 3) Autorización del usuario

**Figura 29. Flujo de usuario sobre la consistencia e integridad**

Posterior a la validación de la información por el usuario y a las comprobaciones pertinentes por parte de la Entidad, el cliente procederá a autorizar la transferencia utilizando el factor de autenticación designado.

Con fines ilustrativos, la Figura 30 muestra ejemplos de las vistas de usuario asociadas a la etapa sobre consistencia e integridad. Este flujo incluye la información a mostrar.

**Figura 30. Imágenes ilustrativas del flujo de instrucción de una transferencia originada por notificación push en la etapa 3.**

### d. Notificación

La fase de notificación consiste en mostrar al usuario los detalles de su operación, así como su estado (enviado, rechazado, en revisión) y en operaciones entre instituciones el vínculo para la descarga del Comprobante Electrónico de Pago (CEP), en una sola pantalla.

La Interfaz del Usuario debe mostrar un texto que informe al usuario el estado de la operación, los textos sugeridos son los siguientes:

- Si el envío de la transferencia se realizó de manera correcta, el texto puede ser “¡Transferencia enviada!” o alguno similar.

- Si la operación está siendo sujeta a validaciones adicionales, el texto puede ser “Transferencia en validación” o alguno similar. Se sugiere indicar la causa de la validación y el tiempo máximo en el que se concretará la verificación de la operación.

- Si la operación se rechazó, el texto puede ser “Transferencia rechazada” o alguno similar.

Solo en caso de que la transferencia haya sido enviada, la Interfaz de Usuario debe mostrar los siguientes datos (con excepción del campo folio, que debe mostrarse en todos los escenarios del estado de la operación):

- Estampa de tiempo. Se debe mostrar la fecha y hora del envío de la transferencia.

- Monto. La Interfaz del Usuario debe incluir un campo con el texto “Monto”. Enseguida, se debe mostrar la cifra que se ingresó en la orden de transferencia. Este campo debe ser predominante visualmente respecto del resto de los campos.

- Concepto del pago. La Interfaz del Usuario debe incluir un campo con el texto “Concepto del pago”. Enseguida, se debe mostrar el concepto del pago que se incluyó en la orden de transferencia.

**Figura 31. Imágenes ilustrativas de la notificación en transferencias derivadas de una notificación push.**

- Información del emisor. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”. Enseguida se debe mostrar el número de la cuenta origen de forma enmascarada, dejando visibles sólo los últimos 4 dígitos.

- Información del beneficiario. La Interfaz del Usuario debe incluir un campo con el texto “Cuenta”, un campo con el texto “Participante” y un campo con el texto “Beneficiario”. En seguida se debe mostrar la siguiente información: se debe incluir la CLABE/ tarjeta/ número telefónico receptora enmascarada, dejando visibles sólo los últimos 4 dígitos, junto al texto “CLABE”, “Número de tarjeta”, “Número telefónico”. Se debe incluir el nombre corto del participante receptor junto al campo “Participante”. Para el caso del campo “Beneficiario”, se debe mostrar el nombre del beneficiario, junto al texto “Beneficiario”.

- Referencia numérica. La Interfaz del Usuario debe incluir un campo con el texto “Referencia numérica”. Enseguida, se debe mostrar la referencia numérica que se incluyó en la orden de transferencia.

- Clave de rastreo. Para operaciones inter institución, la Interfaz del Usuario debe incluir un campo con el texto “Clave de rastreo”. Enseguida, se debe mostrar la clave de rastreo que la Entidad Emisora asigne a la orden de transferencia.

- Folio CoDi. La Interfaz del Usuario debe incluir un campo con el texto “Folio CoDi”. Enseguida, se debe mostrar el folio o número de autorización que corresponda al envío de la transferencia. Este campo debe mostrarse en todos los escenarios del estado de operación. En este caso, ya que la operación deriva de una notificación _push_ generada a través del esquema CoDi, este dato corresponderá al Folio CoDi.

- Vínculo al CEP. Para operaciones inter institución, la Interfaz del Usuario deberá incluir un vínculo para la descarga del Comprobante Electrónico de Pago (CEP).

Adicionalmente, las Entidades deberán facilitar el intercambio de un comprobante que detalle las condiciones específicas en que se llevó a cabo la autorización de la transferencia.

## VII. Control de versiones

La presente “Guía para la homologación de la experiencia de usuario en transferencias electrónicas de fondos a través de dispositivos móviles”, versión 1.0, entrará en vigor a partir del 14 de diciembre de 2026.

| **Fecha de publicación** | **Fecha de entrada en vigor** | **Versión** | **Descripción de ajustes y actualizaciones** |
|---|---|---|---|
| 16-junio-2026 | 14-diciembre-2026 | 1.0 | Publicación del documento “Guías para la homologación de la experiencia de usuario en transferencias electrónicas de fondos a través de dispositivos móviles”. |
