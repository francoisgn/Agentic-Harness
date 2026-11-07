---
id: <identifiant court, ex. dora>
référentiel: <texte officiel et version, ex. Règlement (UE) 2022/2554 (DORA)>
confirme: <qui tranche : DPO, RSSI, QSA, auditeur>
version-spec: 1
---
# <Nom du référentiel> : spec de revue

Spec lue par le relecteur générique `compliance-reviewer` (cadre agentic-harness, COMPLIANCE.md §2). Le projet
l'écrit, la tient à jour et la déclare dans `.harness/config.json` :
`{"id": "<id>", "spec": "docs/compliance/<id>.md", "paths": ["…"], "keywords": ["…"]}`.
Rien de deviné : un identifiant d'exigence non vérifié sur le texte officiel porte « (à vérifier) ».

## Quand intervenir
- Chemins, mots-clés, types de données qui font entrer un diff dans le périmètre.

## Ce que je vérifie
1. <Ce qui se vérifie dans le code, la configuration, la CI ou les docs> — <exigence, n°> (<source>)
2. …

## Preuves attendues
- Artefacts qui doivent exister dans le dépôt (registre, analyse d'impact, ADR, SBOM, politique…).

## Sources
- <URL officielle> (consultée le <AAAA-MM-JJ>)
