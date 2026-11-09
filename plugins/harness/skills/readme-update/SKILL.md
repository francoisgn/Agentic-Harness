---
name: readme-update
description: Met le README du projet au standard du cadre agentic-harness et le garde vrai — tuiles technologiques en en-tête, image du produit, schéma d'architecture Excalidraw, tableau d'avancement des lots, démarrage, section Contribuer. À utiliser à la fin d'un lot, après un merge qui change l'architecture ou l'état d'un lot, ou quand le README est absent, vide ou périmé.
argument-hint: "[lot ou section à mettre à jour, défaut : tout]"
---

# Mettre le README à jour

Cible : $ARGUMENTS (défaut : tout le README). Standard : `.harness/docs/README-STANDARD.md` (sinon
`${CLAUDE_PLUGIN_ROOT}/docs/README-STANDARD.md`). Ce que le projet a coupé dans `.harness/config.json` › `readme` ne
se remet pas.

1. **Constater** : `python3 .harness/scripts/readme-check.py` liste les écarts. README absent : partir du gabarit
   `README.md` du cadre ; `CONTRIBUTING.md` absent : idem.
2. **Tuiles** : une par brique réellement utilisée, lue dans les manifestes (`Package.swift`, `Cargo.toml`,
   `package.json`, `pyproject.toml`, workflows), pas de mémoire. Version = celle du manifeste. Tuile d'état (CI,
   release) = badge vivant du workflow. Retirer celles qui ne sont plus vraies.
3. **Schéma d'architecture** : si les modules, les flux ou les services externes ont changé, modifier
   `docs/diagrams/architecture.json`, puis `python3 .harness/scripts/diagrams-render.py` et commiter `.json`, `.svg`,
   `.excalidraw` ensemble. Le schéma montre ce qui est livré, pas la cible ; 5 à 9 boîtes, un verbe sur chaque flèche
   utile. Un débordement de texte signalé par le rendu se corrige (boîte plus large ou texte plus court).
4. **Avancement** : réécrire le tableau entre `<!-- harness:begin avancement -->` et `<!-- harness:end avancement -->`.
   Une ligne par lot de `docs/LOTS.md` (sinon par jalon GitHub) ; l'état se lit sur l'issue et sa PR **maintenant**
   (ouverte, prise en charge, PR prête, mergée, `bloqué`), jamais sur le souvenir de la session :
   ⚪ à faire · 🔵 en cours · 🟠 en revue · 🔴 bloqué · 🟢 livré.
5. **Images** : une capture n'entre que si elle montre le produit actuel ; texte alternatif qui décrit ce qu'on voit ;
   fichier sous `docs/images/`. Une capture qui demande un appareil ou un poste précis : une issue, pas une image
   inventée.
6. **Démarrage et Contribuer** : rejouer les commandes citées (ou dire lesquelles n'ont pas pu l'être ici) ; la
   section Contribuer renvoie à `CONTRIBUTING.md`.
7. **Vérifier** : `python3 .harness/scripts/readme-check.py` sans écart, `diagrams-render.py --check` vert. Les
   changements partent dans le commit du lot (ou une PR de docs en brouillon hors lot).

Rendre compte : écarts trouvés, sections modifiées, ce qui reste à fournir par l'opérateur (capture, licence).
