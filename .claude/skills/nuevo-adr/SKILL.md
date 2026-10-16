---
name: nuevo-adr
description: Registra una decisión de arquitectura, de producto técnico o de interpretación de reglas en docs/adr/ de SGCH, con numeración correlativa e índice. Úsala cuando se tome o cambie una decisión técnica, o cuando el documento maestro deba reflejar una decisión nueva.
argument-hint: "[título de la decisión]"
---

# Nuevo ADR

Decisión: $ARGUMENTS

## ADR existentes

!`ls docs/adr/`

## Pasos

1. Toma el siguiente número correlativo de 4 dígitos según la lista de arriba.
2. Crea `docs/adr/NNNN-<slug-sin-tildes>.md` con este formato:

   ```markdown
   # ADR NNNN: <Título>

   - Estado: aceptada | propuesta
   - Fecha: <aaaa-mm-dd de hoy>
   - Reemplaza: ADR XXXX (solo si corresponde)

   ## Contexto
   ## Decisión
   ## Motivo
   ## Alternativa descartada
   ## Consecuencias
   ```

3. Nunca edites el cuerpo de un ADR aceptado. Si una decisión cambia, el ADR nuevo indica
   "Reemplaza: ADR XXXX". En el anterior, solo se puede cambiar el estado a "reemplazada por NNNN".
4. Agrega la fila al índice `docs/adr/README.md`.
5. Si la decisión cambia algo del documento maestro, muestra al usuario las líneas a modificar y
   pide confirmación antes de editarlo.
6. Si la decisión afecta una regla de `CLAUDE.md` o de `.claude/rules/`, actualízala también.
