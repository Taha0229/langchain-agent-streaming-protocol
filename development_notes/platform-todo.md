# Platform TODO

Work that spans the frontend, backend and ai service.

## Resource URLs

Dev uploads resources to the public `resources` bucket in Supabase Storage and passes permanent public URLs around (`put_source` in `last-lab-be/app/services/core/infra/storage/__init__.py`, marked DEV ONLY). The ai service downloads that URL and sends the bytes to Chunkr.

- [ ] Before production: keep objects private in GCS and presign per request
  - [ ] Send Chunkr a signed URL directly instead of downloading the bytes
  - [ ] The Source tab needs a fresh signed URL on every page load, because a signed URL saved in the checkpoint expires

## Surviving a backend restart

Thread state lives in `InMemorySaver`, and the run plus its event buffer live in an in-process session. A backend restart loses every thread's state and replay; in dev that includes the uvicorn auto-reload on every code change.

- [ ] Postgres checkpointer, so `values` (including `url`) survive a restart
- [ ] Redis Streams for the event buffer, so replay survives a restart and works across workers
- [ ] Until then, the lab tabs read only the channels, so a restarted server shows empty tabs. Once state survives, seed the tabs from checkpoint `values` when nothing replays.
