# SENTRAFIK — BRT Dakar (Configuration & Scénarios)

Ce dossier (`current_config`) contient les fichiers de simulation SUMO, les modèles IA et les scripts de contrôle des feux de circulation pour le projet SENTRAFIK, visant à optimiser le trafic et donner la priorité au BRT (Bus Rapid Transit) à Dakar.

## 📁 Structure du projet

La structure a été récemment réorganisée pour séparer clairement la configuration de la logique d'exécution :

*   `config/` : Les fichiers vitaux pour SUMO (`brt.sumocfg`, `output.net.xml`, `brt_road.rou.xml`, etc.).
*   `scenarios/` : Tous les scripts Python permettant d'exécuter la simulation avec différents niveaux d'intelligence.
*   `Model/` : Modèles de Machine Learning pré-entraînés (ex. `policier_model_generic_v2.pkl`).
*   `data/` : Dossier de sortie pour les résultats (fichiers `.xlsx`) et modèles FQI.
*   `logs/` : Fichiers de suivi et logs d'entraînement.
*   `tools/` : Outils auxiliaires pour la génération de véhicules et la visualisation.

---

## 🚀 Prérequis

Tous les scripts nécessitent l'environnement virtuel du projet contenant des dépendances spécifiques (comme `numpy`, `joblib`, `openpyxl`).

**Activation de l'environnement virtuel :**
(À lancer depuis la racine du projet SENTRAFIK)
```bash
source .venv/bin/activate
```
*Si vous êtes déjà dans ce dossier (`current_config`), vous pouvez utiliser `../../.venv/bin/python` au lieu de `python` pour lancer les scripts.*

---

## 🚦 Exécution des Scénarios

Chaque scénario s'exécute depuis ce dossier (`current_config`). Vous pouvez utiliser l'option `--no-gui` pour exécuter les simulations en arrière-plan sans ouvrir l'interface SUMO (beaucoup plus rapide).

### Scénario 1 : Baseline (Temps fixe)
Ce scénario de référence (Baseline) lance la simulation avec les feux configurés en mode statique classique.

```bash
python scenarios/scenario1_baseline.py
# Ou sans interface graphique :
python scenarios/scenario1_baseline.py --no-gui
```
*Sortie : `data/scenario1/traffic_metrics_results.xlsx`*

### Scénario 2 : Policier Intelligent (Système de Règles)
Un agent intelligent observe l'approche du BRT et force le feu au vert selon des règles de priorité prédéfinies.

```bash
python scenarios/scenario2_policier.py
# Ou sans interface graphique :
python scenarios/scenario2_policier.py --no-gui
```
*Sortie : `data/scenario2/scenario2_results.xlsx`*

### Scénario 2 bis : Policier Machine Learning (IA)
Une version évoluée du policier qui utilise un modèle d'IA (Random Forest / Scikit-learn) pour anticiper et optimiser les temps de feu à l'approche des bus.

```bash
python scenarios/scenario2_policier_ml.py
# Ou sans interface graphique :
python scenarios/scenario2_policier_ml.py --no-gui
```

### Scénario 3 : Multi-Agent Reinforcement Learning (FQI)
Ce scénario utilise l'apprentissage par renforcement (Fitted Q-Iteration). Il est décomposé en 3 étapes :

**1. Collecte des données (Exploration)**
```bash
# Lancer la collecte pour 1 épisode
python scenarios/scenario3_fqi_collector.py --episodes 1
```
*Sortie : `data/transitions.pkl`*

**2. Entraînement du modèle (Offline)**
```bash
# Entraîner le modèle FQI sur 8 itérations
python scenarios/scenario3_fqi_train.py --iterations 8
```
*Sortie : les modèles seront sauvegardés dans `data/fqi_models/`*

**3. Évaluation du modèle entraîné**
```bash
# Lancer la simulation pour évaluer la politique apprise par l'IA
python scenarios/scenario3_fqi_eval.py
```
*Sortie : `data/scenario3/scenario3_fqi_results.xlsx`*

---

## 🛠️ Outils Utilitaires

### Générateur de trafic
Regénère la demande de trafic (`current_state.rou.xml`) en se basant sur les flux existants.
```bash
python tools/vehicules_generator.py
```

### Visualisation des résultats
Ce script lit les fichiers Excel générés dans le dossier `data/` et génère des graphiques comparatifs globaux et radars pour analyser la performance de l'IA face aux autres scénarios.
```bash
python tools/visualize_results.py
```
*Sortie : les graphiques sont sauvegardés dans `data/graphiques/`*
