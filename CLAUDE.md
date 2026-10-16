# SGCH: Sistema de Gestión de Comunidades Habitacionales

SaaS para que administradores de condominios en Chile emitan, cobren y rindan gastos comunes
cumpliendo la Ley 21.442. Hoy está en la fase 0, sin clientes y con un desarrollador único.
Responde siempre en español de Chile.

## Fuente de verdad

- `Sistema de Gestión de Comunidades Habitacionales.md` es el documento maestro (unos 50 KB; no
  lo importes completo, lee la sección que necesites). Secciones clave: 7 (glosario), 8 (reglas
  de negocio), 10 (modelo de datos y RLS), 11 (API), 14 (pruebas) y 20 (reglas para la IA).
- `docs/adr/`: decisiones de arquitectura. Un ADR aceptado no se edita; se reemplaza con uno nuevo
  (skill `/nuevo-adr`).
- Si una tarea contradice el documento o un ADR, **detente y señálalo antes de implementar**.
- Toda decisión de producto o arquitectura se refleja en el documento maestro la misma semana.

## Reglas no negociables

1. Montos de dinero en `int` CLP. Nunca `float`. Tasas y prorrateos en `Decimal` (prorrateo con
   8 decimales, `numeric(9,8)`); el cálculo interno usa `fractions.Fraction`.
2. Redondeo por mayor residuo (`app/services/prorrateo.py::repartir`): la suma de las partes
   iguala el total al peso. No inventes otro método de redondeo.
3. Nada con efecto económico se borra: se anula con `anulado_en`, `anulado_por` y `motivo`. Los
   períodos cerrados no se editan; se corrigen con un cargo `ajuste` en el período siguiente.
4. Toda tabla lleva `organizacion_id` (directo o por relación), nace con RLS habilitado y con su
   prueba de aislamiento pgTAP.
5. Toda consulta de la API filtra por la organización resuelta desde el JWT. La API usa un rol
   que omite RLS, así que este filtro es la única barrera.
6. La web nunca calcula montos: solo muestra lo que devuelve la API.
7. El esquema solo cambia con migraciones nuevas en `supabase/migrations/`. Nunca edites una
   migración ya aplicada.
8. Sin datos personales (nombre, RUT, correo, teléfono) en logs ni en mensajes de error.
9. Toda regla legal cita su artículo y queda marcada **[verificar]** hasta que un abogado la
   confirme. Las marcadas hoy: tope de interés, orden de imputación de pagos, destino de
   intereses y multas, artículo 39 (fondo de reserva).
10. El sistema nunca suspende servicios ni firma convenios por su cuenta: solo marca la
    elegibilidad, y la decisión humana queda registrada.

## Comandos

```bash
make check          # lint + formato + mypy + pytest (lo mismo que CI). Correr antes de dar algo por terminado
make api-test       # solo pytest
make api-fmt        # ruff format + ruff check --fix
make doctor         # herramientas instaladas y faltantes
cd apps/api && uv run pytest tests/test_cierre.py -k reserva   # una prueba puntual
```

`uv` vive en `~/.local/bin`. Si `make` no lo encuentra, ejecuta
`export PATH="$HOME/.local/bin:$PATH"`.

## Estructura

```text
apps/api/            Python 3.12 + uv. Hoy: motor de cálculo puro, sin BD ni FastAPI todavía
  app/services/      prorrateo, cierre, cobranza, intereses, cargos (tipos compartidos)
  app/utils/         rut, formato (CLP, fechas, zona America/Santiago)
  tests/             pytest + Hypothesis; comunidad_ficticia.py es el fixture principal
docs/adr/            ADR 0001-0013
.claude/rules/       reglas por carpeta (api, supabase, web)
.claude/skills/      flujos del proyecto: regla-negocio, nueva-migracion, nuevo-adr, revisar-cambios
```

Aún no existen `apps/web/` (Next.js, etapa 5) ni `supabase/` (etapa 3).

## Plan por etapas

| Etapa | Contenido | Estado |
|---|---|---|
| 0-2 | Entorno, esqueleto, motor de cálculo | Hecho |
| 3 | Esquema Supabase, RLS, pgTAP (requiere Docker Engine en WSL) | Siguiente |
| 4 | API FastAPI: JWT, organización, idempotencia, cierre y pagos | |
| 5 | Web Next.js: login OTP, cartera, comunidad, unidades, gastos | |
| 6 | PDF, correo, cartola, rendición, exportación, portal del residente | |
| 7 | Staging, Sentry, respaldos y piloto | |

No adelantes trabajo de etapas futuras sin preguntar.

## Glosario mínimo (dominio → código)

Organización `organizacion` · Comunidad `comunidad` · Unidad `unidad` · Prorrateo `prorrateo` ·
Período `periodo` · Gasto `gasto` (`ordinario`/`extraordinario`) · Cargo `cargo` (conceptos:
`gasto_comun`, `reserva`, `extraordinario`, `interes`, `multa`, `ajuste`) · Pago `pago` ·
Aplicación de pago `aplicacion_pago` · Colilla `aviso_cobro` · Cartola `cartola` ·
Rendición `rendicion` · Fondo de reserva `fondo_reserva`. La morosidad se calcula, no se guarda.

## Convenciones

- Identificadores de dominio, docstrings y mensajes en español, en `snake_case`. Las palabras
  clave y las librerías mantienen su nombre en inglés.
- Python: `mypy --strict` sin `# type: ignore` nuevos salvo en pruebas de entradas inválidas;
  dataclasses `frozen=True` para valores de dominio; funciones puras en `services/`.
- Pruebas: casos tabulados verificables a mano y además pruebas por propiedades (Hypothesis) para
  todo invariante de dinero. Una regla de la sección 8 sin prueba no está terminada.
- Git: ramas `feat/`, `fix/` y `chore/`; Conventional Commits en español
  (`feat(cierre): agrega multas por unidad`). `main` protegida.
- Formatos visibles: montos `$1.234.567`, fechas `dd-mm-aaaa`, zona `America/Santiago`.

## Entorno

- WSL2 Ubuntu con VS Code (extensión WSL) y Claude Code; ver `.vscode/extensions.json`.
- Claude no tiene sudo. Lo que requiera `sudo apt ...` se le pide al usuario para que lo ejecute
  con el prefijo `!`.
- Remoto: `origin` → `github.com/KsmBlitz/SGCH`. No hagas push sin que el usuario lo pida; el CI
  (`.github/workflows/ci.yml`) corre en GitHub tras el push.

## Definición de terminado

Código con pruebas, `make check` en verde, migración versionada si cambia el esquema, RLS
revisado, documento maestro o ADR actualizados si cambió una decisión y, desde la etapa 7,
probado en staging.
