# ADR 0013: VS Code con Claude Code en lugar de Cursor

- Estado: aceptada
- Fecha: 2026-10-16
- Reemplaza parcialmente: ADR 0001 (en el motivo, "la IA en Cursor")

## Decisión

El entorno de desarrollo es VS Code, conectado a WSL con la extensión Remote - WSL, más
Claude Code como asistente de IA. Se elimina `.cursor/rules/`.

## Cómo se organiza el contexto para la IA

- `CLAUDE.md`: reglas no negociables, comandos y estructura. Se carga en toda sesión.
- `.claude/rules/`: reglas por carpeta con `paths:`; se cargan solo al tocar esos archivos.
- `.claude/skills/`: flujos repetibles del proyecto (regla de negocio, migración, ADR, revisión).
- `CLAUDE.local.md`: preferencias personales, fuera de git.
- `.vscode/`: configuración y extensiones recomendadas, compartidas en el repositorio.

## Motivo

Decisión del fundador. Claude Code funciona en la terminal y dentro de VS Code, y sus
instrucciones por carpeta y sus skills cubren lo que hacían las reglas de Cursor.

## Alternativa descartada

Seguir con Cursor.
