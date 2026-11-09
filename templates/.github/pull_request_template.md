<!-- Titre dans le style des PR précédentes. PR ouverte en brouillon dès le premier push, poussée souvent ; « Ready for
     review » quand tout est fini et relu : la CI coûteuse tourne alors (CONVENTIONS.md §PR, CI-BUDGET.md §2). -->
<!-- LOT-XXX (pour un lot du plan seulement) -->
Closes #
<!-- Une ligne par issue fermée. Travail partiel : « Refs #n — reste : … ». Petit correctif sans issue : Direct-PR: <raison>. -->
Claim: <!-- identifiant du /claim actif de l'issue -->

**Problème** :

**Cause** :

**Changement** (et pourquoi si large, pas plus) :

**Tests** :
<!-- Noms, ce qu'ils vérifient, montrés en échec sans le changement ; commandes lancées ; build Mac ; non testé / à
     valider sur l'appareil (ex. app non compilable dans le conteneur Linux). -->

<!-- Revues : chaque verdict (adversarial, conformité) est posté en commentaire, le premier négatif compris
     (REVIEW-ROUNDS.md §Traçabilité). -->

<!-- Registre (seulement si .harness/config.json → ledger.enabled, CONVENTIONS.md §Registre) : une section
     « ### Ledger » avec un bloc par entrée, au format du script du projet, et le label `ledger`. Aucune entrée :
     ni section, ni label. Ne jamais modifier directement les fichiers du registre. -->

<!-- Modèle auteur / relecteur (doivent différer), avec l'identifiant de chaque agent (ORCHESTRATION.md §7) : -->
Modèle auteur : … (<projet>.<orc>.lot.<cible>) · relecteur : … (<projet>.<orc>.rev.<cible>)
