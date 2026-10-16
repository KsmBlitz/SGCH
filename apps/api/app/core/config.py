"""Configuración de la API, leída del entorno o de `.env` (ver `.env.example`)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Conexión con un rol que omite RLS (sección 10): por eso todo filtra por organización.
    database_url: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres"
    # Supabase firma con una clave asimétrica (JWKS) o, en proyectos antiguos y en local, con HS256.
    jwks_url: str | None = None
    jwt_secret: str | None = None
    jwt_audience: str = "authenticated"
    cors_origins: list[str] = ["http://localhost:3000"]
