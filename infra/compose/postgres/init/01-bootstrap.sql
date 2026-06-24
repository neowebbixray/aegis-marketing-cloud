-- Aegis Marketing Cloud — PostgreSQL Bootstrap
-- Creates additional databases needed by the platform

CREATE DATABASE aegis_n8n;
CREATE DATABASE aegis_notifications;
CREATE DATABASE aegis_analytics;

-- Extensions for the main application database
-- Database name is set via POSTGRES_DB env var; override files may change it.
-- The docker-compose.override.yml sets aegis_marketing_cloud for local dev.
\c aegis_marketing_cloud
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "ltree";

-- Vector extension for AI embeddings (optional, can use Qdrant instead)
-- CREATE EXTENSION IF NOT EXISTS "vector"; -- vector extension disabled for CI
