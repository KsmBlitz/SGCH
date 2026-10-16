# SGCH

Sistema de Gestión de Comunidades Habitacionales: software para que administradores de
comunidades pequeñas y medianas emitan, cobren y rindan los gastos comunes conforme a la
Ley 21.442.

El producto, las reglas de negocio y la arquitectura están en
[el documento maestro](Sistema%20de%20Gestión%20de%20Comunidades%20Habitacionales.md). Las
decisiones técnicas están en [docs/adr](docs/adr/README.md).

## Puesta en marcha

Requisitos actuales: [uv](https://docs.astral.sh/uv/) y `make`.

```bash
make doctor        # revisa herramientas
make api-install   # instala dependencias de la API
make check         # lint, tipos y pruebas
```
