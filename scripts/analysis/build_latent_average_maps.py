#!/usr/bin/env python3
"""
Build a private HTML view of average latent scores in two regional maps.

Outputs:
  data/review/static_latent_average_maps.html
  data/review/static_latent_country_averages_v0.json
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
IN_JSON = ROOT / "data" / "modeling" / "static_latent_scores_v0.json"
OUT_HTML = ROOT / "data" / "review" / "static_latent_average_maps.html"
OUT_JSON = ROOT / "data" / "review" / "static_latent_country_averages_v0.json"


COUNTRY_NAME_TO_ID = {
    "Brazil": 76,
    "Colombia": 170,
    "Mexico": 484,
    "Venezuela": 862,
    "Argentina": 32,
    "Peru": 604,
    "Chile": 152,
    "Ecuador": 218,
    "Bolivia": 68,
    "Honduras": 340,
    "Nicaragua": 558,
    "Guatemala": 320,
    "El Salvador": 222,
    "Paraguay": 600,
    "Uruguay": 858,
    "Cuba": 192,
    "Haiti": 332,
    "Dominican Republic": 214,
    "Panama": 591,
    "Costa Rica": 188,
    "Jamaica": 388,
    "Trinidad and Tobago": 780,
    "Guyana": 328,
    "Suriname": 740,
    "Belize": 84,
}


def average_by_country(rows: list[dict], field: str) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for row in rows:
        value = row.get(field)
        if value is None:
            continue
        buckets.setdefault(row["country"], []).append(float(value))
    return {country: round(sum(vals) / len(vals), 3) for country, vals in sorted(buckets.items())}


def build_payload() -> dict:
    payload = json.loads(IN_JSON.read_text(encoding="utf-8"))
    rows = payload["rows"]
    civilian = average_by_country(rows, "civilian_control_latent_v0_score")
    militarization = average_by_country(rows, "militarization_latent_v0_score")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(IN_JSON.relative_to(ROOT)),
        "country_name_to_id": COUNTRY_NAME_TO_ID,
        "civilian_control_latent_v0_avg": civilian,
        "militarization_latent_v0_avg": militarization,
    }


def build_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    template = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Static Latent Average Maps</title>
  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/topojson-client@3/dist/topojson-client.min.js"></script>
  <style>
    :root {{
      --eggshell:#F5F2ED;
      --eggshell-warm:#EDE8DF;
      --slate:#1C2B3A;
      --gold:#B8963E;
      --rule:#D8D0C4;
      --text:#1A1A18;
      --text-secondary:#5A6470;
      --serif:'Cormorant Garamond', Georgia, serif;
      --sans:'DM Sans', system-ui, sans-serif;
      --mono:'DM Mono', 'Courier New', monospace;
    }}
    html, body {{
      margin:0;
      background:linear-gradient(180deg, #f7f4ee 0%, #f2eee7 100%);
      color:var(--text);
      font-family:var(--sans);
    }}
    .page {{
      padding:24px;
      max-width:1600px;
      margin:0 auto;
    }}
    .header {{
      display:flex;
      justify-content:space-between;
      align-items:end;
      gap:24px;
      padding:18px 0 20px;
      border-bottom:1px solid var(--rule);
      margin-bottom:18px;
    }}
    .eyebrow {{
      font-family:var(--mono);
      font-size:11px;
      letter-spacing:.18em;
      text-transform:uppercase;
      color:var(--gold);
    }}
    h1 {{
      margin:8px 0 0;
      font-family:var(--serif);
      font-size:48px;
      font-weight:400;
      color:var(--slate);
    }}
    .meta {{
      font-family:var(--mono);
      font-size:11px;
      letter-spacing:.12em;
      text-transform:uppercase;
      color:var(--text-secondary);
      text-align:right;
    }}
    .grid {{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:18px;
    }}
    .lookup {{
      display:grid;
      grid-template-columns:minmax(280px, 520px) 1fr;
      gap:16px;
      align-items:start;
      margin-bottom:18px;
      padding:16px;
      background:rgba(255,255,255,.42);
      border:1px solid var(--rule);
      box-shadow:0 8px 26px rgba(28,43,58,.04);
    }}
    .lookup-title {{
      font-family:var(--mono);
      font-size:11px;
      letter-spacing:.16em;
      text-transform:uppercase;
      color:var(--text-secondary);
      margin-bottom:8px;
    }}
    .lookup-input {{
      width:100%;
      height:44px;
      border:1px solid var(--rule);
      background:#fffdfa;
      color:var(--slate);
      padding:0 14px;
      font-size:16px;
      font-family:var(--sans);
      outline:none;
    }}
    .lookup-input:focus {{
      border-color:var(--gold);
      box-shadow:0 0 0 3px rgba(184,150,62,.12);
    }}
    .lookup-help {{
      margin-top:8px;
      font-size:13px;
      color:var(--text-secondary);
    }}
    .lookup-result {{
      min-height:44px;
      display:flex;
      align-items:stretch;
      justify-content:flex-end;
      gap:12px;
      flex-wrap:wrap;
    }}
    .lookup-empty {{
      width:100%;
      min-height:44px;
      display:flex;
      align-items:center;
      justify-content:flex-end;
      color:var(--text-secondary);
      font-size:13px;
      text-align:right;
    }}
    .lookup-card {{
      min-width:200px;
      padding:10px 12px;
      border:1px solid var(--rule);
      background:#fffdfa;
    }}
    .lookup-card-name {{
      font-family:var(--serif);
      font-size:28px;
      color:var(--slate);
      line-height:1;
      margin-bottom:8px;
    }}
    .lookup-card-label {{
      font-family:var(--mono);
      font-size:10px;
      letter-spacing:.16em;
      text-transform:uppercase;
      color:var(--text-secondary);
      margin-bottom:4px;
    }}
    .lookup-card-score {{
      font-family:var(--mono);
      font-size:20px;
      color:var(--gold);
    }}
    .panel {{
      background:rgba(255,255,255,.46);
      border:1px solid var(--rule);
      box-shadow:0 8px 26px rgba(28,43,58,.05);
      padding:16px;
      min-height:760px;
      display:flex;
      flex-direction:column;
    }}
    .panel-label {{
      font-family:var(--mono);
      font-size:11px;
      letter-spacing:.18em;
      text-transform:uppercase;
      color:var(--text-secondary);
      margin-bottom:6px;
    }}
    .panel-title {{
      font-family:var(--serif);
      font-size:34px;
      line-height:1.05;
      color:var(--slate);
      margin-bottom:10px;
    }}
    .panel-note {{
      font-size:15px;
      line-height:1.7;
      color:var(--text-secondary);
      margin-bottom:14px;
      max-width:42rem;
    }}
    .map-wrap {{
      position:relative;
      flex:1 1 auto;
      min-height:540px;
      background:linear-gradient(180deg, rgba(255,255,255,.55), rgba(237,232,223,.62));
      border:1px solid var(--rule);
    }}
    .map-wrap svg {{
      width:100%;
      height:100%;
      display:block;
    }}
    .legend {{
      display:flex;
      justify-content:space-between;
      font-family:var(--mono);
      font-size:10px;
      letter-spacing:.12em;
      text-transform:uppercase;
      color:var(--text-secondary);
      margin-top:10px;
    }}
    .ranking {{
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:16px;
      margin-top:14px;
      padding-top:14px;
      border-top:1px solid var(--rule);
    }}
    .rank-block-title {{
      font-family:var(--mono);
      font-size:11px;
      letter-spacing:.16em;
      text-transform:uppercase;
      color:var(--text-secondary);
      margin-bottom:8px;
    }}
    .rank-row {{
      display:flex;
      justify-content:space-between;
      gap:14px;
      padding:5px 0;
      border-bottom:1px solid rgba(216,208,196,.45);
      font-size:14px;
    }}
    .rank-row:last-child {{
      border-bottom:none;
    }}
    .country {{
      color:var(--slate);
    }}
    .score {{
      font-family:var(--mono);
      color:var(--gold);
    }}
    .tooltip {{
      position:fixed;
      display:none;
      pointer-events:none;
      z-index:50;
      background:#fffdfa;
      border:1px solid var(--rule);
      box-shadow:0 12px 30px rgba(28,43,58,.12);
      padding:10px 12px;
      min-width:150px;
      font-size:13px;
      line-height:1.55;
      color:var(--text);
    }}
    .tooltip .name {{
      font-family:var(--serif);
      font-size:24px;
      color:var(--slate);
      line-height:1;
      margin-bottom:2px;
    }}
    .tooltip .value {{
      font-family:var(--mono);
      font-size:12px;
      letter-spacing:.1em;
      text-transform:uppercase;
      color:var(--gold);
    }}
    @media (max-width: 1100px) {{
      .lookup {{ grid-template-columns:1fr; }}
      .lookup-result {{ justify-content:flex-start; }}
      .lookup-empty {{ justify-content:flex-start; text-align:left; }}
      .grid {{ grid-template-columns:1fr; }}
      .panel {{ min-height:680px; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div>
        <div class="eyebrow">Private Latent Review</div>
        <h1>Average Static Latent Maps</h1>
      </div>
      <div class="meta">Generated __GENERATED_AT__<br>Source static_latent_scores_v0</div>
    </div>

    <section class="lookup">
      <div>
        <div class="lookup-title">Country Lookup</div>
        <input id="country-lookup" class="lookup-input" type="search" list="country-options" placeholder="Type a country name — Brazil, Argentina, Chile..." autocomplete="off">
        <datalist id="country-options"></datalist>
        <div class="lookup-help">Search any country with latent coverage to see both average scores instantly.</div>
      </div>
      <div class="lookup-result" id="lookup-result"></div>
    </section>

    <div class="grid">
      <section class="panel">
        <div class="panel-label">Construct</div>
        <div class="panel-title">Civilian Control</div>
        <div class="panel-note">Country averages of the first private static civilian-control latent score. Higher values indicate stronger civilian control in the current `v0` construct.</div>
        <div class="map-wrap"><svg id="cc-map"></svg></div>
        <div class="legend"><span>Lower Civilian Control</span><span>Higher Civilian Control</span></div>
        <div class="ranking" id="cc-ranking"></div>
      </section>

      <section class="panel">
        <div class="panel-label">Construct</div>
        <div class="panel-title">Militarization</div>
        <div class="panel-note">Country averages of the first private static militarization latent score. Higher values indicate stronger militarization in the current `v0` construct.</div>
        <div class="map-wrap"><svg id="mil-map"></svg></div>
        <div class="legend"><span>Lower Militarization</span><span>Higher Militarization</span></div>
        <div class="ranking" id="mil-ranking"></div>
      </section>
    </div>
  </div>

  <div class="tooltip" id="tooltip"></div>

  <script id="latent-payload" type="application/json">__PAYLOAD_JSON__</script>
  <script>
    const payload = JSON.parse(document.getElementById('latent-payload').textContent);
    const LATAM_IDS = new Set(Object.values(payload.country_name_to_id));
    const COUNTRY_NAMES_MAP = Object.fromEntries(Object.entries(payload.country_name_to_id).map(([name,id]) => [String(id), name]));
    const tooltip = document.getElementById('tooltip');
    const allCountries = Array.from(new Set([
      ...Object.keys(payload.civilian_control_latent_v0_avg),
      ...Object.keys(payload.militarization_latent_v0_avg)
    ])).sort((a,b) => a.localeCompare(b));

    function showTooltip(evt, name, value, label) {{
      tooltip.innerHTML = `<div class="name">${{name}}</div><div class="value">${{label}}</div><div style="margin-top:4px">${{value.toFixed(2)}} / 100</div>`;
      tooltip.style.display = 'block';
      tooltip.style.left = (evt.clientX + 16) + 'px';
      tooltip.style.top = (evt.clientY - 14) + 'px';
    }}
    function hideTooltip() {{
      tooltip.style.display = 'none';
    }}

    function renderRanking(targetId, values, descending=true) {{
      const entries = Object.entries(values).sort((a,b) => descending ? b[1]-a[1] : a[1]-b[1]);
      const top = entries.slice(0,5);
      const bottom = entries.slice(-5);
      document.getElementById(targetId).innerHTML = `
        <div>
          <div class="rank-block-title">Highest</div>
          ${top.map(([name,score]) => `<div class="rank-row"><span class="country">${{name}}</span><span class="score">${{score.toFixed(2)}}</span></div>`).join('')}
        </div>
        <div>
          <div class="rank-block-title">Lowest</div>
          ${bottom.map(([name,score]) => `<div class="rank-row"><span class="country">${{name}}</span><span class="score">${{score.toFixed(2)}}</span></div>`).join('')}
        </div>`;
    }}

    function renderLookupResult(query='') {{
      const target = document.getElementById('lookup-result');
      const normalized = query.trim().toLowerCase();
      if(!normalized) {{
        target.innerHTML = `<div class="lookup-empty">Type a country name to retrieve both average latent scores.</div>`;
        return;
      }}
      const match = allCountries.find(name => name.toLowerCase() === normalized)
        || allCountries.find(name => name.toLowerCase().includes(normalized));
      if(!match) {{
        target.innerHTML = `<div class="lookup-empty">No country with latent coverage matches “${{query}}”.</div>`;
        return;
      }}
      const cc = payload.civilian_control_latent_v0_avg[match];
      const mil = payload.militarization_latent_v0_avg[match];
      target.innerHTML = `
        <div class="lookup-card">
          <div class="lookup-card-name">${{match}}</div>
          <div class="lookup-card-label">Civilian Control</div>
          <div class="lookup-card-score">${{cc == null ? 'No score' : `${{cc.toFixed(2)}} / 100`}}</div>
        </div>
        <div class="lookup-card">
          <div class="lookup-card-name">${{match}}</div>
          <div class="lookup-card-label">Militarization</div>
          <div class="lookup-card-score">${{mil == null ? 'No score' : `${{mil.toFixed(2)}} / 100`}}</div>
        </div>`;
    }}

    function drawMap(svgId, values, label, palette) {{
      const svgEl = document.getElementById(svgId);
      const w = svgEl.clientWidth || 700;
      const h = svgEl.clientHeight || 560;
      const svg = d3.select(svgEl).attr('viewBox', `0 0 ${{w}} ${{h}}`);
      svg.selectAll('*').remove();

      d3.json('https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json').then(world => {{
        const worldFeatures = topojson.feature(world, world.objects.countries).features;
        const latamFeat = worldFeatures.filter(f => LATAM_IDS.has(+f.id));
        const projection = d3.geoMercator().fitExtent([[24,24],[w-24,h-24]], {{
          type:'FeatureCollection',
          features:latamFeat
        }});
        const path = d3.geoPath().projection(projection);

        const scores = Object.values(values);
        const min = d3.min(scores);
        const max = d3.max(scores);
        const color = d3.scaleLinear().domain([min, (min + max) / 2, max]).range(palette);

        svg.append('g')
          .selectAll('path')
          .data(latamFeat)
          .enter()
          .append('path')
          .attr('d', path)
          .attr('fill', d => {{
            const name = COUNTRY_NAMES_MAP[String(d.id)];
            const score = values[name];
            return score == null ? '#ebe5dc' : color(score);
          }})
          .attr('stroke', '#b8b2a4')
          .attr('stroke-width', 0.9)
          .on('mousemove', function(evt, d) {{
            const name = COUNTRY_NAMES_MAP[String(d.id)];
            const score = values[name];
            if(score == null) {{
              hideTooltip();
              return;
            }}
            showTooltip(evt, name, score, label);
          }})
          .on('mouseleave', hideTooltip);

        svg.append('g')
          .attr('pointer-events', 'none')
          .selectAll('text')
          .data(latamFeat.filter(d => values[COUNTRY_NAMES_MAP[String(d.id)]] != null))
          .enter()
          .append('text')
          .attr('x', d => path.centroid(d)[0])
          .attr('y', d => path.centroid(d)[1])
          .attr('text-anchor', 'middle')
          .attr('font-family', 'DM Sans, system-ui, sans-serif')
          .attr('font-size', 10)
          .attr('fill', '#3d4753')
          .text(d => COUNTRY_NAMES_MAP[String(d.id)]);
      }});
    }}

    renderRanking('cc-ranking', payload.civilian_control_latent_v0_avg);
    renderRanking('mil-ranking', payload.militarization_latent_v0_avg);
    document.getElementById('country-options').innerHTML = allCountries.map(name => `<option value="${{name}}"></option>`).join('');
    const lookup = document.getElementById('country-lookup');
    lookup.addEventListener('input', evt => renderLookupResult(evt.target.value));
    renderLookupResult('Brazil');
    drawMap('cc-map', payload.civilian_control_latent_v0_avg, 'Civilian Control', ['#efe6cf','#b9c287','#5f7a2d']);
    drawMap('mil-map', payload.militarization_latent_v0_avg, 'Militarization', ['#f1eadf','#d39c6c','#7d3f2e']);
  </script>
</body>
</html>
"""
    return (
        template.replace("{{", "{")
        .replace("}}", "}")
        .replace("__PAYLOAD_JSON__", data_json)
        .replace("__GENERATED_AT__", payload["generated_at"])
    )


def main() -> None:
    payload = build_payload()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_HTML.write_text(build_html(payload), encoding="utf-8")
    print(f"Wrote country averages JSON to {OUT_JSON}")
    print(f"Wrote latent average maps HTML to {OUT_HTML}")


if __name__ == "__main__":
    main()
