# Gridiron IQ — NFL Broadcast Intelligence

**Gridiron IQ** est un dashboard Python interactif conçu pour assister un commentateur NFL avant, pendant et après une action. Il transforme les données du NFL Big Data Bowl en une interface de type régie TV : scorebug, replay aérien, analyse frame par frame, lecture tactique, métriques de poche, fenêtre de passe, tendances d’équipe et duels individuels.

> Le jeu de données fourni contient les matchs de la saison 2021, semaines 1 à 8. L’application simule donc un affichage en direct à partir de rencontres historiques ; elle n’est pas connectée à un flux NFL temps réel.

## Sommaire

- [Objectif](#objectif)
- [Fonctionnalités principales](#fonctionnalités-principales)
- [Installation et lancement](#installation-et-lancement)
- [Parcours utilisateur](#parcours-utilisateur)
- [Description détaillée des vues](#description-détaillée-des-vues)
- [Statistiques et métriques](#statistiques-et-métriques)
- [Provenance et niveau de confiance](#provenance-et-niveau-de-confiance)
- [Données utilisées](#données-utilisées)
- [Architecture](#architecture)
- [Limites analytiques](#limites-analytiques)
- [Dépannage](#dépannage)

## Objectif

Les box scores expliquent **ce qui s’est produit**, mais rarement **pourquoi**. Gridiron IQ cherche à répondre en quelques secondes aux questions utiles à l’antenne :

- Quelle formation et quel personnel ont été employés ?
- Quelle couverture la défense a-t-elle jouée ?
- Le quarterback a-t-il conservé le ballon trop longtemps ?
- La pression vient-elle de la protection ou du comportement du quarterback ?
- Le receveur était-il réellement ouvert au moment du lancer ?
- Le défenseur refermait-il rapidement la fenêtre de passe ?
- Quel duel bloqueur–pass rusher a décidé de l’action ?
- Cette action confirme-t-elle une tendance du match ou des semaines précédentes ?

L’interface privilégie des informations courtes, visuelles et formulables immédiatement par un commentateur.

## Fonctionnalités principales

- Navigation **semaine → match → action**.
- Scorebug de diffusion avec score pré-snap, quart-temps, horloge, down et distance.
- Replay aérien animé des 22 joueurs et du ballon.
- Lecture, pause et navigation sur la timeline du replay.
- Mode **Instant T** pour figer une frame et synchroniser toutes les métriques.
- Trajectoires du quarterback et de la cible probable.
- Identification des événements clés : snap, lancer, arrivée et fin du jeu.
- Analyse de la pression et de la distance pass rusher–quarterback.
- Analyse de la séparation et de la vitesse de fermeture du défenseur.
- Métrique expérimentale de **fenêtre de passe dynamique**.
- Tendances par formation, couverture, play action et pression.
- Assignations de protection et duels bloqueur–pass rusher issus de PFF.
- Classement des créateurs de pression du match.
- Fiche individuelle de déplacement pour chaque joueur.
- Insights automatiques rédigés pour une utilisation à l’antenne.
- Signalement des pénalités et des jeux annulés (`No Play`).

## Installation et lancement

### Prérequis

- Python 3.11 ou 3.12 recommandé.
- Windows PowerShell pour les commandes ci-dessous.
- Les fichiers de données présents dans `data/data`.

### 1. Créer un environnement virtuel

Avec le launcher Windows :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Ou avec `python3` si c’est la commande disponible sur la machine :

```powershell
python3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Installer les dépendances

```powershell
python3 -m pip install -r requirements.txt
```

Les versions sont épinglées dans `requirements.txt` pour rendre l’environnement reproductible.

### 3. Démarrer Streamlit

```powershell
python3 -m streamlit run .\app.py
```

Il ne faut pas utiliser `python3 .\app.py` : une application Streamlit doit être exécutée par le runtime Streamlit afin de disposer du serveur web, du cache, de l’état de session et des interactions.

L’application est ensuite disponible à l’adresse :

```text
http://localhost:8501
```

## Parcours utilisateur

La barre latérale pilote tout le dashboard :

1. **Semaine** : sélection d’une semaine de la saison 2021.
2. **Match** : sélection d’une rencontre de cette semaine.
3. **Action** : sélection d’un dropback, avec quart-temps, horloge, down, distance et résultat.
4. **Frame analysée** : choix d’un instant précis du tracking.
5. **Revenir au lancer** : repositionnement rapide sur la frame de lancer.

Changer de match charge uniquement le fichier de tracking correspondant. Le chargement est mis en cache afin d’éviter de relire les mêmes CSV à chaque interaction.

## Description détaillée des vues

### En-tête broadcast

L’en-tête reste visible au-dessus de toutes les vues. Il contient :

- équipes extérieure et domicile ;
- score avant l’action ;
- quart-temps et horloge ;
- down et yards à parcourir ;
- identifiant du jeu ;
- statut de simulation historique.

Six indicateurs donnent immédiatement le contexte de l’action :

- **Time to Throw** ;
- présence ou absence de pression PFF ;
- séparation de la cible au lancer ;
- durée de la fenêtre ouverte ;
- résultat officiel en yards ;
- couverture défensive.

### 1. Direct & Replay

Cette vue constitue l’écran principal du commentateur.

#### Replay automatique

Le terrain est représenté vu du dessus avec :

- attaque sous la couleur de l’équipe en possession ;
- défense sous la couleur de l’équipe adverse ;
- ballon sous forme de losange marron ;
- numéros de maillot à l’intérieur des marqueurs ;
- ligne de scrimmage en bleu ;
- ligne à atteindre en jaune ;
- cible probable cerclée en cyan.

Les contrôles Plotly permettent de lancer, suspendre ou déplacer le replay frame par frame. Le survol d’un joueur affiche son nom, son rôle PFF, sa vitesse et son accélération.

#### Analyse Instant T

Ce mode fige la visualisation sur la frame choisie dans la barre latérale. Il ajoute :

- la trajectoire passée du quarterback en jaune ;
- la trajectoire passée de la cible probable en cyan ;
- les positions exactes de tous les joueurs ;
- les statistiques calculées à cet instant.

Il permet au commentateur d’analyser précisément le snap, le lancer, l’arrivée du ballon ou n’importe quel moment intermédiaire.

#### Lecture tactique

Le panneau de droite affiche :

- événement de tracking actif ;
- temps depuis le snap ;
- formation offensive ;
- personnel offensif et défensif ;
- nombre de défenseurs dans la boîte ;
- couverture détaillée ;
- famille homme/zone/autre ;
- présence d’une play action.

#### Capteurs Instant T

Les capteurs sont recalculés pour la frame sélectionnée :

- pass rusher le plus proche ;
- distance entre ce rusher et le quarterback ;
- cible probable ;
- séparation cible–défenseur ;
- vitesse de fermeture ;
- score de fenêtre ;
- vitesse du quarterback.

La cible n’étant pas explicitement fournie dans les CSV, l’application affiche toujours le niveau de confiance de cette inférence.

#### Graphique poche et fenêtre

Deux courbes sont superposées :

- **orange** : distance entre le rusher le plus proche et le quarterback ;
- **cyan** : séparation entre la cible probable et le défenseur en couverture le plus proche.

Des repères verticaux identifient le snap, le lancer et le résultat de la passe. Le graphique montre donc simultanément la fermeture de la poche et l’ouverture de la fenêtre de passe.

#### Insights commentateur

Le moteur compose jusqu’à quatre observations courtes, par exemple :

- production offensive contre la couverture rencontrée ;
- présence et rapidité de la pression ;
- cible probable et durée de sa fenêtre ;
- pass rusher le plus proche à l’instant sélectionné.

Ces phrases sont conçues comme des aides à la préparation et non comme du texte à lire obligatoirement mot pour mot.

#### Description officielle

Un panneau repliable conserve le texte play-by-play original. Il signale également :

- les jeux annulés ;
- le type de pénalité ;
- les yards de pénalité ;
- l’écart entre résultat terrain et résultat officiel.

### 2. Tendances

Cette vue agrège les dropbacks de l’équipe en possession jusqu’à la semaine sélectionnée. Les semaines futures sont volontairement exclues afin de reproduire les informations dont un commentateur aurait réellement disposé à ce moment-là.

Les indicateurs principaux sont :

- nombre de dropbacks ;
- pourcentage de complétion ;
- yards par dropback ;
- taux de conversion ;
- pression subie ;
- fréquence de play action.

#### Couvertures affrontées

L’histogramme classe les couvertures par fréquence. La couleur encode l’efficacité en yards par jeu. Le tableau associé présente pour chaque couverture :

- volume de jeux ;
- pourcentage de complétion ;
- yards par jeu ;
- taux de pression ;
- taux de conversion.

#### Formations offensives

Le tableau des formations compare :

- nombre de jeux ;
- yards par jeu ;
- taux de conversion.

Cette vue permet par exemple d’identifier une formation rarement utilisée mais très productive, ou une couverture défensive qui pose régulièrement problème.

### 3. Duels & Protection

Cette vue se concentre sur la ligne offensive et le pass rush.

#### Pass rushers sur le jeu

Pour chaque défenseur dont le rôle PFF est `Pass Rush`, l’application affiche :

- nom ;
- position réelle à l’alignement ;
- impact crédité : hurry, hit, sack ou aucun impact.

#### Assignations de protection

Pour chaque bloqueur :

- nom et alignement ;
- premier rusher assigné par PFF ;
- type de bloc ;
- bloc battu ou non ;
- pression concédée ou non.

Les types de bloc incluent notamment protection standard, switch, chip, backfield pickup, play action protection et pocket roll.

#### Leaders de pression du match

Le classement agrège pour chaque pass rusher :

- rush snaps ;
- nombre de pressions ;
- sacks ;
- pourcentage de snaps avec pression.

Une pression correspond ici à au moins un `hurry`, `hit` ou `sack` crédité par PFF.

### 4. Joueurs

Cette vue permet de sélectionner n’importe quel joueur présent sur l’action.

Elle affiche :

- équipe ;
- rôle sur le jeu ;
- position à l’alignement ;
- vitesse maximale ;
- distance totale parcourue ;
- accélération maximale ;
- trajectoire complète sur le terrain.

La couleur de la trajectoire évolue avec la vitesse. Le survol de chaque point indique la frame et la vitesse instantanée.

### 5. Méthode

Cette vue explique directement dans l’application :

- les données structurées disponibles ;
- les métriques calculées ;
- les métriques inférées ;
- les hypothèses temporelles ;
- les limitations du corpus ;
- la différence entre annotations PFF et métriques internes.

Son objectif est d’éviter qu’une métrique expérimentale soit présentée à l’antenne comme une statistique NFL officielle.

## Statistiques et métriques

### Métriques directement observées

| Métrique | Source | Utilisation |
|---|---|---|
| Down, distance, horloge, score | `plays.csv` | Contexte du jeu |
| Formation et personnel | `plays.csv` | Lecture pré-snap |
| Défenseurs dans la boîte | `plays.csv` | Structure défensive |
| Couverture et famille | PFF dans `plays.csv` | Explication tactique |
| Play action | PFF dans `plays.csv` | Comparaison play action / dropback classique |
| Résultat de passe | `plays.csv` | Complétion, incompletion, sack, interception, scramble |
| Yards avant/après pénalité | `plays.csv` | Impact réel et officiel |
| Hurries, hits et sacks | `pffScoutingData.csv` | Création de pression |
| Pressions concédées | `pffScoutingData.csv` | Évaluation de la protection |
| Position, vitesse, accélération | Tracking | Replay et analyse biomécanique |

### Time to Throw

Temps entre la frame du snap et la frame de passe :

```text
Time to Throw = (frame_lancer - frame_snap) × 0,1 seconde
```

La valeur n’est pas affichée sur les sacks et scrambles sans passe afin de ne pas créer un faux temps de lancer.

### Pourcentage de complétion

```text
Completion % = passes complétées / tentatives
```

Les tentatives comprennent les passes complétées, incomplètes et interceptées. Les sacks et scrambles restent des dropbacks, mais pas des tentatives de passe.

### Yards par dropback

```text
Yards par dropback = somme des yards officiels / nombre de dropbacks
```

Les tendances utilisent `playResult`, qui inclut l’effet officiel des pénalités.

### Taux de conversion

```text
Conversion = playResult ≥ yardsToGo
Taux de conversion = conversions / jeux
```

Il s’agit d’un indicateur interne simple, et non de l’Expected Points Added ou du Success Rate officiel.

### Pressure Rate

```text
Pression = au moins un hurry, hit ou sack PFF sur le jeu
Pressure Rate = jeux avec pression / dropbacks
```

### Pass-rusher Pressure Rate

```text
Pressure Rate joueur = pressions créditées / rush snaps
```

Le volume de snaps doit toujours accompagner ce pourcentage afin d’éviter les conclusions sur un échantillon trop faible.

### Séparation de la cible

Pour une frame donnée :

```text
Séparation = min(distance euclidienne entre la cible et chaque défenseur en Coverage)
```

Les coordonnées `x` et `y` sont exprimées en yards.

### Vitesse de fermeture

```text
Vitesse de fermeture = - variation(séparation) / 0,1 seconde
```

Une valeur positive signifie que le défenseur réduit la distance. Le signal est limité à une plage raisonnable pour contenir les pics de bruit du tracking.

### Cible probable

Le dataset ne possède pas de colonne `targetReceiverId`. La cible est donc estimée ainsi :

1. identifier la frame d’arrivée ou de résultat ;
2. récupérer la position du ballon ;
3. sélectionner le joueur en `Pass Route` le plus proche ;
4. convertir sa distance au ballon en niveau de confiance.

Aucune cible n’est inférée sur un sack ou un scramble sans passe.

### Durée de fenêtre ouverte

```text
Fenêtre ouverte = séparation ≥ 3 yards
Durée = nombre de frames ouvertes × 0,1 seconde
```

Le seuil de 3 yards est une convention interne explicable et modifiable, pas une définition NFL officielle.

### Dynamic Passing Window Score

Le score expérimental combine l’espace disponible et la vitesse à laquelle cet espace disparaît :

```text
Window Score = max(0, séparation - 0,35 × max(0, vitesse de fermeture))
```

Interprétation :

- score élevé : cible ouverte et espace relativement stable ;
- score moyen : cible ouverte mais défenseur en train de fermer ;
- score faible : fenêtre réduite ou en disparition rapide.

Ce score sert à comparer des instants d’un même jeu. Il n’est pas calibré comme une probabilité de complétion.

### Distance rusher–quarterback

Pour chaque frame :

```text
Distance pression = min(distance entre le quarterback et chaque joueur en Pass Rush)
```

Le nom du défenseur associé est affiché pour faciliter le commentaire du replay.

### Distance parcourue

```text
Distance totale = somme de dis pour toutes les frames du joueur
```

`dis` représente le déplacement depuis la frame précédente.

## Provenance et niveau de confiance

Gridiron IQ distingue trois catégories :

| Catégorie | Exemples | Présentation |
|---|---|---|
| Donnée structurée | score, down, formation, yards | Valeur directe |
| Annotation PFF | couverture, rôle, hurry, sack | Mention PFF |
| Inférence interne | cible, séparation cible, fenêtre | Niveau de confiance et méthodologie |

Cette distinction est importante : une inférence utile ne doit pas être transformée en fait officiel sans validation.

## Données utilisées

### `games.csv`

Une ligne par match : saison, semaine, date et équipes.

### `plays.csv`

Une ligne par dropback : contexte, résultat, pénalités, formation, personnel, type de dropback, play action et couverture.

### `players.csv`

Informations d’identité : nom, poste, taille, poids, date de naissance et université.

### `pffScoutingData.csv`

Une ligne par joueur et par jeu : rôle, position à l’alignement, impacts de pression, responsabilité de protection, joueur bloqué et type de bloc.

### `tracking/tracking_[gameId].csv`

Une ligne par joueur et par frame : position, vitesse, accélération, déplacement, orientation, direction et événement. Les lignes dont `team == "football"` correspondent au ballon.

### Clés de jointure

```text
games.gameId → plays.gameId
plays.(gameId, playId) → scouting.(gameId, playId)
plays.(gameId, playId) → tracking.(gameId, playId)
players.nflId → scouting.nflId / tracking.nflId
```

## Architecture

```text
.
├── app.py                       # Navigation et composition des vues Streamlit
├── requirements.txt             # Dépendances Python épinglées
├── .streamlit/
│   └── config.toml              # Thème et configuration Streamlit
├── src/
│   ├── __init__.py
│   ├── data_loader.py           # Lecture, typage et cache des CSV
│   ├── analytics.py             # Keyframes, métriques, agrégations et inférences
│   ├── visualizations.py        # Terrain, replay et graphiques Plotly
│   └── components.py            # Scorebug, panneaux et design system
└── data/
    └── data/
        ├── games.csv
        ├── plays.csv
        ├── players.csv
        ├── pffScoutingData.csv
        └── tracking/
            └── tracking_[gameId].csv
```

### Flux de traitement

```text
Sélection utilisateur
        ↓
Chargement du match et de son tracking
        ↓
Filtrage du playId
        ↓
Jointure tracking + joueurs + rôles PFF
        ↓
Détection snap / lancer / résultat
        ↓
Inférence de cible et calcul frame par frame
        ↓
Visualisations et insights commentateur
```

### Performances

- Les tables principales sont mises en cache avec `st.cache_data`.
- Le tracking est chargé par match et non pour les 122 matchs simultanément.
- Le cache de tracking conserve un nombre limité de matchs pour contrôler la mémoire.
- Les agrégations d’équipe sont recalculées à partir des semaines autorisées seulement.

## Limites analytiques

- Le corpus contient uniquement les jeux de passe/dropbacks, pas tous les snaps.
- Les semaines disponibles sont limitées à 1–8 de la saison 2021.
- Les cibles, routes, air yards et YAC ne sont pas fournis sous forme structurée.
- Les événements de tracking peuvent être absents ou varier selon les jeux.
- La cadence de 0,1 seconde par frame est l’hypothèse attendue du tracking et doit être contrôlée avant un usage de production.
- Les angles et accélérations peuvent contenir du bruit.
- Les jeux annulés restent visualisables, mais sont exclus des tendances.
- L’EPA, le WPA, la probabilité de victoire et les statistiques de drives nécessitent un play-by-play complet supplémentaire.
- Le dashboard n’est pas connecté à une API live.

## Dépannage

### `missing ScriptRunContext` ou `No runtime found`

Cause : l’application a été lancée avec :

```powershell
python3 .\app.py
```

Correction :

```powershell
python3 -m streamlit run .\app.py
```

### `No module named streamlit`

```powershell
python3 -m pip install -r requirements.txt
```

Vérifier ensuite que `pip` et Streamlit utilisent le même interpréteur :

```powershell
python3 -m pip show streamlit
python3 -m streamlit --version
```

### Fichier de tracking introuvable

Vérifier la présence d’un fichier correspondant au match :

```text
data/data/tracking/tracking_[gameId].csv
```

### Le chargement est lent au premier affichage

C’est normal : le premier accès lit les CSV et construit les métriques. Les interactions suivantes utilisent le cache Streamlit.

## Évolutions possibles

- Connexion à un véritable flux play-by-play et tracking live.
- Modèle de Completion Probability et CPOE interne.
- Classification automatique des routes.
- Responsabilité partagée des sacks entre ligne, couverture et quarterback.
- Détection géométrique des doubles équipes et stunts.
- Comparaisons joueur/équipe ajustées à l’adversaire.
- Export automatique d’une fiche commentateur avant match.
- Génération d’un clip vidéo ou GIF du replay.

---

**Gridiron IQ** transforme le tracking brut en une question simple et utile à l’antenne : **pourquoi cette action a-t-elle réussi ou échoué ?**
