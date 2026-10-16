---
name: regla-negocio
description: Implementa o modifica una regla de negocio con efecto económico en el motor de cálculo de SGCH (prorrateo, cierre, reserva, extraordinarios, cobranza, aplicación de pagos, intereses, multas, morosidad). Úsala siempre que un cambio pueda alterar un monto en pesos.
argument-hint: "[regla a implementar]"
---

# Regla de negocio con dinero

Regla pedida: $ARGUMENTS

## 1. Antes de escribir código

1. Lee en el documento maestro la sección 8 y las partes de las secciones 3 y 7 que apliquen.
2. Revisa `docs/adr/0012-*.md` (redondeo, reserva, orden de imputación, interés).
3. Si la regla contradice el documento o un ADR, o si depende de un punto **[verificar]**, detente
   y pregúntale al usuario antes de seguir.
4. Escribe en una frase el invariante que nunca debe romperse (por ejemplo, "la suma de cargos
   iguala el total").

## 2. Implementación (`apps/api/app/services/`)

- Funciones puras con dataclasses `frozen=True`; la fecha llega como parámetro.
- Montos `int`, tasas y prorrateos `Decimal`, cálculo en `Fraction`.
- Todo reparto entre unidades pasa por `prorrateo.repartir`, ordenando por código de unidad.
- Los parámetros legales van como constantes del módulo, con artículo y **[verificar]**.
- Valida las entradas y lanza `<Algo>InvalidoError(ValueError)` con un mensaje en español.

## 3. Pruebas (`apps/api/tests/`)

Toda regla necesita los tres tipos:

1. **Caso tabulado a mano:** 2 o 3 unidades, con el cálculo explicado en el docstring de la prueba.
2. **Caso realista:** usa `tests/comunidad_ficticia.py`.
3. **Propiedad Hypothesis:** el invariante del paso 1.4 sobre entradas aleatorias.

Agrega también casos de entradas inválidas con `pytest.raises`.

## 4. Verificación y cierre

1. `make check` en verde.
2. Comprueba que las pruebas detectan errores: introduce temporalmente un error de redondeo o de
   orden y confirma que fallan. Revierte el error.
3. Si la regla fija una interpretación nueva, propone un ADR (`/nuevo-adr`) y el cambio en la
   sección 8 del documento maestro.
4. Resume para el usuario: la regla, el invariante, los casos probados y los puntos que siguen
   en **[verificar]**.
