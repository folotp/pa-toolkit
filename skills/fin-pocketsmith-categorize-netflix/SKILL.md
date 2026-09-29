---
name: fin-pocketsmith-categorize-netflix
description: "Sépare la transaction mensuelle Netflix dans PocketSmith en deux montants fixes (part de PA vers Contenu TV & musique, part d'André vers Avances - André), revue avec PA avant écriture. Trigger sur toute mention de Netflix dans PocketSmith, catégorisation ou split de la facture Netflix."
---

# Netflix → PocketSmith categorization

Netflix facture PA pour l'abonnement principal (forfait Premium) et pour un abonnement additionnel utilisé par son père André, dans une seule transaction bancaire mensuelle. PA rembourse déjà cette portion via une catégorie d'avance — ce n'est pas un partage proportionnel à calculer, mais un split à **montant fixe connu d'avance** : 27,58$ (PA, taxes incluses) + 9,19$ (André, taxes incluses) = 36,77$. Contrairement à Rogers (répartition lue sur une facture externe chaque mois) ou Amazon (répartition recalculée depuis le contenu réel de la commande), il n'y a ici ni facture à récupérer ni calcul à faire : les deux montants sont des constantes tant que Netflix ne change pas ses prix canadiens.

## 1. Trouver les transactions candidates

```
list_transactions(user_id=<id>, uncategorised=true, search="netflix")
```

Le payee brut varie d'un mois à l'autre côté banque — vu en pratique : `Netflix.com`, `NETFLIX.COM`, et `Netflix` (ère YNAB, avant juin 2026). Le paramètre `search` de PocketSmith fait un match insensible à la casse/sous-chaîne, donc `"netflix"` attrape les trois formes — ne pas supposer une seule orthographe canonique.

**Contexte important** : jusqu'au 2026-09-15, une règle de catégorisation (`payee_matches: "Netflix"` → *Contenu TV & musique*) routait automatiquement la transaction entière (36,77$) vers cette catégorie dès l'import — elle n'apparaissait donc jamais comme *uncategorised*, contrairement à Rogers. Cette règle a été supprimée manuellement par PA le 2026-09-15 (l'API PocketSmith ne permet ni de modifier ni de supprimer une règle existante une fois créée — seule la création de nouvelles règles est possible par ce canal). Depuis, les nouvelles transactions Netflix devraient arriver *uncategorised* comme n'importe quel autre payee non traité. **Si une transaction Netflix récente apparaît de nouveau intégralement catégorisée dans Contenu TV & musique sans passer par ce skill** (signe qu'une règle similaire a été recréée, manuellement ou par erreur), chercher plutôt avec `category_id=<Contenu TV & musique>, search="netflix"` et filtrer sur les transactions à exactement -36,77$ sans étiquette `netflix-processed` — puis signaler la règle retrouvée à PA plutôt que de supposer qu'elle a disparu pour de bon.

Exclure toute transaction portant déjà l'étiquette `netflix-processed` — la retraiter dupliquerait l'avance déjà enregistrée pour André.

Une transaction à **montant positif** (remboursement/crédit) — aucun précédent observé — doit être signalée à PA comme question autonome plutôt que traitée automatiquement.

## 2. Vérifier le montant

Montant attendu : **-36,77$** (PA 27,58$ + André 9,19$, taxes incluses chacun).

- **Si le montant correspond exactement** : passer directement à la revue avec PA (étape 3) — pas de facture à lire, pas de calcul proportionnel.
- **Si le montant diffère de -36,77$** : ne rien écrire. Faire une recherche web sur la tarification Netflix Canada actuelle (page de tarifs officielle ou centre d'aide Netflix) pour vérifier si les prix ont changé et pour quels forfaits. Présenter à PA, via `AskUserQuestion`, l'ancien split (27,58$/9,19$) et ce que la recherche a trouvé comme nouveaux prix possibles, et le laisser trancher le nouveau split — ne jamais déduire un nouveau split soi-même. Une fois PA d'accord sur de nouveaux montants fixes, **mettre à jour les constantes de ce skill** (cette section et l'étape 4) pour refléter le nouveau split, et consigner le changement dans `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0155.md` (journal).

## 3. Revoir avec PA

Un seul `AskUserQuestion` suffit pour confirmer le split (contrairement à Rogers, pas de montants variables à valider ligne par ligne — les deux montants sont fixes et déjà connus). Montrer : date, montant, compte, et le split proposé (27,58$ → Contenu TV & musique / 9,19$ → Avances - André).

S'il y a **plusieurs transactions Netflix en attente simultanément** avec le même montant attendu (ex. rattrapage de plusieurs mois), les présenter ensemble dans une seule question plutôt qu'une par une, puisque le split est identique à chaque fois — sauf si l'une d'entre elles a un montant différent (auquel cas cette transaction-là suit le chemin de l'étape 2 séparément).

PA peut toujours ajuster en texte libre — traiter comme faisant autorité.

## 4. Exécuter le split approuvé

```
update_transaction(id,
  category_id=<Contenu TV & musique>,   # reste sur la transaction mère (part de PA)
  payee="Netflix",
  splits=[
    {amount: 9.19, category_id: <Avances - André>, payee: "Netflix"}
  ],
  note=<voir format ci-dessous>,
  labels="netflix-processed")
```

Ceci fixe correctement la note sur la transaction mère mais la copie aussi sur l'enfant (même comportement PocketSmith que pour Rogers/Amazon) — corriger avec un `update_transaction(child_id, note=...)` de suivi, en utilisant l'ID retourné dans `split_transactions`.

**Payee** : `"Netflix"` sur la transaction mère et sur le split — convention confirmée par PA le 2026-09-15 (reprend l'usage de l'ère YNAB). `original_payee` conserve la chaîne brute de la banque quel que soit le mois.

**Format de note** — une première ligne commune (montants du split), puis la ligne spécifique à cette moitié :

```
Netflix — split fixe PA/André (27,58$ / 9,19$)
Part 1/2: PA (Contenu TV & musique), 27,58$
```
```
Netflix — split fixe PA/André (27,58$ / 9,19$)
Part 2/2: André (Avances - André), 9,19$
```

Ne pas résoudre les IDs de catégorie depuis un run précédent codé en dur — les relire via `list_categories` à chaque fois (même discipline que Rogers/Amazon), l'ID reste stable mais la vérification coûte peu et protège contre une réorganisation future des catégories.

## Hors périmètre (ne pas essayer de résoudre ici)

- **Remboursements/crédits** — aucun cas observé; une transaction Netflix à montant positif va à PA comme question autonome, pas dans ce flux.
- **Un deuxième pattern de payee Netflix** — seuls `Netflix`, `Netflix.com` et `NETFLIX.COM` ont été observés (tous attrapés par `search="netflix"`); si un jour un pattern radicalement différent apparaît (ex. facturation via un tiers), le signaler à PA plutôt que de l'ignorer silencieusement.

## Convention de nommage

Suit la convention `fin-<outil>-<action>` de PA : `pocketsmith` est le système où atterrit le travail, `categorize-netflix` est l'action — même patron que `fin-pocketsmith-categorize-rogers` et `fin-pocketsmith-categorize-amazon`.

## Référence

Rationale de conception, découvertes sur le fonctionnement réel du payee Netflix et de la règle de catégorisation supprimée, et le rattrapage des 3 premières transactions traitées de bout en bout sont documentés dans le coffre Organon à `01 - Finances et patrimoine/Backlog/Items/FIN-BL-0155.md`.