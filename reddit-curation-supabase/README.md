# reddit-curation-supabase

Instancia **local y aislada** de Supabase para el panel de curación de Reddit.
No comparte `project_id`, puertos ni volumen Docker con `api_arkos_remittance`
ni con otros proyectos locales.

## Requisitos

- Docker Desktop encendido
- [Supabase CLI](https://supabase.com/docs/guides/local-development)

## Inicio

```bash
cd reddit-curation-supabase
supabase start
supabase status
```

`supabase start` aplica las migraciones en esta base nueva.

## Puertos (distintos a los default 5432x)

| Servicio | URL |
|---|---|
| API / REST | http://127.0.0.1:55321 |
| Postgres | postgresql://postgres:postgres@127.0.0.1:55322/postgres |
| Studio | http://127.0.0.1:55323 |
| Mailpit | http://127.0.0.1:55324 |

Las claves **anon** y **service_role** las imprime `supabase status`.
Son las de esta instancia local; úsalas en el dashboard (anon) y en el
ingestor (service_role).

## Comandos útiles

```bash
# Conserva los datos de esta instancia
supabase stop

# Borra y recrea SOLO esta base (no toca ark-os ni otras)
supabase db reset

# Ver estado
supabase status
```
