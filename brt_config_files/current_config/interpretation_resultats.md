# Interprétation des Résultats de Simulation (MARL FQI)

Ce document analyse les performances du système de gestion de trafic Multi-Agent (MARL) basé sur l'algorithme Fitted Q-Iteration (FQI) pour le réseau BRT de Dakar.

---

## 1. Comparatif Global des Scénarios (`01_comparatif_global.png`)
**Analyse :** Ce graphique valide la supériorité du MARL FQI sur les métriques macroscopiques.
*   **Vitesse Réseau** : Le MARL FQI atteint **22,3 km/h**, soit une amélioration de **67%** par rapport à la Baseline statique (13,4 km/h).
*   **Vitesse BRT** : On observe une vitesse stable à **27,1 km/h**, dépassant l'objectif contractuel de 25 km/h sans paralyser les autres usagers (contrairement au scénario "Policier").
*   **Fiabilité** : Les téléportations (indicateurs de blocages critiques) chutent de **241 à 83**, prouvant que l'IA prévient activement les congestions sévères.

## 2. Dynamique Collective MARL (`02_marl_collective_dynamics.png`)
**Analyse :** Ce graphique illustre la **synergie** entre les 150 agents.
*   La **Récompense Cumulée** (courbe verte) montre une croissance logarithmique typique d'un apprentissage réussi : les agents s'accordent de mieux en mieux au fil du temps.
*   La **Congestion Globale** (pointillés rouges) diminue en miroir de la récompense. Cela prouve que l'objectif mathématique (maximiser la récompense) se traduit concrètement par une réduction physique des bouchons dans la ville.

## 3. Performance Individuelle des Agents (`03_marl_agents_rewards.png`)
**Analyse :** Ce graphique montre l'hétérogénéité du réseau.
*   Chaque barre représente l'un des 150 agents. Le gradient (Rouge vers Vert) indique que certains carrefours sont intrinsèquement plus difficiles à gérer (zones de forte densité).
*   **Conclusion** : L'architecture décentralisée permet à chaque agent de développer une expertise spécifique à son carrefour, plutôt que d'imposer une règle uniforme et inefficace.

## 4. Analyse Multi-Critères (`04_marl_radar.png`)
**Analyse :** Le diagramme en toile d'araignée montre l'équilibre du modèle.
*   Le MARL FQI (vert) couvre la plus grande surface, signifiant qu'il est performant sur **tous les axes simultanément** (Vitesse, Écologie, Attente).
*   La Baseline (gris) est limitée, et le Policier (rouge) est très déséquilibré (excellent pour le BRT mais médiocre pour le réseau global).

## 5. Distribution des Temps d'Attente (`05_waiting_distribution.png`)
**Analyse :** Ce graphique traite de l'équité et de la prévisibilité du trafic.
*   La courbe FQI est fortement déplacée vers la gauche, avec une "traîne" très courte.
*   **Impact** : Cela signifie que le système a pratiquement **éliminé les attentes extrêmes** (supérieures à 300s). Pour l'usager, cela se traduit par un trajet plus fiable et moins de stress.

## 6. Importance des Variables (`06_feature_importance.png`)
**Analyse :** "L'ouverture de la boîte noire" du modèle.
*   **Action Choisie** : C'est la variable dominante, confirmant que le modèle a bien appris l'impact de ses décisions de changement de phase.
*   **Voisins & BRT** : L'importance significative des variables "Voisin" et "Présence BRT" démontre que le système est réellement **coopératif** et **sensible à la priorité des transports en commun**.

---

### 💡 Conclusion pour la thèse
L'approche MARL FQI décentralisée transforme le réseau routier en un organisme vivant capable d'auto-organisation. Elle réconcilie deux objectifs souvent opposés : la **priorité au transport de masse (BRT)** et la **fluidité du trafic général**, tout en assurant une résilience face aux congestions critiques.
