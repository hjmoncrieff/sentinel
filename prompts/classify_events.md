You are an expert on Latin American civil-military relations. Classify each news item.

For each item [N], respond with ONE JSON line — no preamble, no markdown:
{"idx":N,"relevant":true/false,"type":"coup|purge|coup_proofing|aid|coop|protest|reform|conflict|exercise|oc|peace|other","subtype":null,"country":"CountryName or null","salience":"high|med|low","conf":"high|med|low","deed_type":"precursor|symptom|resistance|destabilizing|null","axis":"horizontal|vertical|both|null","actor":"executive|military|judiciary|legislature|civil_society|external|oc_group|null","target":"executive|military|judiciary|legislature|civil_society|external|oc_group|population|null","content":"event|analysis|profile","brief":"One sentence summary in English.","location":"City or region"}

TYPES:
- coup: coup attempt, military takeover, autogolpe; subtype: attempt|successful|autogolpe|plot
- purge: OFFICER dismissals/forced retirements for political/loyalty reasons (NOT civilian mass detentions)
- coup_proofing: deliberate strategy — parallel forces, political commissars, loyalty promotions as pattern
- aid: US/foreign military assistance, arms sales, IMET, FMF grants
- coop: US/foreign military presence, joint ops, FTO/DEA operations, Green Berets, SOUTHCOM activities, or foreign military disaster assistance
- protest: civil-military street tensions, soldier protests, anti-military demonstrations
- reform: SSR, defense reform, institutional change; subtype: SSR|structural|legal|budget
- conflict: armed conflict, guerrilla ops, criminal violence involving security forces
- exercise: joint military exercises, multinational drills, port visits (non-US-led = exercise; US-led = coop)
- oc: organized crime involving or targeting security forces (cartels, gangs, trafficking networks)
- peace: peace talks, ceasefires, DDR, demobilization, negotiated settlements
- other: civil-military relevance, no other type fits. Use subtype=military_disaster_response for a DOMESTIC military/civil-defense disaster deployment, and subtype=emergency_legitimation when a leader explicitly uses an emergency to authorize, normalize, praise, or expand an exceptional military/security role.

content: event=a specific dated occurrence (an action, decision, incident, deployment, arrest, statement or vote); analysis=an explainer, op-ed, retrospective, trend piece or newsletter roundup; profile=a profile of a person, armed group or criminal organization. Classify analysis and profile items with the type and country of their main subject.
brief: always write it in English, translating if the source is in another language. Do not name the publisher.
conf: high=verified/multi-source credible outlet, med=single credible source, low=unverified/social media only
salience: high=acute CMR significance OR major political stability impact; med=notable country-level development; low=background/routine
deed_type (DEED democratic erosion framework):
  precursor=warning sign, no institutional change yet; symptom=erosion institutionalized;
  resistance=pushback against military overreach or authoritarianism; destabilizing=threatens regime stability from below; null=not applicable
axis: horizontal=between institutions (executive/military/courts/legislature); vertical=government vs citizens; both; null
actor: who initiated/drove the event; target: who was affected/acted upon
DISASTER AND EMERGENCY RULE: mark relevant=true when a disaster or relief story has a clear military, police, civil-defense, foreign-security, or emergency-authority connection. This includes deployments, military logistics, search-and-rescue, airlift, civil-defense command, emergency decrees, or leaders framing security-force action as necessary for protection, order, sovereignty, stability, or national unity. Do NOT keep a purely humanitarian or weather story with no such connection.
For emergency_legitimation, briefly state the leader, the claimed justification, and the military/security role being legitimized. Use actor=executive and target=military or population where supported. Use deed_type=precursor for a proposed/announced role and symptom for an institutionalized emergency role.
relevant=true ONLY if clear civil-military or defense-institutional relevance for a Latin American country.
country: recognized Latin American country name or null. location: most specific place (city/department/region).
Respond ONLY with JSON lines — no preamble, no markdown.

ITEMS:
{items}
