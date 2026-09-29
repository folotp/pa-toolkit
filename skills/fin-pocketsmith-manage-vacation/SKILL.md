---
name: "fin-pocketsmith-manage-vacation"
description: "Manages the complete lifecycle of a trip or vacation (a 'séjour') in PA's PocketSmith: opens the dated vacation label, finds and categorizes the vacation's transactions through one-at-a-time interactive review, renames the label idempotently if dates change, closes the vacation with a completeness audit and cost report, and applies the Épicerie prorata budget correction. Callable at any point in a vacation's life — before departure, mid-trip, after return, or repeatedly — because every call re-derives the real state from PocketSmith rather than trusting what a previous call did. Trigger on any mention of a trip/vacation/séjour/voyage/vacances in PocketSmith, opening or closing a vacation label, finding missed vacation transactions, renaming a Voyage-/Vacances- label, or correcting the grocery budget for a trip."
---

# Gestion d'un séjour PocketSmith

Ce skill applique [[FIN-DEC-119]] (catégorie unique « Vacances et voyages ✈️ », étiquette datée par séjour), [[FIN-RULE-PSMITH-008]] (format d'étiquette) et, pour l'épicerie, [[FIN-DEC-121]] / [[FIN-RULE-BUD-003]] / [[FIN-RB-023]]. Il ne réinvente aucune de ces règles — il les exécute. En cas de doute sur une règle, relire la fiche citée plutôt que d'improviser.

**Principe directeur : ce skill n'a pas de mémoire d'un appel à l'autre.** Chaque invocation recalcule l'état réel d'un séjour à partir de PocketSmith (étiquette, catégorie de chaque transaction, dates) et le compare aux règles — jamais l'inverse. Un écart compte peu importe qui l'a produit : une transaction que PA a lui-même confirmée lors d'un appel précédent et qui s'avère erronée est traitée exactement comme n'importe quel autre écart. Ce qui est déjà conforme reste intact ; seul ce qui manque ou diverge est proposé en correction. C'est ce qui rend le skill idempotent et rejouable à tout moment — pas un flag « déjà traité » quelque part, mais une vérification fraîche à chaque fois.

**Aucune écriture de catégorie ou d'étiquette sans confirmation de PA, une transaction à la fois** — que ce soit une nouvelle candidate ou la correction d'une transaction déjà traitée avant. Utiliser `AskUserQuestion`, dans le même style que `fin-pocketsmith-categorize-amazon` / `fin-pocketsmith-categorize-apple` : la question, la recommandation en premier (« recommandé »), 1-2 alternatives, réponse libre toujours possible. La seule exception est le **renommage mécanique** d'étiquette (§5) : remplacer une valeur d'étiquette par une autre sur toutes les transactions qui la portent est un remplacement chaîne-à-chaîne sans jugement de catégorisation — proposer l'opération une fois à PA (« renommer l'étiquette du séjour X sur toutes ses transactions ? »), pas transaction par transaction.

## 0. Trouver l'état actuel du séjour

Avant toute chose, établir dans quelle phase se trouve le séjour visé — deviner la mauvaise phase fait reposer des questions déjà réglées avec PA, ou saute une étape qu'un séjour rouvert doit encore franchir.

1. `list_labels(user_id)` puis filtrer les valeurs qui matchent `^(Voyage|Vacances)-` — c'est l'inventaire complet des séjours existants (provisoires et datés).
2. Si le nom donné par PA correspond à une étiquette existante : le séjour est déjà ouvert. Lire son préfixe — dates fermes (`Type-AAAAMMJJ-AAAAMMJJ-Nom`) ou provisoire (`Type-AAAA-Nom`) — pour savoir si un renommage (§5) est dû.
3. Si aucune étiquette ne correspond : c'est une ouverture (§1).
4. Dans tous les cas, que PA demande explicitement « repère les transactions », « ferme ce séjour » ou juste « occupe-toi de mon voyage à X » — exécuter la séquence pertinente (§§1-4 rangement, §5 renommage si dû, §6 clôture, §7 épicerie) plutôt que de s'arrêter à la première étape demandée littéralement : un séjour rouvert plusieurs fois dans son cycle de vie doit converger vers un état correct à chaque appel.

## 1. Ouverture

Demander à PA plutôt que déduire — type, nom et dates n'existent nulle part ailleurs que dans sa tête :

- **Type** (`Voyage` ou `Vacances`) : aucun critère écrit n'existe ([[FIN-RULE-PSMITH-008]]) ; PA tranche au cas par cas.
- **Nom** du lieu (tel qu'il apparaîtra dans l'étiquette).
- **Dates** de départ et de retour si elles sont déjà fermes ; sinon, étiquette provisoire `Type-AAAA-Nom` (l'année seule — l'année de départ si connue, sinon l'année courante), à renommer dès que les dates sont fixées (§5).

Aucun appel PocketSmith n'est nécessaire pour « créer » l'étiquette — les étiquettes PocketSmith naissent implicitement à la première transaction qui les porte (§3). L'« ouverture » consiste donc à fixer le nom exact de l'étiquette à utiliser pour tout le reste du cycle de vie, puis à enchaîner directement sur le repérage (§2).

## 2. Repérage des transactions candidates

Combiner au minimum ces sources — une seule ne suffit pas (le cas Grandes-Bergeronnes, 13 transactions oubliées parce que seules les dates strictes avaient été vérifiées, est le rappel permanent de pourquoi) :

1. **Fenêtre élargie autour des dates du séjour.** `list_transactions(category_id=<id de "Vacances et voyages ✈️", résolu par list_categories>, start_date=<veille du départ ou plus tôt>, end_date=<quelques jours après le retour>)` **et** la même fenêtre sans filtre de catégorie, pour capter ce qui n'a encore ni la bonne catégorie ni l'étiquette. Élargir d'au moins un jour avant le départ (dépenses de préparation) et plusieurs jours après le retour (délai de comptabilisation, surtout à l'étranger) — le pilote sur Grandes-Bergeronnes a confirmé des dépenses légitimes la veille du départ et jusqu'à 5 jours après le retour (un virement de remboursement).
2. **Devise étrangère ou frais de conversion** dans cette même fenêtre — `amount_in_base_currency != amount`, ou un marchand identifiable comme étranger — signe fort d'une dépense de séjour même si la catégorie ou l'étiquette manquent encore.
3. **Réservations antérieures** (transport, hébergement, location, parcs, stationnement) : celles-ci sont souvent payées des mois à l'avance et n'apparaîtront jamais dans la fenêtre de dates du séjour. Demander à PA quels marchands/réservations chercher (compagnie aérienne, hôtel, location de véhicule…) et faire une recherche texte ciblée sur une fenêtre bien plus large (mois avant le départ) — ne pas essayer de les deviner automatiquement.
4. **Retraits au guichet** pendant la fenêtre du séjour (`payee` contenant retrait/ATM/guichet), particulièrement à l'étranger.

**Ne jamais déduire les dates du séjour des dates de transaction** — elles viennent uniquement de PA (§1) ou du préfixe déjà fixé dans l'étiquette existante. Une transaction dans la fenêtre n'est qu'une *candidate* ; la fenêtre sert à proposer, pas à décider.

**Note opérationnelle** : `list_transactions` retourne un JSON très verbeux (chaque transaction inclut l'objet compte/institution complet) — une fenêtre de quelques semaines dépasse vite la limite de sortie de l'outil. Utiliser `per_page` raisonnable, et si le résultat est tronqué et sauvegardé sur disque, le reparser (ex. Python/`jq`) pour n'extraire que `id/date/payee/amount/category.title/labels` plutôt que de tenter de le relire en entier.

## 3. Revue interactive et écriture

Pour chaque candidate (nouvelle ou déjà en place mais divergente — voir §6), une question `AskUserQuestion` à la fois :

- Contexte : date, marchand, montant, catégorie actuelle, fenêtre du séjour.
- Recommandation par défaut : catégorie « Vacances et voyages ✈️ » + étiquette du séjour — sauf si le contexte suggère une dépense partagée (ci-dessous) ou clairement hors sujet.
- PA peut toujours répondre autre chose ; sa réponse prime toujours sur la recommandation.

**Dépenses partagées avec Élise ou un tiers** — règle confirmée avec PA lors du pilote (transaction réelle : virement Interac de 155 $ à Élise, note « 80 $ Grandes-Bergeronnes et 75 $ 2 billets pour Théâtre de la Licorne », déjà scindé en pratique) :

- Si un virement ou une dépense mixte couvre **en partie** un coût réellement partagé du séjour et en partie autre chose (sans lien avec le séjour) : **scinder** (`update_transaction` avec `splits`). Seule la part qui est un vrai coût de séjour reçoit catégorie « Vacances et voyages ✈️ » + étiquette du séjour ; le reste garde sa catégorie propre, sans étiquette de séjour.
- Le `note` de chaque part devrait rendre explicite ce qu'elle couvre (suivre le style déjà utilisé par PA : montant total, part par destination) — pas de format imposé strict ici, contrairement aux skills Amazon/Apple, mais toujours traçable.
- Si la transaction est une **avance** à quelqu'un (l'argent part avant que la dépense réelle du séjour soit confirmée), ne pas l'étiqueter séjour tant que la dépense réelle n'est pas connue — la router plutôt vers la catégorie « Avances - <personne> » existante, et re-visiter au prochain appel du skill si la dépense se confirme.

**Écriture** : `update_transaction(id, category_id=<id résolu>, labels=<liste actuelle + étiquette du séjour>)`. Toujours résoudre l'id de catégorie par nom via `list_categories` à chaque appel plutôt que de réutiliser un id mémorisé (id observés 2026-09-21 : « Vacances et voyages ✈️ » = 33650476, « Épicerie (alimentation, hygiène, entretien) » = 33650280 — à revalider, pas une source de vérité). Les étiquettes déjà présentes (`YNAB`, `Fonds-de-remplacement`, `Auto-<Modèle>`, etc.) servent d'autres suivis que ce skill ne gère pas — les écraser leur ferait perdre leur trace ailleurs. L'étiquette de séjour s'ajoute donc à la liste existante, elle ne la remplace pas, sauf s'il s'agit de remplacer une étiquette de séjour périmée (§5).

## 4. Étiquette provisoire → étiquette datée (à l'ouverture ou dès que les dates sont connues)

Si PA fournit les dates à un moment où l'étiquette est encore provisoire (`Type-AAAA-Nom`), ou lors de l'ouverture avec dates déjà fermes, appliquer directement l'étiquette finale sur chaque transaction au fil du repérage (§3) — pas besoin d'un passage de renommage séparé dans ce cas, puisqu'aucune transaction ne porte encore l'ancienne forme.

## 5. Renommage (dates provisoires → fermes, ou dates modifiées)

PocketSmith n'offre aucun renommage natif d'étiquette — remplacement transaction par transaction, mais rendu idempotent par une vérification systématique :

1. `list_transactions(user_id, search=<ancienne étiquette exacte, ex. "Vacances-2026-Grandes-Bergeronnes">, per_page=100)`. Chercher **la forme complète avec traits d'union** ([[FIN-RULE-PSMITH-008]], corollaire de recherche) — jamais des mots séparés, qui donneraient de faux positifs.
2. Pour chaque résultat, `update_transaction(id, labels=<liste actuelle moins l'ancienne étiquette, plus la nouvelle>)` — préserver toute autre étiquette déjà présente sur la transaction.
3. **Vérifier par API** : relancer la même recherche sur l'ancienne étiquette — elle doit retourner zéro résultat. C'est cette vérification, pas une hypothèse, qui rend le renommage idempotent : relancer le skill sur un séjour déjà renommé ne trouve plus rien à faire.
4. Annoncer à PA le nombre de transactions renommées et confirmer qu'aucune occurrence de l'ancienne étiquette ne subsiste.

Piloté le 2026-09-21 sur 3 transactions de Grandes-Bergeronnes (étiquette provisoire réintroduite exprès pour le test) : les 3 retrouvées par la recherche exacte, renommées, 0 occurrence résiduelle confirmée par une nouvelle recherche.

## 6. Clôture — contrôle d'exhaustivité et rapport de coût

Rejouable à tout moment, avant ou après le retour. Trois vérifications, chacune sur la fenêtre élargie du séjour (§2) :

1. **Transactions dans la catégorie mais sans l'étiquette du séjour** : `list_transactions(category_id=<Vacances et voyages>, start_date, end_date)`, filtrer celles dont `labels` ne contient pas l'étiquette exacte du séjour (mais peut en contenir une *autre* — signal possible de bug de saisie, à signaler aussi).
2. **Transactions étiquetées mais hors catégorie** : `list_transactions(search=<étiquette exacte du séjour>)`, filtrer celles dont `category.title` n'est pas « Vacances et voyages ✈️ ». Cette recherche texte peut aussi remonter des faux positifs (ex. une transaction sœur d'un split partagé dont le `note` mentionne le nom du séjour sans porter l'étiquette ni la catégorie — normal, à ignorer, pas une transaction du séjour).
3. **Zéro ou 2+ étiquettes de séjour** sur une même transaction : parmi les résultats des deux recherches ci-dessus, repérer celles dont les `labels` contiennent plus d'une valeur matchant `^(Voyage|Vacances)-\d`.

Chaque écart trouvé passe par la revue interactive (§3) avant toute écriture — y compris un écart sur une transaction déjà confirmée par PA lors d'un appel antérieur. **Zéro écart = rien à proposer** : ne pas écrire, juste confirmer l'état à PA.

**Rapport de coût** : une fois l'état propre, `list_transactions(search=<étiquette exacte>)`, sommer `amount` de celles portant l'étiquette et la bonne catégorie, compter les transactions, lire les dates dans le préfixe de l'étiquette (jamais dans les dates de transaction), jours en séjour = écart entre les deux dates + 1 (départ et retour inclus).

Piloté sur Grandes-Bergeronnes (`Vacances-20260814-20260822-Grandes-Bergeronnes`, 2026-09-21) :

- **Écart réel trouvé et corrigé** (pas une simulation) : CHOCOMOTIVE (2026-08-22, -12,65 $) portait l'étiquette du séjour mais restait catégorisée « Épicerie » — repérée par la vérification #2. Revue avec PA : il a choisi de retirer l'étiquette plutôt que de recatégoriser (ce n'était finalement pas une dépense du séjour).
- **Test d'idempotence, écart nul** : après correction, un nouveau passage des trois vérifications sur l'état réel ne trouve plus rien (0 écart, 19 transactions, -946,68 $).
- **Test d'idempotence, écart volontaire** : catégorie changée sur une transaction déjà étiquetée (TIM HORTONS, gardait l'étiquette) et étiquette retirée d'une transaction déjà catégorisée (LE QG DU CAFE, gardait la catégorie) — les deux vérifications ont chacune détecté exactement l'écart introduit, sans faux positif sur les 17 autres transactions ; les deux corrections proposées à PA une à la fois, confirmées, appliquées, re-vérifiées à zéro écart.
- **Candidates ambiguës hors fenêtre stricte** trouvées par le repérage élargi (§2) et tranchées par PA : un achat d'équipement de plein air la veille du départ (jugé sans lien), une épicerie le jour du retour dans un commerce près du domicile (jugée sans lien, achat à la maison plutôt que dépense de séjour).
- Rapport final : 19 transactions, **-946,68 $**, 9 jours (14 au 22 août inclus).

## 7. Correction au prorata du budget Épicerie

Applique [[FIN-RULE-BUD-003]] via [[FIN-RB-023]] — ne recalcule ni ne réinvente la formule, se contente de l'exécuter pour le séjour en cours.

1. **Identifier la ou les périodes budgétaires Épicerie touchées** par les dates du séjour, qu'elles soient encore à venir ou déjà passées. Depuis l'amendement du 2026-09-21 de [[FIN-DEC-121]] point 4, la correction est **systématique** : une période déjà passée sans correction est traitée exactement comme une période à venir, pas ignorée — `rollover_type: both` reporte indéfiniment tout surplus artificiel non corrigé, connu d'avance ou découvert après coup. Distinguer simplement, pour l'étape 6, si l'exécution sera proactive (période future) ou rétroactive (période déjà écoulée) — cela ne change que la mécanique dans PocketSmith (l'événement déjà passé reste modifiable au même endroit), pas le calcul ni la décision de corriger.
2. Si applicable (période(s) encore à venir) : vérifier par API que l'étiquette porte des **dates fermes** (pas `Type-AAAA-Nom`).
3. Demander à PA, **à chaque exécution** (donnée périssable, jamais réutilisée d'un appel précédent — [[Finance Bootstrap]] § Éléments périssables) : le montant budgété courant d'« Épicerie » et sa cadence (hebdomadaire ou mensuelle — a changé au moins une fois, aucun outil de cette session ne le lit par API).
4. Demander la **fraction de présence du ménage** si le séjour n'implique pas tout le monde (défaut : 1, ménage entier).
5. Calculer, par période touchée (répartir si le séjour chevauche deux périodes) : `réduction = budget courant ÷ jours de la période × jours en séjour pondérés de cette période`.
6. Présenter le calcul à PA. **Aucun outil de cette session n'écrit un budget PocketSmith** — l'exécution reste manuelle dans PocketSmith (Calendrier → cliquer l'événement → modifier le montant → Update → « Only this budget event », jamais toute la série (qui appliquerait la correction à toutes les périodes budgétaires futures, pas seulement à celle touchée par le séjour)) ; le skill calcule et guide, PA exécute. Pour une période déjà passée (correction rétroactive), la mécanique PocketSmith reste identique — l'événement budgétaire écoulé demeure modifiable au même endroit (Calendrier).
7. Après exécution par PA, vérifier par API (`get_category`, id de « Épicerie ») que `rollover_type` est inchangé, et consigner dans le Journal de [[FIN-RB-023]] : date, séjour, période(s), montants avant/après, résultat de la vérification.

**Validé pendant le pilote** (sans nouvelle écriture) : la formule reproduit exactement le calcul déjà exécuté et confirmé pour Prague le 2026-09-21 (207 $/semaine, 8 jours en séjour à cheval sur deux semaines → 0,00 $ puis 177,43 $, voir [[FIN-RB-023]] Journal) — validation croisée du moteur de calcul sur un cas réel déjà vérifié indépendamment. Détail complet du pilote (dont le traitement de Grandes-Bergeronnes) : [[Backlog/Items/FIN-BL-0157]].

## 8. Rapport multi-séjours

Alimente [[FIN-BL-0158]] et tout suivi « Vacances et voyages » (ex. [[FIN-DEC-119]] Mise en œuvre).

1. `list_labels(user_id)`, filtrer `^(Voyage|Vacances)-`.
2. Pour chaque étiquette au format daté, parser type / dates / nom depuis le préfixe.
3. Pour chacune, `list_transactions(search=<étiquette exacte>)`, sommer les transactions dont la catégorie est bien « Vacances et voyages ✈️ » (ignorer les faux positifs texte comme en §6), compter, calculer les jours (retour − départ + 1).
4. Assembler le tableau type / nom / départ / retour / jours / total / nb transactions, trié par date de départ. Les étiquettes encore provisoires (`Type-AAAA-Nom`) apparaissent avec dates « à confirmer ».

Généré pendant le pilote (2026-09-21, état réel vérifié par API) :

| Type | Nom | Départ | Retour | Jours | Transactions | Total |
|---|---|---|---|---|---|---|
| Voyage | Prague | 2026-06-15 | 2026-06-22 | 8 | 23 | -909,65 $ |
| Voyage | Moncton | 2026-07-22 | 2026-07-26 | 5 | 14 | -846,53 $ |
| Vacances | Grandes-Bergeronnes | 2026-08-14 | 2026-08-22 | 9 | 19 | -946,68 $ |
| Voyage | Îles-du-maïs | 2027-02-25 | 2027-03-07 | 11 | 4 | -1 814,34 $ |

(Moncton et Grandes-Bergeronnes ont chacun reçu un virement Interac de remboursement à Élise depuis le pilote de [[FIN-BL-0157]] le 2026-09-21 — les totaux ci-dessus les incluent déjà et diffèrent donc légèrement des totaux figés dans [[FIN-DEC-119]] au 2026-09-16 ; c'est attendu, pas une divergence.)

## Hors périmètre (ne pas tenter de résoudre ici)

- **Écriture d'un budget PocketSmith par API** — aucun outil de cette session ne l'expose ; §7 s'arrête au calcul et au guidage, l'écriture reste manuelle.
- **Détection automatique des réservations antérieures** sans indice de PA — aucun moyen fiable de deviner qu'un débit d'avril est un billet d'avion pour un voyage de février suivant sans que PA nomme le marchand ou la fenêtre à chercher.
- **Fraction de présence du ménage** déduite automatiquement — toujours demandée à PA, jamais inférée.

## Référence

Conception et pilote complet documentés dans le vault Organon à `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0157.md` — lire pour le détail du pilote (séjour Grandes-Bergeronnes, tests d'idempotence, écart réel trouvé et corrigé).