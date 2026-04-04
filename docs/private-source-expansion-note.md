# Private Source Expansion Note

## Purpose

This note records the next useful expansion path for SENTINEL's source layer:

- regional wire and agency coverage
- official Latin American defense-ministry websites

The goal is not to ingest everything equally. The goal is to widen discovery
while preserving clear source weighting.

## Recommended Regional Agency Layer

### Tier 1 regional wire backbone

- `EFE`
  - broad and fast regional political coverage
  - especially useful for executive, military, diplomatic, and crisis stories
  - official site: `https://efe.com/`

- `AFP` Spanish / LatAm-facing output
  - should be treated as a core wire when accessible through the current source mix
  - official site: `https://www.afp.com/`

### Tier 2 regional discovery layer

- `Notimérica`
  - useful for Ibero-American regional monitoring and cross-border developments
  - official site: `https://www.notimerica.com/`

- `Agência Brasil`
  - especially useful for Brazil
  - good supplement for state policy, public-security, and defense governance
  - official site: `https://agenciabrasil.ebc.com.br/`

### Tier 3 perspective / regime-line monitoring

- `Prensa Latina`
  - useful for Cuba, ALBA, Nicaragua, and Venezuela official-line or
    regime-adjacent narratives
  - should be treated as monitored perspective coverage, not neutral baseline
  - official site: `https://www.plenglish.com/`

## Recommended Weighting

- Tier 1
  - Reuters
  - AP
  - AFP
  - EFE

- Tier 2
  - Notimérica
  - Agência Brasil

- Tier 3 / perspective-only
  - Prensa Latina

## Official Defense-Ministry Sites

These are useful as:

- official announcements
- force posture and command changes
- procurement or cooperation signaling
- doctrine, missions, and policy framing

But they are not equally suitable for clean feed ingestion.

### Confirmed useful official sites

- Argentina
  - Ministry of Defense: `https://www.argentina.gob.ar/defensa`
  - this appears usable for direct article/news discovery

- Colombia
  - Ministry of Defense: `https://www.mindefensa.gov.co/`
  - official site is present, but much of the accessible indexed content appears
    JS-heavy or nested in institutional sub-sites

- Mexico
  - SEDENA institutional presence: `https://www.gob.mx/sedena`
  - broader defense web presence is also tied to `sedena.gob.mx`

### Expanded LatAm ministry set

- Bolivia
  - Ministry of Defense: `https://www.mindef.gob.bo/mindef/`
  - broader state directory path: `https://www.gob.bo/entidad/254`

- Dominican Republic
  - Ministry of Defense: `https://mide.gob.do/`

- Guatemala
  - Ministry of Defense: `https://guatemala.gob.gt/mindef/`

- Honduras
  - Secretariat of Defense: `https://www.sedena.gob.hn/`

- Peru
  - Ministry of Defense: `https://www.gob.pe/mindef`
  - legacy/domain family reference: `mindef.gob.pe`

- Uruguay
  - Ministry of National Defense: `https://www.gub.uy/ministerio-defensa-nacional/`

### Structural special cases

- Costa Rica
  - no classical defense ministry because there is no standing army
  - use public-security and executive-security institutions instead

- Panama
  - public-security structure is more relevant than a classical defense-ministry
    model
  - use Ministry of Public Security and related official institutions instead

- El Salvador
  - Ministry of National Defense remains relevant, but the public discovery path
    still needs verification before treating it as a live ingest source

- Ecuador
  - Ministry of Defense remains relevant, but the public discovery path still
    needs verification before treating it as a live ingest source

## Operational Judgment

### Best immediate additions

- `EFE`
- `Agência Brasil`
- `Notimérica`

### Best official-defense additions

- Argentina Ministry of Defense
- Mexico `gob.mx/sedena`
- Colombia Ministry of Defense, but likely through targeted scraping of public
  announcements rather than naive homepage ingestion
- Uruguay Ministry of National Defense
- Honduras Secretariat of Defense
- Dominican Republic Ministry of Defense

## Technical Note

My current inference is:

- regional agencies are more promising for near-term ingestion than most
  defense-ministry sites
- many ministry sites are better treated as:
  - targeted monitored sources
  - page-specific scrapers
  - or periodic manual/AI-assisted review sources
  rather than generic RSS inputs

That means the next clean implementation path is:

1. add or test `EFE`
2. add or test `Agência Brasil`
3. add or test `Notimérica`
4. map the public news/press-release sections for Argentina, Mexico, and
   Colombia defense ministries before building scrapers

## Source Implementation Plan

### Priority 1: easiest regional additions

- `EFE`
  - role: Tier 1 regional wire
  - implementation path: test direct feed if available; otherwise use
    Google News site-scoped RSS
  - expected output: faster executive, crisis, diplomatic, and military-event
    discovery

- `Agência Brasil`
  - role: Brazil official/public-interest supplement
  - implementation path: direct feed if stable; otherwise Google News
  - expected output: stronger Brazil state-policy and security-governance
    coverage

- `Notimérica`
  - role: regional discovery layer
  - implementation path: likely Google News site-scoped RSS first
  - expected output: more Ibero-American cross-border and regional-political
    awareness

### Priority 2: official-defense monitored layer

- Argentina Ministry of Defense
  - mode: targeted official-source monitor
  - implementation preference: page/news-section scrape or RSS if present

- Mexico `gob.mx/sedena`
  - mode: targeted official-source monitor
  - implementation preference: public news/press-release scrape

- Colombia Ministry of Defense
  - mode: targeted official-source monitor
  - implementation preference: page/news-section scrape, not homepage polling

- Uruguay Ministry of National Defense
  - mode: targeted official-source monitor
  - implementation preference: direct news-page scrape or RSS if present

- Honduras Secretariat of Defense
  - mode: targeted official-source monitor
  - implementation preference: direct news-page scrape or RSS if present

- Dominican Republic Ministry of Defense
  - mode: targeted official-source monitor
  - implementation preference: direct news-page scrape or RSS if present

### Priority 3: expanded official-defense watchlist

- Guatemala Ministry of Defense
  - mode: monitored source first
  - implementation preference: verify public news architecture before scraper

- Bolivia Ministry of Defense
  - mode: monitored source first
  - implementation preference: verify stable public content path before scraper

- Peru Ministry of Defense
  - mode: monitored source first
  - implementation preference: use `gob.pe` public path rather than legacy
    domain if possible

- Ecuador Ministry of Defense
  - mode: verify first
  - implementation preference: only promote after public news path is clear

- El Salvador Ministry of National Defense
  - mode: verify first
  - implementation preference: only promote after public news path is clear

## Working Rule

For this layer, the implementation sequence should be:

1. regional agency expansion first
2. targeted official-defense monitors second
3. only then broader ministry expansion

That preserves source quality while still expanding the discovery surface.
