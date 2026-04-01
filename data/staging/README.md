# Staging Layer

This directory is reserved for machine-generated intermediate artifacts that sit between ingestion and canonical event assembly.

Current examples:

- `raw_articles.json`
- `filtered_articles.json`
- `event_article_links.json`

These files capture article-level pipeline state before canonical assembly so
provenance can trace clustered events back to specific reports.

Do not treat this directory as analyst-reviewed or publication-ready.
