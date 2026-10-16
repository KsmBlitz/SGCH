#!/usr/bin/env bash
# Verifica que las herramientas del entorno (sección 13 del documento maestro) estén instaladas.
# Las marcadas "etapa N" solo se necesitan desde esa etapa del plan.
set -u

falta=0

revisar() {
  local cmd="$1" nota="$2" requerida="${3:-no}"
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "  ok      %-10s %s\n" "$cmd" "$("$cmd" --version 2>&1 | head -1)"
  else
    printf "  falta   %-10s %s\n" "$cmd" "$nota"
    [ "$requerida" = "si" ] && falta=1
  fi
}

echo "Herramientas:"
revisar uv       "curl -LsSf https://astral.sh/uv/install.sh | sh" si
revisar make     "sudo apt install -y make" si
revisar git      "sudo apt install -y git" si
revisar docker   "etapa 3: Docker Engine en WSL (docs.docker.com/engine/install/ubuntu)"
revisar node     "etapa 3: Node.js 22"
revisar pnpm     "etapa 5: corepack enable pnpm"
revisar supabase "etapa 3: Supabase CLI"
revisar gh       "opcional: sudo apt install -y gh"

case "$(pwd)" in
  /mnt/*) echo "  ADVERTENCIA: el repositorio está en /mnt; muévelo al sistema de archivos de WSL." ;;
esac

exit "$falta"
