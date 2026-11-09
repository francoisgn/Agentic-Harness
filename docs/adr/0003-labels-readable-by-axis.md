# 0003 — Labels lisibles par axe : `axe: valeur`, états « à trier » et « prête »

**Statut :** Proposé — 2026-11-09 (le mainteneur décide ; rien n'est renommé tant que cet ADR n'est pas accepté)

## Contexte
Relevé du 2026-11-09 sur les dépôts qui suivent ou ont inspiré le cadre.

- **Client iOS** (437 issues, 269 PR, 51 labels) : quatre axes préfixés, tenus exclusifs à la main. Sur 217 issues
  ouvertes, 216 portent exactement un `status:`, toutes un `type:` et une `priority:`. États les plus peuplés :
  `status: ready` (84), `status: blocked` (64), `status: needs-triage` (52), `status: claimed` (16). Le statut est
  retiré à la fermeture. Aucun jalon GitHub, aucun assigné ; lot et jalon vivent dans les titres (`LOT-147`, `(M4)`).
  Les PR ne sont presque pas labellisées (202 sur 269) : leur état se lit sur la PR (brouillon, revue, contrôles).
  Les huit labels GitHub par défaut ont zéro usage.
- **Projet Rust (fork)** : suivi hors GitHub ; l'amont utilise `priority: critical|high|medium|low`, `needs info`,
  `in progress`, et propose `difficulty: trivial|easy|medium|hard`.
- **Le cadre** (`templates/.github/labels.json`, 27 labels) : noms français sans préfixe (`bloqué`, `à clarifier`,
  `pris en charge`), priorités avec emoji (`P1 🔴`), deux axes (`modèle:` ×4, `taille:` ×3) là où le projet réel en
  utilise un (`difficulty:` ×4). Aucun des projets observés n'utilise les noms canoniques du cadre ; ils passent par
  les `aliases`.
- **Trous** : le cadre n'a ni « à trier » ni « prête », soit 136 des 217 issues ouvertes du projet le plus actif. Un
  agent ne peut pas distinguer une issue prenable d'une issue non triée. `bloqué` mélange dépendance technique et
  décision humaine attendue.
- **Poids mort** (zéro usage observé) : `ux`, `release`, `feedback`, `taille:` ×3, `modèle:` ×4, `tableau de bord`,
  `revue: aucune`, `conformité`.
- Le dépôt du cadre lui-même ne porte que les labels GitHub par défaut : `labels.json` n'y est pas appliqué, le
  label `leçon` de son formulaire n'existe pas.

## Options
1. **Garder les noms actuels, ajouter deux états** (`à trier`, `prête`). Aucune migration. Les axes restent non
   filtrables par préfixe, l'emoji reste dans les priorités, le cadre reste à côté de ce que les projets utilisent.
2. **Passer à `axe: valeur`, en anglais, ASCII, sans emoji** ; les noms actuels deviennent des `aliases` (le
   mécanisme existe, on en inverse le sens). Migration : `labels-sync` avec `apply-aliases: true`, plus
   `flow-metrics.py`, `issue-hygiene.yml`, les formulaires et les docs. Changement cassant, donc version mineure avec
   ligne « Action ».
3. **Option 2, avec le jeu de noms réglable par langue** (`i18n/<langue>/labels.json`). Même migration ; les projets
   francophones gardent des noms français préfixés (`statut: prête`). Deux jeux à maintenir.

## Décision
Proposée : **option 2**.

| Axe | Labels | Exclusif | Obligatoire |
|---|---|---|---|
| `status:` (issues ouvertes, retiré à la fermeture) | `needs-triage`, `ready`, `claimed`, `blocked`, `needs-decision` | oui | oui |
| `type:` | `bug`, `feature`, `chore`, `docs`, `security`, `epic` | oui | oui |
| `priority:` | `critical`, `high`, `medium`, `low` | oui | après tri |
| `difficulty:` | `trivial`, `easy`, `medium`, `hard` (le niveau de modèle conseillé va dans la description) | oui | après tri |
| `needs:` (cumulable, issues et PR) | `info`, `host`, `review` | non | non |
| suivi | `direct-pr`, `dependencies` | non | non |
| local (`labels.local.json`) | `area: <module>`, `origin: …`, labels déclencheurs de CI, `leçon` pour le dépôt du cadre | — | — |

- 24 labels au lieu de 27 ; quatre axes exclusifs lisibles par préfixe.
- `status: needs-decision` (aujourd'hui `à clarifier`) sépare « un humain doit trancher » de `status: blocked`
  (dépendance, accès, capture).
- **Pas de label par lot ni par jalon** : jalon = milestone GitHub ; lot = `type: epic` avec sous-issues,
  identifiant `LOT-NNN` gardé dans le titre.
- **Pas de label d'état de PR** par défaut : brouillon, décision de revue et contrôles se lisent sur la PR ;
  `needs: review` reste disponible pour une PR prête sans relecteur.
- Prise en charge : `status: claimed` + commentaire daté (session, branche) ; signalée abandonnée après 24 h sans PR
  en brouillon ni commentaire d'avancement.
- Supprimés : `ux` (devient `area:` local), `release` (jalon), `feedback` (`type: epic`), `taille:` et `modèle:`
  (`difficulty:`), `tableau de bord`, `revue: aucune`, `conformité` (local si besoin).
- L'état se lit **sans workflow** : `issue-hygiene` contrôle (exactement un `status:` et un `type:` par issue
  ouverte, `status:` retiré à la fermeture) mais la règle tient aussi posée à la main.
- `labels-sync` signale les labels GitHub par défaut inutilisés au lieu de les laisser doubler les axes.

Lire l'état d'un projet :

| Question | Requête |
|---|---|
| En cours | `label:"status: claimed"`, PR ouvertes |
| Prenable | `label:"status: ready"`, triée par `priority:` |
| Bloqué / décision humaine | `label:"status: blocked"` / `label:"status: needs-decision"` |
| À trier | `label:"status: needs-triage"` |
| Hors de portée d'une session cloud | `label:"needs: host"` |
| Par jalon / par lot | `milestone:<nom>` / sous-issues de l'epic |

## Conséquences
- Plus facile : filtrer par axe, écrire le tableau de bord et le tableau d'avancement du README, accueillir un
  contributeur anglophone, s'aligner sur ce que les projets font déjà.
- Plus difficile : une migration par projet (alias appliqués une fois), `flow-metrics.py` et `issue-hygiene.yml` à
  adapter avec leurs tests, docs à reprendre (METHODOLOGY, ESSENTIEL, STEWARDS, formulaires).
- À surveiller : la règle « français partout » ne s'applique plus aux noms de labels ; le dire dans CONVENTIONS.
- À faire d'abord, quelle que soit l'option : appliquer `labels.json` au dépôt du cadre.
