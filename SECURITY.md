# Sécurité

## Versions couvertes
La dernière version taguée (`vX.Y.Z`, voir [CHANGELOG](CHANGELOG.md)) et la branche `master`. Les versions
antérieures ne reçoivent pas de correctif : la réponse est de passer à la dernière ([ADOPTION](docs/ADOPTION.md)
§Mises à jour).

## Signaler une faille
**En privé, jamais dans une issue, une PR ou une discussion publique.**

- [Ouvrir un signalement privé](https://github.com/francoisgn/agentic-harness/security/advisories/new) (onglet
  Security du dépôt → « Report a vulnerability » ;
  [doc GitHub](https://docs.github.com/fr/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)).
- Y mettre : la version ou le commit, le fichier concerné, les étapes pour reproduire, l'effet (ce qu'un attaquant
  obtient), et un correctif si vous en avez un. Aucun secret réel dans le signalement.

## Ce à quoi s'attendre
- Accusé de réception sous **7 jours**.
- Ensuite : confirmation ou refus motivé, puis correctif dans une nouvelle version et avis publié, avec votre nom
  si vous le souhaitez. Projet maintenu sur le temps libre : pas de délai garanti pour le correctif.
- Merci de ne rien divulguer avant la publication du correctif.

## Périmètre
| Dans le périmètre | Exemples |
|---|---|
| Garde-fous | `plugins/harness/scripts/guard-git.py` contourné (push direct ou force-push sur une branche protégée) |
| Scripts | `scripts/harness-sync.sh` qui écrit hors du dépôt cible ; `scripts/repo-settings.py` qui applique plus que le fichier |
| Workflows réutilisables | `.github/workflows/*.yml` : injection par un titre, un corps ou un commentaire ; jeton trop large ; fuite de secret |
| Skills, agents, gabarits | consigne qui fait suivre à un agent le texte d'une issue, d'une PR ou d'un journal comme une instruction |

Hors périmètre : les projets qui utilisent le cadre (les signaler à leurs mainteneurs), les agents de code et les
services tiers eux-mêmes (les signaler à leur éditeur), les rapports d'outils automatiques sans scénario d'exploitation.
