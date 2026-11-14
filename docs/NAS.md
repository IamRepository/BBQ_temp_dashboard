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

**By hand:** replace the files in `docker/probe-2-plot` with the new release (keep the `data` folder), then
Container Manager, Project, `probe-2-plot`, Action, Build. The library is not touched: it lives in `data/`,
outside the image.

**Automatically (from v1.9.1), as for Bresaola:** the NAS checks the `stable` branch on GitHub every night and
updates itself. `stable` only moves when a release has passed the tests and the owner has said OK
(`git push origin main:stable`), so the NAS never runs an unchecked `main`. The repository is public, so the NAS
needs no key or password.

One-time setup:
1. Put `scripts/nas-update.sh` in `docker/probe-2-plot/scripts/` (File Station, create the folder `scripts`, upload the file).
2. Task Scheduler, Create, Scheduled Task, User-defined script: name `probe-2-plot-update`, user **root**, daily at
   **04:05** (Bresaola updates at 04:00, so the two never build at the same time), script:

        sh /volume1/docker/probe-2-plot/scripts/nas-update.sh

   If your shared folder `docker` isn't on volume1, use the path shown in File Station (right-click the folder,
   Properties, Location). Task Settings: tick **Send run details by email** and **only when the script
   terminates abnormally**.
3. Select the task, **Run** once. The first run turns the folder into a git checkout and rebuilds once.
   `docker/probe-2-plot/update.log` should end with `OK: <version> is running`; a second Run says `up to date`.

What a run does: asks GitHub for the newest commit on `stable`; if there is nothing new it stops. Otherwise it
copies the library to `data/pre-update/projects-<date>` (keeps the last 5), checks out the new files, rebuilds
and restarts, then checks that the web server answers and that the container reports the new version and can
read the library. If that fails it goes back to the previous version (its image is kept), remembers the bad
commit so it isn't retried every night, and exits with an error so DSM mails you.

A failure that was only passing (no internet during the build, say): delete `update.failed` and Run the task
again. Stopping it: untick "Enabled" on the task. Local edits to `compose.yaml` are replaced by an update; a copy
of the old one is kept in `data/pre-update/`.

## Moving projects

- Cloud to NAS: on Cloud, *Save project file*; on the NAS, *Open a project file*, then *Save to library*.
- NAS to anywhere: open the project, *Save project file*.
- Restore a deleted project: move its file from `data/projects/deleted/` back to `data/projects/` and rename it to
  `<id>.p2p` (the 12 characters before the first `-`).
