# LOT-XXX — <nom court>

- **Module / couche :** <moteur | app | outillage | docs>
- **Modèle :** <auteur> → <relecteur> (jamais le même ; label `modèle:` de l'issue)
- **Taille :** S | M | L (L = à découper avant de commencer)
- **Issue :** #…  ·  **Dépend de :** #… (ou —)

## Résumé
Une user story ou deux lignes : ce que le lot apporte et pourquoi maintenant.

## Sources
Chaque fait externe (règle, API, protocole, comportement de référence) avec sa source : lien officiel, `fichier:ligne`
à un commit nommé, capture. Rien de deviné : ce qui manque est listé dans « En attente » ci-dessous.

## Comportement
Entrées, sorties, règles. Cas limites (vide, très gros, erreurs, annulation, concurrence).

## Différences voulues
Écarts assumés avec la référence (ancien comportement, ancienne version), chacun justifié.

## Données et compatibilité
Champs persistés ajoutés ou renommés : optionnels ou par défaut, décodage tolérant, migration à la lecture
(CONVENTIONS.md §Persistance). « Aucun » sinon.

## Tests
Les tests qui prouvent le lot, chacun vu en échec sans le changement. Ce qui ne se teste qu'à la main (et où).

## En attente
Captures, décisions (`à clarifier`), accès manquants : chacun avec son issue.

## Leçons
À reporter dans LESSONS (méthode) ou dans les notes du projet (faits du domaine) à la clôture.
