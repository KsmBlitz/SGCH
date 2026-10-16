# ADR 0012: Redondeo por concepto, reserva con techo y otras precisiones del cálculo

- Estado: aceptada
- Fecha: 2026-10-16
- Origen: implementación del motor de cálculo (`apps/api/app/services/`)

## Contexto

La sección 8 define la fórmula del cargo por unidad y exige que la suma de los cargos iguale
el total a cobrar, pero deja abiertos algunos detalles que cambian montos al peso.

## Decisiones

1. **Mayor residuo por concepto.** El gasto común, la reserva y cada gasto extraordinario se
   reparten por separado. Así, cada concepto cuadra al peso por sí solo y la colilla muestra
   líneas que se pueden verificar por separado.
2. **Total de reserva = techo(r × G_ord).** Redondear hacia abajo podría dejar el fondo bajo el
   mínimo legal por fracciones de peso. El total redondeado se reparte luego con mayor residuo.
3. **Desempate reproducible.** Los empates de residuo se resuelven por código de unidad en orden
   ascendente.
4. **Prorrateos que no suman 1 bloquean el cierre.** Se ofrece `normalizar_prorrateos` como
   corrección explícita; la API debe exigir que el administrador la confirme y debe auditarla.
5. **Interés simple, redondeado hacia abajo,** sobre el saldo vencido de gasto común, reserva,
   extraordinarios y ajustes. No genera interés sobre intereses ni multas. **[verificar]**
6. **Orden de imputación de pagos:** período más antiguo primero; dentro del período: interés,
   multa, reserva, gasto común, extraordinario y ajuste. **[verificar]**
7. **Cuotas impagas:** períodos distintos con gasto común, reserva o extraordinario vencido e
   impago. Los intereses y las multas por sí solos no cuentan como cuota. **[verificar]**

## Consecuencias

- Una unidad puede pagar hasta $1 más por concepto que su parte exacta. La diferencia nunca se
  pierde ni se inventa a nivel de comunidad.
- Las reglas 5 a 7 son parámetros del motor (`CONCEPTOS_BASE`, `ORDEN_IMPUTACION`,
  `CONCEPTOS_CUOTA`); cambiarlas tras la revisión del abogado no exige rediseño.
- Se pospone la excepción de vivienda social al mínimo del 5%. El motor y el check
  `pct_reserva >= 0.05` de la sección 10 la rechazan hoy; cuando se confirme, habrá un ADR nuevo.
