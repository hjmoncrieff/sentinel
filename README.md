# SENTINEL — LatAm Civil-Military Monitor

A quasi-automated dashboard that monitors civil-military events in Latin America.  
Nightly GitHub Actions pipeline → RSS + ACLED → Claude classification → `data/events.json` → dashboard.

---

## Repository structure

```
sentinel/
├── .github/workflows/fetch_events.yml   ← nightly GitHub Action
├── scripts/fetch_events.py              ← Python pipeline
├── data/events.json                     ← auto-updated event store
└── index.html                           ← dashboard (reads events.json)
```
