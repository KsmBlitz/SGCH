# Sistema de Gestión de Comunidades Habitacionales

Documento maestro del proyecto · Oct 15, 2026 · @Vicente Estay Valdivia

## 0. Cómo leer este documento

Este es el documento fuente de verdad del proyecto: define qué se construye, para quién, por qué y cómo. Cualquier persona o IA que se sume debe leerlo completo antes de proponer cambios de producto, de arquitectura o de negocio.

| Campo | Valor |
| --- | --- |
| Nombre provisional | Sistema de Gestión de Comunidades Habitacionales (abreviado SGCH en este documento) |
| Estado | Fase 0: definición y validación. Sin clientes ni código en producción |
| País de operación inicial | Chile, con foco comercial en la Región de Valparaíso |
| Fundador | Ingeniero en computación e informática, desarrollador único en la etapa inicial |
| Stack definido | WSL, VS Code con Claude Code, Supabase, Vercel (Next.js), FastAPI en Railway o servidor propio |

**Sobre el nombre.** Se eligió "Comunidades Habitacionales" porque cubre edificios, condominios de casas y conjuntos de departamentos, y suena natural para un residente. La ley chilena usa los términos "condominio" y "copropiedad inmobiliaria"; ambos se usan en este documento como sinónimos del cliente final. El nombre comercial definitivo se decidirá en la Fase 1.

**Convenciones del documento.**

- "Debe" indica una regla obligatoria; "debería" indica una recomendación con excepciones justificadas.
- Los montos se expresan en pesos chilenos (CLP) o en UF, según se indique.
- Todo dato legal marcado como **\[verificar\]** debe confirmarse en la fuente oficial (Biblioteca del Congreso Nacional o Minvu) antes de implementarse.
- Las decisiones técnicas se registran como ADR en la sección 9. Cambiar una decisión exige un nuevo ADR, no editar el anterior en silencio.
- Este documento no constituye asesoría legal ni financiera.

## 1. Resumen ejecutivo

SGCH será un software web, pensado primero para el escritorio, que permite a un administrador independiente emitir, cobrar y rendir los gastos comunes de 5 a 30 comunidades pequeñas y medianas en menos tiempo y con cumplimiento de la Ley 21.442.

| Elemento | Definición |
| --- | --- |
| Problema | La Ley 21.442 exige contabilidad separada, fondo de reserva, rendición mensual al comité, registro de copropietarios y cobranza trazable. Muchos administradores pequeños y comités lo hacen con Excel, correo y WhatsApp |
| Cliente que paga | Administrador independiente o pequeña empresa de administración (segmento principal). Comités que se autoadministran (segmento secundario) |
| Usuarios | Administrador y su equipo (escritorio), comité de administración (escritorio y móvil), copropietarios y residentes (móvil, solo consulta y pago) |
| Cuña de entrada | Panel multicomunidad rápido para el administrador, con emisión masiva, conciliación por cartola, cobranza por WhatsApp y rendición lista para el comité |
| Competencia | Mercado con un líder financiado (ComunidadFeliz) y varios actores establecidos. No se compite por amplitud de funciones, sino por velocidad, simplicidad y precio para carteras pequeñas |
| Modelo de negocio | Suscripción mensual por comunidad, escalonada por número de unidades, más planes para la cartera del administrador |
| Meta a 24 meses | 300 comunidades activas a través de 25 a 40 administradores |
| Siguiente paso | Validar con 10 administradores y 10 comités de la Región de Valparaíso antes de construir más allá del núcleo |

**Por qué ahora.** La Ley 21.442 rige desde 2022 y su reglamento (Decreto 7 de 2024 del Minvu) se publicó el 9 de enero de 2025, lo que detalló las obligaciones de rendición y cobro. Además, todo administrador debe inscribirse en el Registro Nacional de Administradores de Condominios, lo que profesionaliza el rubro y aumenta la demanda de herramientas formales.

**Por qué este fundador.** El fundador vive en Viña del Mar, conoce Placilla y Curauma, zonas con alta densidad de condominios nuevos, y puede construir el producto completo sin depender de terceros.

## 2. Visión, misión y principios de producto

**Visión.** Que administrar una comunidad pequeña en Chile sea tan ordenado y transparente como administrar un edificio grande con un equipo profesional.

**Misión.** Darle al administrador de comunidades pequeñas y medianas una herramienta que le ahorre horas cada mes, le permita crecer su cartera sin contratar más personas y lo mantenga en regla frente a la ley y a sus copropietarios.

**Principios de producto.** Ante un conflicto entre principios, prevalece el de número menor.

1. **Exactitud del dinero.** Un peso mal calculado destruye la confianza. Todo cálculo es reproducible, auditable y en enteros.
2. **Trazabilidad legal.** Cada cobro, pago, ajuste y rendición deja registro de quién, cuándo y por qué. Nada se borra; se anula con motivo.
3. **Velocidad del administrador.** Las tareas mensuales repetitivas (emitir, conciliar, cobrar, rendir) deben tomar minutos por comunidad, no horas.
4. **Simplicidad sobre amplitud.** Se construye menos, pero mejor. Una función que solo usa el 10% de los clientes no entra al núcleo.
5. **Escritorio para operar, móvil para consultar.** El administrador trabaja en PC con tablas, teclado y archivos. El residente consulta y paga desde el celular.
6. **Datos portables.** El cliente puede exportar todos sus datos en formatos abiertos en cualquier momento. Esto reduce el miedo a cambiarse desde la competencia.
7. **Cumplimiento por diseño.** La Ley 21.442 y la Ley 21.719 se reflejan en el modelo de datos y en los flujos, no en un manual aparte.

## 3. Contexto de mercado y marco legal

La Ley 21.442 de Copropiedad Inmobiliaria reemplazó a la Ley 19.537 y convirtió varias prácticas administrativas en obligaciones legales. Esas obligaciones son la base funcional del producto.

**Normas que rigen el dominio.**

- Ley 21.442 de Copropiedad Inmobiliaria (2022).
- Reglamento de la ley: Decreto 7 de 2024 del Minvu, publicado el 9 de enero de 2025 ([Minvu](https://www.minvu.gob.cl/wp-content/uploads/2025/01/Reglamento-de-la-ley-21442.pdf)).
- Ley 21.719 de Protección de Datos Personales, que entra en vigencia el 1 de diciembre de 2026 (sección 15).
- Normativa tributaria y laboral aplicable a la comunidad como empleadora del personal (conserjes, aseo), fuera del alcance del MVP.

**Obligaciones que el producto debe soportar.**

| Obligación | Qué exige | Cómo la resuelve SGCH |
| --- | --- | --- |
| Composición del cobro | El aviso de cobro debe mostrar la proporción de la unidad en gastos comunes, el aporte al fondo de reserva, y los intereses y multas adeudados | Colilla por unidad generada desde el cierre del período, con desglose obligatorio |
| Categorías del gasto ordinario | Administración, mantención, reparación y uso o consumo | Plan de cuentas con esas cuatro categorías como nivel superior fijo |
| Fondo común de reserva | Recargo no inferior al 5% del gasto común mensual, en cuenta o instrumento separado, para gastos urgentes, extraordinarios e imprevistos, incluidas indemnizaciones del personal **\[verificar artículo 39\]** | Porcentaje configurable con mínimo 5%, saldo propio y movimientos separados. Excepción configurable para viviendas sociales |
| Rendición de cuentas | Mensual al comité y en cada asamblea ordinaria, con respaldo de cada movimiento | Informe mensual generado automáticamente con estado de resultados, recaudación, fondo de reserva y comprobantes |
| Registro de copropietarios | Obligatorio según el reglamento (artículos 5 a 7) **\[verificar contenido exacto\]** | Módulo de unidades, propietarios y residentes con historial de cambios |
| Interés por mora | Fijado por el reglamento de copropiedad con un tope legal. Las fuentes consultadas difieren sobre el tope **\[verificar\]** | Tasa configurable por comunidad, con tope validado en el sistema una vez confirmado |
| Suspensión de servicios | Con tres o más cuotas impagas, continuas o discontinuas, acuerdo del comité, notificación previa y un solo servicio a la vez, con excepciones (por ejemplo, personas electrodependientes) | Alerta de unidades elegibles y generación del aviso. La decisión siempre es humana |
| Convenios de pago | El administrador puede pactarlos con morosos de tres o más cuotas | Registro de convenios con cuotas y seguimiento |
| Registro Nacional de Administradores | Inscripción obligatoria y gratuita en el Minvu para todo administrador | Campo de inscripción en el perfil del administrador y recordatorios |

**Lectura de mercado.** La demanda de software ya está educada: los administradores profesionales trabajan sobre plataformas como ComunidadFeliz, Edifito y Kastor. Eso reduce el esfuerzo de explicar la categoría, pero obliga a diferenciarse con claridad (sección 4).

**Preguntas abiertas de mercado.** ¿Cuántas comunidades pequeñas (menos de 60 unidades) hay en la Región de Valparaíso? ¿Qué proporción se autoadministra? Ambas se responden en la Fase 0 con datos del Minvu, del SII o con muestreo directo.

Fuentes de esta sección: [Schneider Abogados](https://schneiderabogados.cl/abogados/propiedades/ley-21442-copropiedad-inmobiliaria), [Enel, ley de condominios](https://www.enel.cl/es/clientes/tarifas-y-regulacion/ley-condominios.html), [DOE](https://actualidadjuridica.doe.cl/ley-n-21-442-conoce-mas-sobre-la-nueva-ley-de-copropiedad-inmobiliaria/), [grmotec](https://www.grmotec.cl/ley-21442-guia-completa).

## 4. Análisis competitivo

El mercado está ocupado por un líder con capital y varios actores antiguos; SGCH no debe competir en amplitud, sino ganar el segmento de carteras pequeñas con velocidad operativa y precio.

| Competidor | Posición | Precio público conocido | Fortalezas | Debilidad explotable (hipótesis) |
| --- | --- | --- | --- | --- |
| [ComunidadFeliz](https://www.comunidadfeliz.cl/administra-condominios-y-edificios-con-comunidadfeliz) | Líder. Cerca de 6.000 comunidades y unos US$ 7 millones de facturación en 2023 ([DF](https://www.df.cl/df-lab/innovacion-y-startups/los-planes-de-comunidadfeliz-para-otorgar-creditos-a-los-condominios-que)) | Desde 2 UF mensuales por comunidad, más instalación equivalente a una mensualidad | Remuneraciones certificadas por Previred, conexión con bancos, app de residentes, asesoría legal, marca | Precio alto por unidad en comunidades chicas; producto amplio y complejo para un administrador con pocas comunidades |
| [Edifito](https://edifito.com/) | Pionero, opera desde 2003 | No publicado | Pago online con Khipu y MercadoPago, paquetería, reservas, outsourcing | Producto antiguo en experiencia de uso (por validar) |
| [Condominio Feliz](https://condominiofeliz.cl/planes.php) | Nicho de precio bajo | CLP 9.990 más IVA hasta 40 unidades | Precio de entrada muy bajo, outsourcing contable | Funcionalidad y marca limitadas (por validar) |
| Kastor, EdiPro, Residentia | Actores establecidos | No revisado | Base instalada | Por investigar en la Fase 0 |

**Dónde está el espacio.** Tres huecos posibles, todos por confirmar con entrevistas:

1. **Costo por unidad en comunidades chicas.** A 2 UF, una comunidad de 12 casas paga una proporción alta de su gasto común solo en software.
2. **Productividad del administrador con cartera.** Un administrador con 15 comunidades necesita operar en lote: emitir, conciliar y cobrar las 15 en una sesión, no entrar comunidad por comunidad.
3. **Comunidades autoadministradas.** Un vecino tesorero no necesita remuneraciones ni conexión bancaria; necesita cobrar, rendir y cumplir la ley sin saber contabilidad.

**Lo que SGCH no hará en sus primeras fases:** remuneraciones certificadas, control de acceso, paquetería, créditos a comunidades. Son terreno donde los competidores llevan años de ventaja.

**Riesgo competitivo principal.** ComunidadFeliz puede lanzar un plan barato para comunidades pequeñas. La defensa es la especialización en el flujo del administrador con cartera y la relación directa en la región.

## 5. Segmentos de cliente y perfiles de usuario

El cliente que paga es el administrador; el comité aprueba y el residente consulta, y el producto debe satisfacer a los tres para no perder la cuenta.

**Segmentos, en orden de prioridad.**

| Prioridad | Segmento | Tamaño de comunidad | Quién decide la compra | Dolor principal |
| --- | --- | --- | --- | --- |
| 1 | Administrador independiente o empresa pequeña con 5 a 30 comunidades | 10 a 150 unidades | El administrador | Horas perdidas cada mes en tareas repetitivas y reclamos por falta de transparencia |
| 2 | Comunidad autoadministrada por el comité | 6 a 60 unidades | Comité, con aprobación de asamblea | Desorden, desconfianza entre vecinos y miedo a incumplir la ley |
| 3 | Inmobiliarias en etapa de primera administración | Variable | Inmobiliaria | Entregar la comunidad ordenada a su primera administración (fase futura) |

**Perfiles de usuario y propuesta de valor.**

| Perfil | Dispositivo principal | Necesita | Propuesta de valor |
| --- | --- | --- | --- |
| Administrador | PC | Emitir, conciliar, cobrar y rendir varias comunidades en lote | Cerrar el mes de una comunidad en menos de 20 minutos |
| Asistente del administrador | PC | Registrar gastos, comprobantes y pagos | Carga rápida con teclado e importación de archivos |
| Comité de administración | PC y móvil | Revisar y aprobar la rendición mensual, ver morosidad | Rendición clara, comentable y aprobable en un clic |
| Copropietario o residente | Móvil | Ver su colilla, su deuda, pagar y descargar documentos | Transparencia total sobre en qué se gasta su dinero |

**Criterio de calificación de un cliente ideal.** Administra al menos 5 comunidades, usa Excel o un software que considera caro o lento, y tiene al menos una comunidad con menos de 60 unidades.

## 6. Alcance del producto

El MVP cubre el ciclo mensual completo de una comunidad (registrar gastos, cerrar, emitir, cobrar, conciliar y rendir) y nada más.

**MVP (Fase 1).**

| Módulo | Funcionalidad | Prioridad |
| --- | --- | --- |
| Cuenta y acceso | Organización del administrador, usuarios con roles, invitación al comité y a residentes | P0 |
| Comunidades y unidades | Alta de comunidades, unidades con prorrateo, propietarios y residentes, importación por Excel o CSV | P0 |
| Gastos | Registro de gastos con categoría legal, proveedor, comprobante adjunto, gastos extraordinarios | P0 |
| Cierre y emisión | Cierre del período, prorrateo, recargo de fondo de reserva, intereses, colillas PDF por unidad, envío por correo | P0 |
| Cobranza | Registro de pagos manuales, importación de cartola bancaria con conciliación asistida, morosidad, recordatorios por WhatsApp (enlace) y correo | P0 |
| Fondo de reserva | Saldo, aportes y usos separados | P0 |
| Rendición | Informe mensual automático para el comité, con aprobación y comentarios | P0 |
| Portal del residente | Web responsive: colilla, estado de cuenta, documentos y avisos | P1 |
| Panel multicomunidad | Vista de cartera: estado de cierre, morosidad y tareas pendientes por comunidad | P0 |
| Documentos | Repositorio de reglamento, actas y contratos por comunidad | P1 |
| Exportación | Exportación completa de datos de una comunidad en Excel y CSV | P0 |

**Fuera de alcance del MVP.** Pago en línea integrado, remuneraciones del personal, facturación electrónica, conexión directa con bancos, control de acceso, reservas de espacios, paquetería, app nativa, votaciones en línea.

**Módulos futuros, en orden tentativo.**

1. Pago en línea (Khipu, Mercado Pago o Webpay) con conciliación automática.
2. Convenios de pago y gestión de suspensión de servicios.
3. Asambleas: convocatoria, quórum, actas y votación en línea **\[verificar requisitos legales de votación electrónica\]**.
4. Mantenciones y certificaciones (ascensores, gas, extintores) con calendario.
5. Lectura de medidores de agua y gas por unidad.
6. Reservas de espacios comunes con cobro automático.
7. Remuneraciones mediante integración con un proveedor existente, no desarrollo propio.
8. Asistente con IA que redacta la rendición y responde dudas de residentes sobre su cuenta.

## 7. Glosario de dominio

Estos términos se usan con el mismo significado en la interfaz, el código, la base de datos y este documento.

| Término | Definición | Nombre en el código |
| --- | --- | --- |
| Organización | Cliente que paga: administrador independiente, empresa de administración o comité autoadministrado | `organizacion` |
| Comunidad | Condominio, edificio o conjunto habitacional administrado | `comunidad` |
| Unidad | Departamento, casa, local, estacionamiento o bodega con dueño | `unidad` |
| Prorrateo (alícuota) | Proporción con que una unidad contribuye a los gastos comunes, fijada en el reglamento de copropiedad | `prorrateo` |
| Copropietario | Dueño de una o más unidades | `persona` con rol `propietario` |
| Residente | Quien habita la unidad, sea o no dueño | `persona` con rol `residente` |
| Comité de administración | Órgano que supervisa al administrador y aprueba la rendición mensual | rol `comite` |
| Período | Mes contable de la comunidad | `periodo` |
| Gasto común ordinario | Gasto de administración, mantención, reparación o uso y consumo | `gasto` con `tipo = ordinario` |
| Gasto común extraordinario | Todo gasto adicional y distinto de los ordinarios | `gasto` con `tipo = extraordinario` |
| Fondo común de reserva | Fondo para gastos urgentes, extraordinarios e imprevistos, financiado con un recargo mínimo del 5% | `fondo_reserva` |
| Cierre | Acto que congela los gastos de un período y calcula los cargos de cada unidad | `cierre` |
| Colilla (aviso de cobro) | Documento por unidad con el detalle del cobro del período | `aviso_cobro` |
| Cargo | Línea de deuda de una unidad (gasto común, reserva, interés, multa) | `cargo` |
| Abono | Pago aplicado a uno o más cargos | `abono` |
| Cartola | Extracto bancario de la cuenta de la comunidad | `cartola` |
| Conciliación | Asociar un movimiento de la cartola con un pago o un gasto | `conciliacion` |
| Moroso | Unidad con cargos vencidos e impagos | calculado, no almacenado |
| Rendición | Informe mensual del administrador al comité | `rendicion` |

## 8. Reglas de negocio

El ciclo mensual de una comunidad es la columna vertebral del sistema; toda regla de esta sección es obligatoria y debe tener pruebas automatizadas.

**Ciclo mensual.**

1. **Período abierto.** Se registran gastos ordinarios y extraordinarios con comprobante, y pagos de residentes.
2. **Revisión.** El sistema advierte gastos sin comprobante, unidades sin prorrateo y prorrateos que no suman 100%.
3. **Cierre.** Se congelan los gastos del período y se calculan los cargos de cada unidad. Un período cerrado no se edita; solo se corrige con un ajuste en el período siguiente.
4. **Emisión.** Se generan y envían las colillas por unidad.
5. **Cobranza.** Se registran pagos, se concilia la cartola y se envían recordatorios.
6. **Rendición.** Se genera el informe mensual y el comité lo aprueba o lo comenta.

**Cálculo del cargo de una unidad.** Para la unidad u en el período p, con prorrateo π (fracción entre 0 y 1) y recargo de reserva r (mínimo 0,05):

```latex
C_{u,p} = \pi_u \cdot G^{ord}_p + \pi_u \cdot r \cdot G^{ord}_p + \pi_u \cdot G^{ext}_p + I_{u,p} + M_{u,p}
```

Donde G ord es el total de gastos ordinarios, G ext el de extraordinarios aprobados para prorratear, I los intereses por mora y M las multas de la unidad.

**Reglas de cálculo.**

- Montos en pesos chilenos como enteros. Nunca decimales ni tipos de punto flotante.
- La suma de los prorrateos de una comunidad debe ser exactamente 1 (o 100%). El sistema no permite cerrar si no se cumple.
- **Redondeo:** cada cargo se redondea al peso con el método del mayor residuo, de modo que la suma de los cargos de todas las unidades sea exactamente igual al total a cobrar. La diferencia nunca se pierde ni se inventa.
- El recargo de reserva se calcula sobre el gasto común ordinario y se registra como cargo separado, con destino al saldo del fondo de reserva.
- Una unidad desocupada o que no usa un bien común paga igual.
- Gastos extraordinarios pueden prorratearse con un criterio distinto si el reglamento lo establece (por ejemplo, solo una torre). El modelo debe permitir prorrateos por grupo de unidades.

**Pagos y aplicación de abonos.**

- Un pago se aplica a los cargos más antiguos primero, y dentro del mismo período en este orden: intereses, multas, fondo de reserva, gasto común **\[verificar si el reglamento o la ley fijan otro orden\]**.
- Un pago mayor a la deuda queda como saldo a favor de la unidad.
- Ningún pago se elimina: se anula con motivo, usuario y fecha.

**Morosidad e intereses.**

- Un cargo vencido e impago hace morosa a la unidad. La morosidad se calcula, no se guarda.
- El interés por mora es una tasa configurable por comunidad, con tope legal validado **\[verificar tope\]**. Se calcula sobre el saldo vencido y se cobra en la siguiente emisión.
- Con tres o más cuotas impagas, continuas o discontinuas, la unidad queda marcada como elegible para convenio de pago o suspensión de servicio. El sistema nunca suspende ni solicita una suspensión sin acción humana registrada.

**Fondo de reserva.**

- Tiene saldo propio, alimentado por el recargo, intereses y multas según el reglamento **\[verificar destino de intereses y multas\]**.
- Su uso exige motivo, comprobante y queda destacado en la rendición.
- No puede usarse para cubrir morosidad ni gastos corrientes.

**Cierre de período y auditoría.** Toda acción que afecte dinero (gasto, cierre, pago, ajuste, anulación) genera un registro inmutable en la tabla de auditoría con usuario, fecha, valores anteriores y nuevos.

## 9. Arquitectura técnica y decisiones

La web en Vercel muestra datos y hace lecturas simples protegidas por RLS; todo cálculo con efecto económico ocurre en la API de FastAPI, que es la única que escribe cargos, pagos aplicados y cierres.

&#91;embedded content: Arquitectura del MVP · 4 servicios, 1 externo futuro\]

La línea punteada marca la pasarela de pago, que se integra en la Fase 2.

**Registro de decisiones (ADR).**

| N° | Decisión | Motivo | Alternativa descartada |
| --- | --- | --- | --- |
| 1 | Monorepo con `apps/web`, `apps/api` y `supabase/` | Un solo contexto para el fundador y para la IA (Claude Code, ver ADR 0013) | Repositorios separados |
| 2 | Next.js (App Router) con TypeScript en Vercel | Framework de referencia de Vercel; rutas públicas y privadas en un solo proyecto | SPA con Vite |
| 3 | FastAPI en Railway para la lógica de negocio | Dominio previo del fundador; Python es adecuado para cálculo, PDF e importación de planillas | Lógica en funciones de Supabase o en Next.js |
| 4 | Supabase como Postgres, Auth y Storage, en São Paulo | Reduce infraestructura; RLS nativo; latencia baja desde Chile | Postgres propio |
| 5 | Supabase CLI como única fuente de verdad del esquema; SQL explícito desde la API | Evita dos definiciones del esquema y versiona también RLS | Alembic con ORM |
| 6 | Montos en enteros CLP y prorrateos en `numeric` | Exactitud y ausencia de errores de punto flotante | `float` o decimales en montos |
| 7 | Períodos cerrados inmutables; correcciones por ajuste | Trazabilidad legal y confianza del comité | Edición de períodos cerrados |
| 8 | Escritorio primero para el administrador; web responsive para residentes, sin app nativa | El administrador opera en PC; el residente solo consulta | App nativa desde el inicio |
| 9 | Inicio de sesión con código OTP por correo | Simple para residentes y funciona igual en escritorio y móvil | Contraseñas |
| 10 | Colillas y rendiciones en PDF generados en la API | Un solo lugar para el formato legal del aviso de cobro | PDF en el navegador |
| 11 | Servidor propio como alternativa futura a Railway | Solo si el costo o el control lo justifican | Migrar antes de tener clientes |

## 10. Modelo de datos, multi-tenencia y seguridad

Toda fila de negocio pertenece a una organización y a una comunidad, y el aislamiento entre clientes se garantiza en la base de datos con Row Level Security (RLS), no solo en la aplicación.

**Jerarquía de pertenencia.** Organización → Comunidad → Unidad → Cargos y abonos. Un usuario se vincula a una organización (equipo del administrador) o a una comunidad específica (comité o residente).

**Entidades principales.**

| Tabla | Propósito | Claves y restricciones clave |
| --- | --- | --- |
| `organizaciones` | Cliente que paga | `plan`, `prueba_hasta` |
| `miembros_organizacion` | Usuarios del equipo del administrador | `rol`: owner, staff |
| `comunidades` | Condominio administrado | `organizacion_id`, RUT de la comunidad, `pct_reserva >= 0.05`, `tasa_interes_mora` |
| `accesos_comunidad` | Comité y residentes con acceso a una comunidad | `rol`: comite, residente; `unidad_id` opcional |
| `unidades` | Departamento, casa, bodega o estacionamiento | `codigo` único por comunidad, `prorrateo numeric(9,8)` |
| `grupos_prorrateo` | Prorrateos alternativos (por torre o por servicio) | Suma de prorrateos por grupo = 1 |
| `personas` | Propietarios y residentes | RUT opcional, contacto, consentimiento |
| `unidad_personas` | Relación persona y unidad con vigencia | `rol`, `desde`, `hasta` |
| `proveedores` | Proveedores de la comunidad | RUT, giro |
| `periodos` | Mes contable | `estado`: abierto, cerrado, emitido; único por comunidad y mes |
| `gastos` | Gasto ordinario o extraordinario | `categoria` legal, `monto_clp int`, comprobante |
| `cargos` | Deuda de una unidad por período y concepto | `concepto`: gasto\_comun, reserva, extraordinario, interes, multa, ajuste |
| `pagos` | Dinero recibido | `monto_clp`, medio, origen (manual, cartola, pasarela) |
| `aplicaciones_pago` | Qué parte de un pago cubre qué cargo | Suma aplicada no mayor al pago |
| `movimientos_cartola` | Líneas importadas del banco | Hash único para evitar duplicados |
| `fondo_reserva_movimientos` | Aportes y usos del fondo | Uso requiere motivo y comprobante |
| `rendiciones` | Informe mensual y su aprobación | Estado, aprobado\_por, comentarios |
| `documentos` | Reglamento, actas, contratos | Ruta en Storage |
| `grupo_prorrateo_unidades` | Miembros de un grupo de prorrateo | Prorrateo por unidad; la suma por grupo debe ser 1 al cerrar |
| `auditoria` | Registro inmutable de cambios con efecto económico | Solo inserción; sin update ni delete |

**Reglas de diseño.**

- Montos en `integer` (CLP). Prorrateos en `numeric` con 8 decimales. Nunca `float`.
- Claves primarias UUID generadas por la base de datos.
- Fechas de negocio como `date`; marcas de tiempo como `timestamptz`. Zona horaria de negocio: America/Santiago.
- Borrado lógico (`anulado_en`, `anulado_por`, `motivo`) en toda tabla con efecto económico.
- Restricciones en la base de datos (checks, uniques, foreign keys) además de la validación en la API.
- Claves foráneas compuestas: toda tabla referencia `(comunidad_id, organizacion_id)` y, según el caso, la unidad, de modo que una fila no puede mezclar clientes aunque la escriba el rol que omite RLS (ADR 0014).
- `accesos_comunidad`: el rol `residente` exige `unidad_id`; el rol `comite` no lleva unidad.

**Seguridad con RLS.**

- RLS habilitado en todas las tablas, sin excepción.
- Dos funciones auxiliares `security definer`: `es_miembro_org(org_id)` y `tiene_acceso_comunidad(comunidad_id, roles[])`.
- El residente solo ve las filas de sus unidades; el comité ve toda su comunidad pero no escribe dinero; el equipo del administrador ve todas las comunidades de su organización.
- La tabla `auditoria` no tiene políticas de update ni delete para ningún rol.
- Privilegios mínimos: `anon` no accede a nada; `authenticated` solo lee las tablas con efecto económico. Desde la web solo se escriben `personas`, `unidad_personas`, `proveedores` y `documentos`; el dinero lo escribe la API (ADR 0014).
- El comité no ve personas ni la cartola bancaria. El residente ve los cargos de sus unidades solo cuando el período está emitido, y no ve gastos, fondo de reserva ni rendiciones.
- La base impide cerrar un período si los prorrateos de la comunidad (o de un grupo usado por un extraordinario) no suman 1, y rechaza gastos o cargos nuevos en períodos cerrados.
- La API declara el usuario de cada escritura con `set_config('app.usuario_id', ..., true)` para la auditoría.
- Storage privado, con rutas `{organizacion_id}/{comunidad_id}/{carpeta}/{archivo}` y políticas que validan pertenencia.
- Prueba automatizada obligatoria: un usuario de la organización A no lee ni escribe nada de la organización B por ninguna vía (web, API ni Storage).

**Acceso desde la API.** La API se conecta con un rol que omite RLS para operaciones de cálculo. Por eso toda consulta de la API filtra por `organizacion_id` resuelto desde el JWT en una dependencia central. Esta regla se revisa en cada pull request.

## 11. Diseño de la API e integraciones

La API en FastAPI concentra todo cálculo con efecto económico; la web nunca calcula montos por su cuenta, solo los muestra.

**Convenciones.** Prefijo `/api/v1`. Autenticación con el JWT de Supabase en `Authorization: Bearer`. Errores con formato único `{"error": {"code", "message", "details"}}`. Operaciones de dinero idempotentes con cabecera `Idempotency-Key`. CORS restringido al dominio de la web. `X-Request-ID` en cada respuesta y en los logs.

**Endpoints del MVP.**

| Método | Ruta | Descripción | Rol |
| --- | --- | --- | --- |
| GET | `/me` | Usuario, organización, roles y comunidades accesibles | Todos |
| GET | `/cartera/resumen` | Estado de cada comunidad: período, morosidad, tareas pendientes | Administrador |
| POST | `/comunidades/{id}/unidades/importar` | Importa unidades y personas desde Excel o CSV con reporte de errores | Administrador |
| POST | `/comunidades/{id}/periodos/{p}/validar` | Revisa el período antes del cierre y lista advertencias | Administrador |
| POST | `/comunidades/{id}/periodos/{p}/cerrar` | Cierra y calcula cargos (idempotente) | Administrador |
| POST | `/comunidades/{id}/periodos/{p}/emitir` | Genera colillas PDF y las envía | Administrador |
| POST | `/cartera/emitir` | Cierra y emite varias comunidades en lote | Administrador |
| POST | `/pagos` | Registra un pago y lo aplica a cargos | Administrador |
| POST | `/comunidades/{id}/cartolas` | Importa una cartola y propone conciliaciones | Administrador |
| POST | `/conciliaciones/{id}/confirmar` | Confirma una conciliación propuesta | Administrador |
| GET | `/comunidades/{id}/morosidad` | Unidades morosas con saldo, antigüedad y enlace de recordatorio | Administrador, comité |
| GET | `/comunidades/{id}/rendiciones/{p}` | Rendición mensual en JSON y PDF | Administrador, comité |
| POST | `/rendiciones/{id}/aprobar` | Aprobación del comité con comentario | Comité |
| GET | `/unidades/{id}/estado-cuenta` | Estado de cuenta de una unidad | Residente de la unidad y superiores |
| GET | `/comunidades/{id}/exportar` | Exportación completa de datos | Administrador |

**Estado de la etapa 4.** Implementados: `GET /me`, `POST /comunidades/{id}/periodos`, `POST .../periodos/{aaaa-mm}/gastos`, `POST /gastos/{id}/anular`, `POST .../periodos/{aaaa-mm}/validar`, `POST .../periodos/{aaaa-mm}/cerrar`, `POST /pagos` y `POST /pagos/{id}/anular`. El resto de la tabla se construye en las etapas 5 y 6. La organización se resuelve desde el JWT (cabecera `X-Organizacion-Id` si el usuario tiene varias) y las operaciones de dinero exigen `Idempotency-Key` (ADR 0015).

**Tareas programadas** (Railway Cron, en UTC, con fechas calculadas en America/Santiago): recordatorios de cobranza, cálculo diario de intereses informativos, alertas de períodos sin cerrar y respaldo lógico semanal.

**Integraciones.**

| Integración | Fase | Uso |
| --- | --- | --- |
| Resend (correo) | 1 | Colillas, invitaciones, recordatorios. Dominio con SPF, DKIM y DMARC |
| Enlaces `wa.me` | 1 | Recordatorios de cobranza enviados por el administrador desde su WhatsApp |
| Importación de cartolas (Excel o CSV de bancos chilenos) | 1 | Conciliación asistida. Un parser por banco, empezando por los 3 más usados por los pilotos |
| Khipu, Mercado Pago o Webpay | 2 | Pago en línea con conciliación automática |
| WhatsApp Business API | 2 o 3 | Envío automático de colillas y recordatorios |
| Facturación electrónica (proveedor externo) | 3 | Solo si la comunidad o el administrador lo requiere |
| Proveedor de remuneraciones | 3 | Integración, no desarrollo propio |

## 12. Experiencia de usuario

El administrador opera en escritorio con densidad de información y teclado; el residente consulta en el celular con pocas pantallas y lenguaje simple.

**Escritorio (administrador y equipo).**

- Diseño para 1366x768 como mínimo y 1920x1080 como objetivo principal.
- Navegación lateral fija con selector de comunidad y vista de cartera como inicio.
- Tablas densas con orden, filtros, búsqueda, selección múltiple y acciones en lote.
- Atajos de teclado para las acciones frecuentes (nuevo gasto, registrar pago, siguiente comunidad).
- Carga de archivos por arrastrar y soltar: comprobantes, planillas y cartolas.
- Previsualización antes de cada acción irreversible (cierre, emisión), con el total y el número de unidades afectadas.
- Estados vacíos que enseñan el siguiente paso, no pantallas en blanco.

**Móvil (residente y comité).**

- Web responsive, sin app nativa. Inicio de sesión con código de 6 dígitos enviado por correo.
- Pantallas: mi deuda y colilla, historial de pagos, documentos, avisos, y para el comité la rendición pendiente de aprobar.
- Botón de pago destacado cuando exista pago en línea (Fase 2).

**Lenguaje y formato.** Español de Chile. Fechas `dd-mm-aaaa`. Montos `$1.234.567`. Nunca jerga contable sin explicación para el residente.

**Accesibilidad.** Contraste AA, navegación completa con teclado, etiquetas en todos los campos y objetivos táctiles de 44 px en móvil.

**Pantallas del MVP.** Cartera, comunidad (resumen), unidades y personas, gastos, cierre y emisión, cobranza y morosidad, conciliación de cartola, fondo de reserva, rendición, documentos, configuración, portal del residente.

## 13. Repositorio, entorno de desarrollo y convenciones

Un solo monorepo con la web, la API y el esquema de base de datos, desarrollado en WSL con VS Code y Claude Code.

**Estructura.**

```text
sgch/
├── apps/
│   ├── web/                 # Next.js (App Router) + TypeScript, desplegado en Vercel
│   │   └── src/
│   │       ├── app/(auth)/        # inicio de sesión
│   │       ├── app/(admin)/       # cartera y comunidades (escritorio)
│   │       ├── app/(residente)/   # portal del residente (móvil)
│   │       ├── components/
│   │       ├── lib/supabase/      # clientes server y browser
│   │       ├── lib/api.ts         # cliente tipado hacia FastAPI
│   │       └── types/database.ts  # generado por Supabase CLI
│   └── api/                 # FastAPI, desplegado en Railway
│       ├── app/
│       │   ├── core/              # configuración, seguridad, errores
│       │   ├── db/                # sesión SQLAlchemy async
│       │   ├── routers/           # endpoints por módulo
│       │   ├── services/          # lógica de negocio (cierre, prorrateo, cobranza)
│       │   ├── schemas/           # modelos Pydantic
│       │   ├── jobs/              # tareas programadas
│       │   └── utils/             # RUT, fechas, formato CLP, WhatsApp
│       └── tests/
├── supabase/
│   ├── migrations/          # única fuente de verdad del esquema y de RLS
│   ├── tests/database/      # pruebas pgTAP de aislamiento
│   └── seed.sql             # datos de desarrollo ficticios
├── docs/
│   ├── adr/                 # decisiones de arquitectura
│   └── runbooks/            # operación y recuperación
├── .claude/                 # reglas y skills de Claude Code
├── .vscode/                 # configuración compartida del editor
├── CLAUDE.md                # instrucciones del proyecto para la IA
├── .github/workflows/ci.yml
└── Makefile
```

**Herramientas.** Windows con WSL2 (Ubuntu), VS Code con la extensión WSL y Claude Code, Docker Engine dentro de WSL, Node.js 22 con pnpm, Python 3.12 con uv, Supabase CLI, Vercel CLI y Railway CLI. El repositorio se clona dentro del sistema de archivos de WSL (`~/dev/sgch`), nunca en `/mnt/c`.

**Puesta en marcha local.**

1. `supabase start` y `supabase db reset` para levantar Postgres, Auth y Storage con migraciones y datos de prueba.
2. Copiar `.env.example` a `.env` en `apps/api` y a `.env.local` en `apps/web`, con las claves de `supabase status`.
3. `make api` (FastAPI en el puerto 8000) y `make web` (Next.js en el puerto 3000).
4. `make types` para regenerar los tipos de TypeScript tras cada migración.

**Convenciones.**

- Ramas `feat/`, `fix/`, `chore/`; `main` protegida. Commits con Conventional Commits.
- Tablas, columnas y términos de dominio en español y `snake_case`, según el glosario de la sección 7.
- Python: tipado, ruff, pytest. TypeScript: modo estricto, ESLint, Prettier.
- Una migración por cambio; nunca editar una migración ya aplicada en producción.
- Secretos solo en variables de entorno de cada plataforma. La clave `service_role` jamás llega al navegador.

**Nota sobre el trabajo previo.** Existe un esqueleto parcial creado para la idea anterior de transporte escolar (configuración de FastAPI, utilidades de RUT, formato CLP y WhatsApp, patrón de RLS y CI). Esas piezas se reutilizan; las tablas de dominio se reemplazan por las de este documento.

## 14. Calidad, pruebas, despliegue y operación

El dinero de los clientes exige que el cálculo esté cubierto por pruebas antes de cualquier piloto, y que cada despliegue sea reversible.

**Pruebas obligatorias.**

| Capa | Herramienta | Qué se prueba |
| --- | --- | --- |
| Cálculo | pytest con casos tabulados y pruebas por propiedades (Hypothesis) | Prorrateo, redondeo por mayor residuo, reserva, intereses, aplicación de pagos. La suma de cargos siempre iguala el total |
| API | pytest y httpx | Autorización por rol, idempotencia del cierre y de los pagos, errores |
| Base de datos | pgTAP con `supabase test db` | Aislamiento entre organizaciones, permisos de comité y residente, inmutabilidad de la auditoría |
| Web | Vitest y Testing Library | Formularios y tablas críticas |
| Extremo a extremo | Playwright | Alta de comunidad, cierre, emisión, pago y rendición |

**Casos que bloquean un piloto si fallan.**

- Un usuario de una organización no accede a datos de otra por ninguna vía.
- Cerrar dos veces un período no duplica cargos.
- La suma de cargos emitidos coincide al peso con el total de gastos más reserva.
- Un pago anulado restituye la deuda exacta.
- Un residente solo ve las unidades a las que está vinculado.

**CI/CD.** GitHub Actions ejecuta lint, tipos y pruebas en cada pull request. Vercel genera un entorno de vista previa por rama. Railway despliega la API desde `main`. Las migraciones se aplican con `supabase db push` en un paso manual aprobado.

**Entornos.** Local, staging (desde el primer piloto) y producción. Supabase en la región de São Paulo para menor latencia desde Chile.

**Operación.**

- Respaldos diarios de Supabase y un respaldo lógico semanal propio; restauración probada antes del primer cliente.
- Monitoreo de disponibilidad del endpoint `/health` y errores con Sentry.
- Logs estructurados sin datos personales.
- Runbooks para: restaurar una base, revertir un cierre erróneo mediante ajuste, y atender una solicitud de datos de un titular.

**Definición de terminado.** Código con pruebas, migración versionada si cambia el esquema, RLS revisado, documentación actualizada y probado en staging.

## 15. Privacidad, seguridad y cumplimiento

SGCH trata datos personales y financieros de miles de residentes, por lo que la Ley 21.719, vigente desde el 1 de diciembre de 2026, debe estar resuelta en el diseño antes del primer cliente.

**Roles en el tratamiento de datos.** La comunidad, representada por su administrador, es responsable del tratamiento de los datos de sus copropietarios y residentes. SGCH actúa como encargado de tratamiento por cuenta de la comunidad **\[validar con abogado\]**. Esto se formaliza en un contrato de encargo firmado con cada cliente.

**Datos tratados.** Nombre, RUT (opcional), correo, teléfono, unidad, deuda, pagos y comprobantes. No se tratan datos sensibles salvo que el cliente los cargue en documentos; el sistema debe advertir contra ello.

**Medidas.**

- Minimización: solo los campos necesarios para cobrar y comunicar.
- Cifrado en tránsito (HTTPS) y en reposo (Supabase).
- RLS, Storage privado, URLs firmadas de corta duración y mínimo privilegio.
- Registro de accesos a documentos y de exportaciones.
- Procedimiento para los derechos de los titulares (acceso, rectificación, supresión, portabilidad) con plazos internos.
- Plan de respuesta a incidentes con notificación al cliente y, cuando corresponda, a la autoridad **\[verificar plazos de la Ley 21.719\]**.
- Retención: definir plazos por tipo de dato, considerando que las deudas de gastos comunes pueden cobrarse durante años.

**Documentos legales necesarios antes del piloto.** Términos de servicio, política de privacidad, contrato de encargo de tratamiento y acuerdo de nivel de servicio básico, todos revisados por un abogado.

**Límite de responsabilidad.** SGCH es una herramienta de gestión. No presta asesoría legal ni contable, y la responsabilidad de la administración sigue siendo del administrador y del comité.

## 16. Modelo de negocio, precios y métricas

Suscripción mensual por comunidad, escalonada por unidades, con un precio medio esperado de CLP 32.000 más IVA; con 300 comunidades el negocio factura cerca de CLP 9,6 millones al mes.

**Precios propuestos (hipótesis a validar, CLP más IVA por comunidad al mes).**

| Plan | Unidades | Precio | Incluye |
| --- | --- | --- | --- |
| Pequeña | Hasta 30 | 19.990 | Ciclo mensual completo, portal del residente, rendición |
| Mediana | 31 a 80 | 34.990 | Lo anterior, más grupos de prorrateo y conciliación de cartola |
| Grande | 81 a 150 | 49.990 | Lo anterior, más soporte prioritario |
| Cartera | 10 o más comunidades de un mismo administrador | 15% de descuento sobre el total | Panel multicomunidad y emisión en lote |

Referencias de mercado: ComunidadFeliz parte en 2 UF por comunidad y Condominio Feliz en CLP 9.990 más IVA hasta 40 unidades (sección 4). SGCH se ubica entre ambos, con un valor justificado por el ahorro de tiempo del administrador.

**Reglas comerciales.** Sin costo de instalación para los primeros 50 clientes. Plan anual con dos meses gratis. Prueba de 30 días sin tarjeta. Importación de datos asistida incluida.

**Proyección base (hipótesis).**

| Hito | Comunidades activas | Administradores | Ingreso mensual (CLP, sin IVA) |
| --- | --- | --- | --- |
| Mes 6 | 20 | 3 a 4 | 640.000 |
| Mes 12 | 80 | 8 a 12 | 2.560.000 |
| Mes 18 | 180 | 15 a 25 | 5.760.000 |
| Mes 24 | 300 | 25 a 40 | 9.600.000 |

**Costos de operación estimados en la etapa inicial.** Infraestructura (Supabase, Vercel, Railway, correo) entre USD 100 y 300 al mes; dominio, contador y abogado como gastos fijos menores. El margen bruto objetivo es superior al 85%.

**Métricas que importan.**

| Métrica | Meta |
| --- | --- |
| Comunidades activas y ingreso mensual recurrente | Según la proyección |
| Abandono mensual de comunidades | Menor a 2% |
| Tiempo de cierre y emisión por comunidad | Menor a 20 minutos |
| Porcentaje de recaudación dentro del mes en clientes | Aumento medible frente a su línea base |
| Comunidades por administrador | Creciente, señal de expansión dentro de la cuenta |
| Costo de adquisición recuperado | En menos de 6 meses |

## 17. Estrategia comercial y validación

La venta inicial es directa, presencial y regional: un administrador convencido trae entre 5 y 30 comunidades, por lo que cada conversación vale mucho.

**Validación previa a construir más allá del núcleo (2 a 3 semanas).**

1. Entrevistar a 10 administradores de Viña del Mar, Valparaíso, Quilpué y Concón, y a 10 comités autoadministrados de Placilla, Curauma y Reñaca.
2. Preguntas clave: cuántas comunidades administra, qué software usa y cuánto paga, cuántas horas le toma cerrar un mes, qué le reclaman los residentes, qué haría que se cambie.
3. Mostrar un prototipo clicable de la vista de cartera y del cierre.
4. Pedir un compromiso concreto: piloto con dos comunidades reales y precio acordado al terminar la prueba.

**Criterio para avanzar.** Al menos 3 administradores con piloto comprometido o 5 comités dispuestos a pagar. Si no se cumple, se revisa el segmento o la propuesta de valor antes de seguir programando.

**Canales de adquisición.**

| Canal | Fase | Acción |
| --- | --- | --- |
| Venta directa presencial | 1 | Visitas a administradores de la región con demostración |
| Referidos | 1 y 2 | Un mes gratis por cada administrador referido que active comunidades |
| Contenido sobre la Ley 21.442 | 2 | Guías prácticas, plantillas y calculadoras gratuitas para atraer búsquedas |
| Cursos para administradores | 2 | Alianza con quienes dictan la capacitación exigida para el Registro Nacional |
| Inmobiliarias | 3 | Primera administración de proyectos nuevos |
| Expansión a otras regiones | 3 | Santiago y Biobío, con venta remota |

**Migración desde la competencia.** Importación asistida de unidades, prorrateos y deudas desde Excel o exportaciones de otros sistemas, sin costo, para eliminar la principal barrera de cambio.

**Soporte.** WhatsApp y correo en horario hábil, con base de conocimiento en el producto. El fundador atiende personalmente a los primeros 20 clientes para aprender del uso real.

## 18. Hoja de ruta y visión a 3 años

El proyecto avanza en cuatro fases y solo pasa a la siguiente cuando cumple una condición medible; las fechas son metas, las condiciones son obligatorias.

&#91;embedded content: Hoja de ruta 2026 a 2028 · 4 fases, 3 condiciones de avance\]

Si una condición no se cumple en su plazo, se revisa el segmento, el precio o la propuesta de valor antes de seguir construyendo.

**Próximos 30 días.**

- [ ] Definir el nombre comercial y revisar marca en INAPI y dominio en NIC Chile.
- [ ] Preparar el guion de entrevista y agendar 10 administradores y 10 comités.
- [ ] Construir un prototipo clicable de la vista de cartera, el cierre y la colilla.
- [ ] Consultar con un abogado los puntos marcados **\[verificar\]**.
- [ ] Adaptar el esqueleto del repositorio al modelo de datos de la sección 10.
- [ ] Implementar y probar el motor de prorrateo y cierre, sin interfaz, con casos reales de una comunidad conocida.

**Visión a 3 años.** SGCH es la herramienta de referencia para administradores de comunidades pequeñas y medianas en Chile. Opera en las principales regiones, procesa los pagos de sus comunidades y usa el historial de datos para anticipar morosidad y planificar mantenciones. Un equipo de 3 a 5 personas sostiene el producto, con el fundador a cargo de producto y tecnología.

## 19. Riesgos, supuestos y preguntas abiertas

El mayor riesgo no es técnico sino comercial: que los administradores no cambien de plataforma aunque el producto sea mejor.

| Riesgo | Probabilidad | Impacto | Mitigación |
| --- | --- | --- | --- |
| Los administradores no migran desde su software actual | Alta | Alto | Migración gratuita, piloto con dos comunidades, precio menor y exportación libre |
| ComunidadFeliz lanza un plan barato para comunidades pequeñas | Media | Alto | Especialización en el flujo de cartera y relación regional |
| Error de cálculo en un cobro emitido | Media | Muy alto | Pruebas por propiedades, previsualización obligatoria, ajustes trazables |
| Interpretación incorrecta de la Ley 21.442 | Media | Alto | Revisión por abogado de reglas y documentos; parámetros configurables |
| Incidente de seguridad o fuga de datos | Baja | Muy alto | RLS, pruebas de aislamiento, respaldos y plan de incidentes |
| Dependencia de un desarrollador único | Alta | Alto | Este documento, ADR, pruebas y código legible por otra persona o IA |
| Diversidad de formatos de cartola bancaria | Alta | Medio | Parser por banco, empezando por los usados por los pilotos |
| Ciclo de venta lento a comités | Media | Medio | Priorizar administradores con cartera |

**Supuestos a validar en la Fase 0.**

- [ ] Un administrador con cartera pagaría entre CLP 20.000 y 50.000 por comunidad.
- [ ] Cerrar y emitir una comunidad toma hoy más de una hora.
- [ ] Existe una proporción relevante de comunidades pequeñas que se autoadministran en la región.
- [ ] La conciliación de cartola es uno de los tres dolores principales.

**Preguntas abiertas.**

- [ ] Tope exacto del interés por mora y orden legal de imputación de pagos.
- [ ] Destino legal de intereses y multas (fondo de reserva u operación).
- [ ] Requisitos para votaciones y asambleas en línea.
- [ ] Nombre comercial definitivo y disponibilidad de marca en INAPI y dominio en NIC Chile.
- [ ] Forma jurídica de la empresa y régimen tributario.

## 20. Guía para colaboradores e IA

Quien trabaje en este proyecto, persona o IA, debe respetar este documento como contrato: si una tarea lo contradice, se detiene y lo señala antes de implementar.

**Antes de escribir código.**

1. Leer las secciones 7 (glosario), 8 (reglas de negocio) y 10 (modelo de datos).
2. Identificar si la tarea toca dinero, permisos o datos personales. Si es así, aplican las reglas reforzadas.
3. Revisar los ADR de la sección 9; no reabrir una decisión sin proponer un ADR nuevo.

**Reglas no negociables.**

- Montos en enteros CLP. Nunca `float` para dinero.
- Toda tabla nueva lleva `organizacion_id` o se relaciona con una tabla que lo tenga, y nace con RLS habilitado y su prueba de aislamiento.
- Toda consulta de la API filtra por la organización del usuario autenticado.
- Ningún registro con efecto económico se borra: se anula con motivo.
- El esquema solo cambia mediante migraciones en `supabase/migrations`.
- No registrar datos personales en logs ni en mensajes de error.
- Toda regla legal nueva cita su artículo y se marca **\[verificar\]** hasta que un abogado la confirme.

**Cómo pedir trabajo a una IA (por ejemplo, en Claude Code).** Incluir: el objetivo en una frase, las secciones de este documento que aplican, los archivos involucrados, el criterio de aceptación y las pruebas que deben pasar. Ejemplo: "Implementa el cierre de período según la sección 8, en `apps/api/app/services/cierre.py`, con pruebas que verifiquen que la suma de cargos iguala el total."

**Instrucciones para Claude Code.** `CLAUDE.md` resume las reglas no negociables y se carga en todas las conversaciones; `.claude/rules/` agrega reglas por carpeta y `.claude/skills/` los flujos repetibles (migraciones, reglas de negocio, ADR). Deben actualizarse cuando cambie este documento.

**Mantención de este documento.** Toda decisión de producto, precio o arquitectura relevante se refleja aquí en la misma semana. La fecha del encabezado indica la última revisión completa.

## 21. Fuentes

- [Reglamento de la Ley 21.442, Minvu](https://www.minvu.gob.cl/wp-content/uploads/2025/01/Reglamento-de-la-ley-21442.pdf)
- [Copropiedad inmobiliaria: gastos comunes, administrador y conflictos, Schneider Abogados](https://schneiderabogados.cl/abogados/propiedades/ley-21442-copropiedad-inmobiliaria)
- [Ley de condominios y suspensión de suministro, Enel](https://www.enel.cl/es/clientes/tarifas-y-regulacion/ley-condominios.html)
- [Ley 21.442, preguntas frecuentes, DOE Actualidad Jurídica](https://actualidadjuridica.doe.cl/ley-n-21-442-conoce-mas-sobre-la-nueva-ley-de-copropiedad-inmobiliaria/)
- [Ley 21.442: guía completa, grmotec](https://www.grmotec.cl/ley-21442-guia-completa)
- [Guía sobre el fondo común de reserva, ComunidadFeliz](https://www.comunidadfeliz.cl/post/guia-fondo-comun-reservas-condominios)
- [Los planes de ComunidadFeliz para otorgar créditos, Diario Financiero](https://www.df.cl/df-lab/innovacion-y-startups/los-planes-de-comunidadfeliz-para-otorgar-creditos-a-los-condominios-que)
- [ComunidadFeliz, planes y funciones](https://www.comunidadfeliz.cl/administra-condominios-y-edificios-con-comunidadfeliz)
- [Edifito](https://edifito.com/)
- [Condominio Feliz, planes y precios](https://condominiofeliz.cl/planes.php)

Las fuentes legales secundarias se usaron para orientar el diseño. Toda regla marcada **\[verificar\]** debe confirmarse en el texto oficial de la ley en la Biblioteca del Congreso Nacional.
