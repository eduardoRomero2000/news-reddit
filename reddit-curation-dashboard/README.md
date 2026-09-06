# reddit-curation-dashboard

Panel en Next.js. Modo **oscuro por defecto** (cálido, bajo contraste) con
toggle a modo papel en la esquina superior derecha; la preferencia se guarda
en `localStorage` y se aplica antes del primer pintado para que no parpadee.
Tipografía grande para revisar historias sin cansar la vista.

## Uso

```bash
cd reddit-curation-supabase && supabase start
cd ../reddit-curation-dashboard
cp .env.example .env.local   # ya viene listo para la instancia local
npm run dev
```

Abre http://localhost:3000

`.env.local` apunta a `http://127.0.0.1:55321` y usa la anon key de
demo local. El dashboard solo lee y marca `used`; no inserta posts.

## Notas

- Las tarjetas con "sin métricas aún" entraron por el fallback RSS del
  ingestor (Reddit no expone score ahí). Ver `reddit-curation-ingestor/README.md`
  para activar OAuth y tener score/comentarios reales.
- "Actualizar" vuelve a leer Supabase; "última ingesta" sale del `fetched_at`
  más reciente en la tabla.
