# Probe-2-Plot on the Synology NAS

From v1.9.0 Probe-2-Plot can run on the NAS (DS1019+, Container Manager) with a **project library**: saved cooks
stay in the app and can be opened again at any time. On Streamlit Community Cloud the app has no library (the
public app would show your cooks to anyone, and Cloud loses files when it restarts); there, use
*Project, Save project file* and *Open a project file*. Both use the same `.p2p` files, so a project saved on
Cloud can be opened on the NAS and the other way round.

## How it is set up

| Item | Value |
|---|---|
| NAS folder | `docker/probe-2-plot` (same share as `docker/bresaola`, so the same Hyper Backup task covers it) |
| Address | `http://<NAS IP>:8522` (host networking; MailPlus blocks 8500-8507, Bresaola uses 8520) |
| Container / image | `probe-2-plot` / `probe-2-plot:<version>` (the tag changes with every version, so *Build* really rebuilds) |
| Library | `docker/probe-2-plot/data/projects/<id>.p2p`, one file per project; deleted projects move to `data/projects/deleted/` |
| Settings | `P2P_MODE=library` (turns the library on), `P2P_DATA=/data`, `TZ=Europe/Berlin` (in `compose.yaml`) |

A project file is a zip: `project.json` (name, date, notes, every profile's settings, the chart settings),
`readings/*.csv` (each profile's readings as imported) and `files/` (the original uploads). Opening a project uses
the stored readings, so it shows exactly what was saved even after a later import fix.

## First install (once)

1. In File Station, create the folder `docker/probe-2-plot`.
2. Put the repository's files in it (Code, Download ZIP on GitHub, unpack, upload the contents; the folder then
   holds `compose.yaml`, `Dockerfile`, `app.py`, ...).
3. Container Manager, Project, Create: name `probe-2-plot`, path `docker/probe-2-plot`, source *Use existing
   docker-compose.yml* (it reads `compose.yaml`), then Build. The first build downloads Python and takes a few minutes.
4. Open `http://<NAS IP>:8522`. The *Project* button in the toolbar now shows *Save to library* and the library list.
5. Hyper Backup: check that the backup task includes `docker/probe-2-plot` (it does if the whole `docker` folder is selected).

## Updating to a new version

Until the nightly auto-update (as for Bresaola, from a `stable` branch) is set up: replace the files in
`docker/probe-2-plot` with the new release (keep the `data` folder), then Container Manager, Project,
`probe-2-plot`, Action, Build. The library is not touched: it lives in `data/`, outside the image.

## Moving projects

- Cloud to NAS: on Cloud, *Save project file*; on the NAS, *Open a project file*, then *Save to library*.
- NAS to anywhere: open the project, *Save project file*.
- Restore a deleted project: move its file from `data/projects/deleted/` back to `data/projects/` and rename it to
  `<id>.p2p` (the 12 characters before the first `-`).
