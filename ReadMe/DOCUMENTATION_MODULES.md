# 📚 Documentation Complète du Dossier `modules/`

Le dossier `modules/` contient **7 fichiers** qui forment le cœur du système de contrôle de feux de circulation par apprentissage par renforcement. Voici une explication détaillée de chaque fichier.

---

## 📁 Structure du Dossier

```
modules/
├── __init__.py                # Initialisation du package
├── environment.py             # Environnement de simulation SUMO
├── observation.py             # Système d'observation modulaire (33 KB)
├── reward.py                  # Système de récompenses modulaire (22 KB)
├── config_loader.py           # Chargement de configuration
├── logging_config.py          # Configuration des logs
└── logging_utils.py           # Utilitaires de logging (17 KB)
```

---

## 1️⃣ `__init__.py` - Initialisation du Package

**Taille** : 384 bytes  
**Rôle** : Définit le package `modules` et expose les modules disponibles

### Contenu
```python
__all__ = [
    'environment',
    'observation',
    'reward',
    'config_loader',
    'logging_config',
    'logging_utils',
]
```

### Utilité
Permet d'importer facilement les modules :
```python
from modules.environment import Environment
from modules.observation import CombinedObservation
from modules.reward import CombinedReward
```

---

## 2️⃣ `environment.py` - Environnement de Simulation

**Taille** : 5,158 bytes  
**Rôle** : Wrapper autour de SUMO-RL pour créer l'environnement de simulation

### 🎯 Classes Principales

#### `NeighborCombinedObservation`
Observation personnalisée qui inclut :
- ✅ Files d'attente par voie
- ✅ Temps d'attente
- ✅ Véhicules approchant (wave)
- ✅ Phase actuelle du feu
- ✅ **Véhicules d'urgence** (détection)
- ✅ **Informations des voisins** (intersections adjacentes)
  - Phases des voisins
  - Files d'attente des voisins
  - Temps d'attente des voisins
  - Actions des voisins

#### `Environment`
Classe principale qui encapsule l'environnement SUMO.

**Paramètres d'initialisation** :
- `use_emergency_vehicles` : Active les véhicules d'urgence (5% du trafic)
- `use_gui` : Affiche l'interface graphique SUMO

**Configuration SUMO** :
```python
sumo_rl.SumoEnvironment(
    net_file='configuration_files/grid4x4.net.xml',
    route_file=route_file,
    observation_class=NeighborCombinedObservation,
    reward_fn=combined_reward_wrapper,
    delta_time=10,        # Intervalle de décision (10s)
    yellow_time=5,        # Durée du feu jaune (5s)
    min_green=10,         # Durée min du vert (10s)
    max_green=50,         # Durée max du vert (50s)
    num_seconds=1800      # Durée d'un épisode (30 min)
)
```

**Méthodes** :
- `reset()` : Réinitialise l'environnement
- `step(actions)` : Exécute une action et retourne le nouvel état
- `close()` : Ferme proprement SUMO

### 🔧 Fonction Utilitaire

#### `combined_reward_wrapper(ts)`
Wrapper qui maintient une instance de récompense par feu de circulation.

---

## 3️⃣ `observation.py` - Système d'Observation Modulaire

**Taille** : 33,335 bytes (900 lignes)  
**Rôle** : Framework flexible pour définir différentes stratégies d'observation

### 🏗️ Architecture

```
ObservationFunction (Classe abstraite)
    ├── QueueObservation
    ├── WaitingTimeObservation
    ├── WaveObservation
    ├── PhaseObservation
    ├── EmergencyVehicleObservation
    ├── NeighborObservation
    └── CombinedObservation
```

### 📊 Classes d'Observation

#### 1. `ObservationFunction` (Classe de base abstraite)
Interface que toutes les observations doivent implémenter.

**Méthodes abstraites** :
- `observation_space()` : Définit l'espace d'observation (Gymnasium)
- `compute()` : Calcule l'observation actuelle
- `get_observation_size()` : Retourne la dimension de l'observation

#### 2. `QueueObservation`
Observe le nombre de véhicules à l'arrêt (vitesse = 0) par voie.

**Sortie** : `[queue_lane1, queue_lane2, ..., queue_laneN]`

#### 3. `WaitingTimeObservation`
Observe le temps d'attente cumulé des véhicules par voie.

**Sortie** : `[wait_lane1, wait_lane2, ..., wait_laneN]`

#### 4. `WaveObservation`
Observe le nombre total de véhicules approchant par voie.

**Sortie** : `[wave_lane1, wave_lane2, ..., wave_laneN]`

#### 5. `PhaseObservation`
Observe la phase actuelle du feu (encodage one-hot).

**Sortie** : `[0, 0, 1, 0]` (si phase 2 active sur 4 phases)

#### 6. `EmergencyVehicleObservation`
Détecte la présence de véhicules d'urgence par voie.

**Sortie** : `[0, 1, 0, 0]` (véhicule d'urgence sur voie 2)

#### 7. `NeighborObservation`
Observe l'état des intersections voisines (dans un rayon de 1).

**Informations collectées** :
- Phases des voisins
- Files d'attente des voisins
- Temps d'attente des voisins
- Actions récentes des voisins

#### 8. `CombinedObservation` ⭐
**La plus importante** - Combine plusieurs observations en une seule.

**Paramètres configurables** :
```python
CombinedObservation(
    traffic_signal,
    include_queue=True,
    include_waiting_time=True,
    include_wave=True,
    include_phase=True,
    include_emergency=True,
    include_neighbors=True,
    neighbor_distance=1,
    normalize=True
)
```

**Dimension typique** : ~490-500 valeurs par agent (selon le nombre de voies et voisins)

---

## 4️⃣ `reward.py` - Système de Récompenses Modulaire

**Taille** : 22,270 bytes (686 lignes)  
**Rôle** : Framework flexible pour définir différentes stratégies de récompense

### 🏗️ Architecture

```
RewardFunction (Classe abstraite)
    ├── QueueReward
    ├── WaitingTimeReward
    ├── DelayReward
    ├── ThroughputReward
    ├── EmergencyVehicleReward
    └── CombinedReward
```

### 💰 Classes de Récompense

#### 1. `RewardFunction` (Classe de base abstraite)
Interface pour toutes les fonctions de récompense.

**Méthodes abstraites** :
- `compute()` : Calcule la récompense
- `reset()` : Réinitialise l'état interne

#### 2. `QueueReward`
Pénalise le nombre de véhicules en file d'attente.

**Formule** : `reward = -sum(queue_lengths)`

#### 3. `WaitingTimeReward`
Pénalise le temps d'attente cumulé.

**Formule** : `reward = -sum(waiting_times)`

#### 4. `DelayReward`
Récompense la réduction du délai.

**Formule** : `reward = -(current_delay - previous_delay)`

#### 5. `ThroughputReward`
Récompense le nombre de véhicules servis.

**Formule** : `reward = vehicles_passed`

#### 6. `EmergencyVehicleReward`
Récompense fortement la priorité aux véhicules d'urgence.

**Formule** : 
```python
if emergency_vehicle_waiting:
    reward = -1000  # Pénalité forte
else:
    reward = +100   # Bonus si passage rapide
```

#### 7. `CombinedReward` ⭐
**La plus importante** - Combine plusieurs récompenses avec des poids.

**Configuration** :
```python
CombinedReward(
    traffic_signal,
    queue_weight=0.5,
    waiting_time_weight=0.3,
    emergency_weight=0.2,
    normalize=False
)
```

**Formule** :
```python
reward = (queue_weight * queue_reward +
          waiting_time_weight * waiting_time_reward +
          emergency_weight * emergency_reward)
```

---

## 5️⃣ `config_loader.py` - Chargement de Configuration

**Taille** : 8,044 bytes (285 lignes)  
**Rôle** : Charge et gère la configuration depuis YAML et variables d'environnement

### 🎯 Fonctionnalités

#### Priorité de Configuration
1. **Variables d'environnement** (`ORABAN_*`) - Priorité la plus haute
2. **Fichier YAML** (`config.yaml`)
3. **Valeurs par défaut** (dans le code)

#### Configuration par Défaut
```python
DEFAULT_CONFIG = {
    'environment': {
        'delta_time': 10,
        'yellow_time': 5,
        'min_green': 10,
        'max_green': 50,
        'num_seconds': 1800,
    },
    'training': {
        'num_parallel_envs': 4,
        'learning_rate': 0.0003,
        'batch_size': 256,
        'epsilon_decay': 0.994,
    },
    'logging': {
        'level': 'INFO',
        'log_to_file': True,
    }
}
```

### 📦 Dataclasses

#### `EnvironmentConfig`
Configuration typée pour l'environnement SUMO.

#### `TrainingConfig`
Configuration typée pour l'entraînement.

### 🔧 Fonctions Principales

#### `load_config(config_path=None)`
Charge la configuration complète.

**Exemple** :
```python
from modules.config_loader import load_config
config = load_config()
print(config['training']['learning_rate'])  # 0.0003
```

#### `get_config()`
Retourne la configuration globale (singleton).

#### `get_environment_config()`
Retourne la config d'environnement en tant que dataclass.

#### `get_training_config()`
Retourne la config d'entraînement en tant que dataclass.

### 🌍 Variables d'Environnement

**Exemple d'override** :
```bash
# Changer le learning rate
ORABAN_TRAINING__LEARNING_RATE=0.001 python train_custom_multienv.py

# Activer le debug
ORABAN_LOGGING__LEVEL=DEBUG python train_custom_multienv.py
```

---

## 6️⃣ `logging_config.py` - Configuration des Logs

**Taille** : 4,734 bytes (154 lignes)  
**Rôle** : Configure le système de logging avec couleurs et rotation

### 🎨 Fonctionnalités

#### Logs Colorés
```
DEBUG    → Gris
INFO     → Vert
WARNING  → Jaune
ERROR    → Rouge
CRITICAL → Magenta
```

#### Rotation des Fichiers
- Taille max par fichier : 10 MB (configurable)
- Nombre de backups : 5 (configurable)
- Fichier principal : `logs/oraban.log`

### 🔧 Fonctions Principales

#### `setup_logging(...)`
Configure le système de logging complet.

**Paramètres** :
```python
setup_logging(
    log_dir="logs",
    log_level="INFO",
    log_to_file=True,
    log_to_console=True,
    max_file_size_mb=10,
    backup_count=5,
    use_colors=True
)
```

#### `get_logger(name)`
Obtient un logger avec un nom spécifique.

**Exemple** :
```python
from modules.logging_config import get_logger
logger = get_logger("oraban.mymodule")
logger.info("Training started")
logger.warning("Low GPU memory")
```

### 📝 Loggers Pré-configurés

```python
from modules.logging_config import (
    environment_logger,
    observation_logger,
    reward_logger,
    training_logger,
    agent_logger
)
```

---

## 7️⃣ `logging_utils.py` - Utilitaires de Logging

**Taille** : 17,441 bytes  
**Rôle** : Fonctions utilitaires avancées pour le logging (métriques, progression, etc.)

> **Note** : Ce fichier contient probablement des utilitaires supplémentaires comme des barres de progression, formatage de métriques, etc.

---

## 🔗 Comment Tout S'Intègre

### Flux de Données

```
1. config_loader.py
   ↓ Charge la configuration
   
2. logging_config.py
   ↓ Configure les logs
   
3. environment.py
   ↓ Crée l'environnement SUMO
   ├── observation.py (définit ce que l'agent voit)
   └── reward.py (définit les récompenses)
   
4. train_custom_multienv.py
   ↓ Utilise tout pour entraîner les agents
```

### Exemple d'Utilisation Complète

```python
# 1. Charger la config
from modules.config_loader import get_config
config = get_config()

# 2. Initialiser les logs
from modules.logging_config import init_logging
init_logging(log_level="INFO")

# 3. Créer l'environnement
from modules.environment import Environment
env = Environment(
    use_emergency_vehicles=True,
    use_gui=False
)

# 4. Réinitialiser
observations, info = env.reset()

# 5. Boucle d'entraînement
for step in range(1000):
    # Choisir des actions (aléatoires ici)
    actions = {agent: env.action_spaces[agent].sample() 
               for agent in env.agents}
    
    # Exécuter
    obs, rewards, terms, truncs, infos = env.step(actions)
    
    # Les observations viennent de observation.py
    # Les récompenses viennent de reward.py

# 6. Fermer
env.close()
```

---

## 📊 Résumé des Dimensions

| Fichier | Lignes | Taille | Classes | Rôle Principal |
|---------|--------|--------|---------|----------------|
| `__init__.py` | 17 | 384 B | 0 | Initialisation package |
| `environment.py` | 131 | 5 KB | 2 | Wrapper SUMO |
| `observation.py` | 900 | 33 KB | 8+ | Observations modulaires |
| `reward.py` | 686 | 22 KB | 7+ | Récompenses modulaires |
| `config_loader.py` | 285 | 8 KB | 2 | Configuration |
| `logging_config.py` | 154 | 5 KB | 2 | Logging |
| `logging_utils.py` | ? | 17 KB | ? | Utilitaires logging |

---

## 🎯 Points Clés à Retenir

1. **Modularité** : Chaque aspect (observation, récompense) est modulaire et interchangeable
2. **Flexibilité** : Facile d'ajouter de nouvelles observations ou récompenses
3. **Configuration** : Tout est configurable via YAML ou variables d'environnement
4. **Logging** : Système de logging professionnel avec couleurs et rotation
5. **Voisinage** : Support natif de la communication entre intersections voisines
6. **Urgences** : Gestion spéciale des véhicules d'urgence

---

**Cette architecture permet d'expérimenter facilement avec différentes configurations sans modifier le code !** 🚀
