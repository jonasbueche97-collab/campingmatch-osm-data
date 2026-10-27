# Garda OSM ground data
Only public OSM ground data and its standalone extraction recipe belong here. No CampingMatch application, private state, profiles or credentials.

Data license: ODbL 1.0, © OpenStreetMap contributors. https://www.openstreetmap.org/copyright
Derived data from https://download.geofabrik.de under ODbL. Keep provenance manifests and provide the database under the same license when redistributing. Coordinates are polygon bounding-box centers, not verified entrances. Camping operation, opening and reviews are not verified by OSM.

The workflow deliberately refuses private repositories. Standard ubuntu-24.04 runner minutes in public repositories are free under GitHub's current policy. No larger runner, Actions cache, Actions artifact, package publishing, LFS, custom image or paid API is used. Runtime maximum 30 minutes. Source downloads maximum 750 MB each; output maximum 250 records/1.5 MB. Changing these resource choices requires another cost review. No guaranteed SLA: scheduled runs may be delayed or dropped. This is a prepared workflow, not proof it ran.

Manual run: install Python 3.12+, `python -m pip install -r requirements.txt`, then `python extract.py OUTPUT_DIRECTORY`.

This repository provides data. It has no private Site credential and cannot by itself import into a private Site. Secure synchronization must be configured and tested separately. A green extraction run does not prove private Site persistence.

## Verified execution

GitHub Actions run https://github.com/jonasbueche97-collab/campingmatch-osm-data/actions/runs/40471503372 succeeded on 2026-10-27. Both regional PBF files were downloaded and 157 Garda OSM objects extracted; the data SHA-256 is 3adba690824c418b43f13f95235c3e4f59bf558fabb0faf3b9cb47b36e32ad71. This push-triggered execution validates the workflow; the first scheduled recurrence is a separate future event. Read data/manifest.json for source timestamps and license.
