"""
Curated RSS and RSS-like feed definitions for SENTINEL.

Notes:
- Native RSS is preferred when stable and known.
- Google News RSS is used for site-scoped monitoring when a clean native feed
  is unavailable or category-specific coverage is needed.
- Several sources below use Google News intentionally because direct RSS
  endpoints were dead, blocked, or unstable in live pipeline tests.
"""


def gnews_site_feed(site: str, terms: str, lang: str = "es-419", gl: str = "US", ceid: str = "US:es-419") -> str:
    query = f"site:{site}+({terms})"
    return f"https://news.google.com/rss/search?q={query}&hl={lang}&gl={gl}&ceid={ceid}"


RSS_FEEDS = [
    # English specialist / regional analysis
    {
        "name": "InSight Crime",
        "url": "https://insightcrime.org/feed/",
        "category": "investigative_security",
        "countries": ["Regional"],
    },
    {
        "name": "Americas Quarterly",
        "url": "https://americasquarterly.org/feed/",
        "category": "policy_analysis",
        "countries": ["Regional"],
    },
    {
        "name": "The Guardian LatAm",
        "url": "https://www.theguardian.com/world/americas/rss",
        "category": "general_news",
        "countries": ["Regional"],
    },
    {
        "name": "Crisis Group",
        "url": "https://www.crisisgroup.org/rss",
        "category": "conflict_analysis",
        "countries": ["Regional"],
    },

    # English wire / broadcast
    {
        "name": "AP LatAm",
        "url": gnews_site_feed("apnews.com", "latin+america+OR+military+OR+security+OR+coup+OR+protest+OR+organized+crime"),
        "category": "wire",
        "countries": ["Regional"],
    },
    {
        "name": "AFP LatAm",
        "url": gnews_site_feed("afp.com", "latin+america+OR+military+OR+security+OR+coup+OR+protest+OR+organized+crime"),
        "category": "wire",
        "countries": ["Regional"],
    },
    {
        "name": "Reuters LatAm",
        "url": gnews_site_feed("reuters.com", "latin+america+OR+military+OR+security+OR+coup+OR+protest"),
        "category": "wire",
        "countries": ["Regional"],
    },
    {
        "name": "BBC Americas",
        "url": "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml",
        "category": "general_news",
        "countries": ["Regional"],
    },
    {
        "name": "NYT World",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "category": "general_news",
        "countries": ["Regional"],
    },

    # Official / institutional
    {
        "name": "SOUTHCOM",
        "url": gnews_site_feed("southcom.mil", "exercise+OR+cooperation+OR+operation+OR+security+OR+partner"),
        "category": "official",
        "countries": ["Regional"],
    },

    # Academic / policy
    {
        "name": "NACLA",
        "url": gnews_site_feed("nacla.org", "security+OR+military+OR+police+OR+authoritarianism+OR+organized+crime"),
        "category": "policy_analysis",
        "countries": ["Regional"],
    },
    {
        "name": "Wilson Center LatAm",
        "url": gnews_site_feed("wilsoncenter.org", "latin+america+security+OR+organized+crime+OR+military+OR+democracy"),
        "category": "policy_analysis",
        "countries": ["Regional"],
    },

    # Spanish-language regional
    {
        "name": "EFE",
        "url": gnews_site_feed("efe.com", "latinoamerica+OR+defensa+OR+seguridad+OR+golpe+OR+protesta+OR+crimen+organizado"),
        "category": "wire",
        "countries": ["Regional"],
    },
    {
        "name": "Notimérica",
        "url": gnews_site_feed("notimerica.com", "latinoamerica+OR+seguridad+OR+defensa+OR+presidente+OR+crimen+organizado"),
        "category": "general_news",
        "countries": ["Regional"],
    },
    {
        "name": "Prensa Latina",
        "url": gnews_site_feed("plenglish.com", "latin+america+OR+security+OR+military+OR+defense+OR+organized+crime"),
        "category": "perspective_monitor",
        "countries": ["Regional"],
    },
    {
        "name": "BBC Mundo",
        "url": "https://feeds.bbci.co.uk/mundo/rss.xml",
        "category": "general_news",
        "countries": ["Regional"],
    },
    {
        "name": "El País América",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada",
        "category": "general_news",
        "countries": ["Regional"],
    },
    {
        "name": "La Nación Argentina",
        "url": gnews_site_feed("lanacion.com.ar", "militar+OR+seguridad+OR+defensa+OR+protesta+OR+gendarmeria"),
        "category": "general_news",
        "countries": ["Argentina"],
    },
    {
        "name": "Folha de S.Paulo",
        "url": "https://feeds.folha.uol.com.br/poder/rss091.xml",
        "category": "general_news",
        "countries": ["Brazil"],
    },
    {
        "name": "Agência Brasil",
        "url": gnews_site_feed("agenciabrasil.ebc.com.br", "defesa+OR+seguranca+OR+segurança+OR+militar+OR+crime+organizado"),
        "category": "official_public_media",
        "countries": ["Brazil"],
    },
    # Defense / security specialist
    {
        "name": "Infodefensa",
        "url": gnews_site_feed("infodefensa.com", "defensa+OR+seguridad+OR+ejercito+OR+fuerza+aerea+OR+armada"),
        "category": "defense_specialist",
        "countries": ["Regional"],
    },
    {
        "name": "Zona Militar",
        "url": gnews_site_feed("zona-militar.com", "defensa+OR+seguridad+OR+ejercito+OR+armada+OR+fuerza+aerea"),
        "category": "defense_specialist",
        "countries": ["Regional"],
    },
    # Colombia
    {
        "name": "El Tiempo Colombia",
        "url": "https://www.eltiempo.com/rss/politica.xml",
        "category": "general_news",
        "countries": ["Colombia"],
    },
    {
        "name": "Semana Colombia",
        "url": gnews_site_feed("semana.com", "militar+OR+seguridad+OR+ejercito+OR+eln+OR+farc"),
        "category": "general_news",
        "countries": ["Colombia"],
    },
    {
        "name": "VerdadAbierta",
        "url": gnews_site_feed("verdadabierta.com", "ejercito+OR+eln+OR+farc+OR+paz+OR+seguridad"),
        "category": "investigative_security",
        "countries": ["Colombia"],
    },

    # Mexico
    {
        "name": "Animal Político Seguridad",
        "url": gnews_site_feed("animalpolitico.com", "seguridad+OR+militar+OR+ejercito+OR+guardia+nacional+OR+cartel"),
        "category": "investigative_security",
        "countries": ["Mexico"],
    },
    {
        "name": "Zeta Tijuana",
        "url": gnews_site_feed("zetatijuana.com", "seguridad+OR+militar+OR+cartel+OR+ejercito+OR+guardia+nacional"),
        "category": "investigative_security",
        "countries": ["Mexico"],
    },

    # Venezuela
    {
        "name": "El Nacional Venezuela",
        "url": "https://www.elnacional.com/feed/",
        "category": "general_news",
        "countries": ["Venezuela"],
    },
    {
        "name": "Runrun.es",
        "url": gnews_site_feed("runrun.es", "militar+OR+fuerza+armada+OR+seguridad+OR+represion+OR+padrino"),
        "category": "investigative_security",
        "countries": ["Venezuela"],
    },
    {
        "name": "Efecto Cocuyo",
        "url": gnews_site_feed("efectococuyo.com", "militar+OR+fuerza+armada+OR+seguridad+OR+represion+OR+padrino"),
        "category": "investigative_security",
        "countries": ["Venezuela"],
    },

    # El Salvador / Central America
    {
        "name": "El Faro",
        "url": gnews_site_feed("elfaro.net", "bukele+OR+seguridad+OR+militar+OR+pandillas+OR+derechos+humanos"),
        "category": "investigative_security",
        "countries": ["El Salvador"],
    },

    # Human rights monitoring
    {
        "name": "Human Rights Watch",
        "url": gnews_site_feed("hrw.org", "Latin+America+OR+Colombia+OR+Mexico+OR+Venezuela+OR+El+Salvador+military+OR+police+OR+abuse"),
        "category": "human_rights_monitor",
        "countries": ["Regional"],
    },
    {
        "name": "Amnesty International",
        "url": gnews_site_feed("amnesty.org", "Latin+America+OR+Colombia+OR+Mexico+OR+Venezuela+OR+El+Salvador+military+OR+police+OR+abuse"),
        "category": "human_rights_monitor",
        "countries": ["Regional"],
    },

    # Official defense / security monitoring
    {
        "name": "Argentina Defensa",
        "url": gnews_site_feed("argentina.gob.ar", "\"ministerio+de+defensa\"+OR+ejercito+OR+armada+OR+fuerza+aerea+OR+operativo"),
        "category": "official",
        "countries": ["Argentina"],
    },
    {
        "name": "Colombia Mindefensa",
        "url": gnews_site_feed("mindefensa.gov.co", "ejercito+OR+policia+OR+defensa+OR+operacion+OR+seguridad"),
        "category": "official",
        "countries": ["Colombia"],
    },
    {
        "name": "Mexico SEDENA",
        "url": gnews_site_feed("gob.mx", "sedena+OR+ejercito+OR+guardia+nacional+OR+seguridad+OR+operativo+OR+defensa"),
        "category": "official",
        "countries": ["Mexico"],
    },
    {
        "name": "Uruguay Defensa",
        "url": gnews_site_feed("gub.uy", "\"ministerio+de+defensa+nacional\"+OR+defensa+OR+ejercito+OR+armada+OR+fuerza+aerea"),
        "category": "official",
        "countries": ["Uruguay"],
    },
    {
        "name": "Honduras SEDENA",
        "url": gnews_site_feed("sedena.gob.hn", "defensa+OR+fuerzas+armadas+OR+seguridad+OR+operacion"),
        "category": "official",
        "countries": ["Honduras"],
    },
    {
        "name": "Dominican Republic MIDE",
        "url": gnews_site_feed("mide.gob.do", "defensa+OR+fuerzas+armadas+OR+seguridad+OR+operativo"),
        "category": "official",
        "countries": ["Dominican Republic"],
    },
    {
        "name": "Peru MINDEF",
        "url": gnews_site_feed("gob.pe", "mindef+OR+defensa+OR+ejercito+OR+armada+OR+fuerza+aerea"),
        "category": "official",
        "countries": ["Peru"],
    },
    {
        "name": "Guatemala MINDEF",
        "url": gnews_site_feed("guatemala.gob.gt", "mindef+OR+defensa+OR+ejercito+OR+fuerza+aerea+OR+operativo"),
        "category": "official",
        "countries": ["Guatemala"],
    },
    {
        "name": "Bolivia Defensa",
        "url": gnews_site_feed("mindef.gob.bo", "defensa+OR+fuerzas+armadas+OR+seguridad+OR+operativo"),
        "category": "official",
        "countries": ["Bolivia"],
    },
]
