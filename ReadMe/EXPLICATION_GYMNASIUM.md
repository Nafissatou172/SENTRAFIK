# 🏋️ Qu'est-ce que Gymnasium ?

## 📖 Définition

**Gymnasium** (anciennement OpenAI Gym) est une bibliothèque Python standard pour l'apprentissage par renforcement (Reinforcement Learning). C'est le **framework de référence** utilisé par la communauté RL.

**Site officiel** : https://gymnasium.farama.org/

---

## 🎯 Rôle de Gymnasium

Gymnasium fournit une **interface standardisée** pour créer et interagir avec des environnements d'apprentissage par renforcement.

### Concept Clé : L'Interface Agent-Environnement

```
┌─────────┐                    ┌──────────────┐
│  Agent  │ ─── action ───────>│ Environnement│
│  (IA)   │                    │   (Monde)    │
│         │ <── observation ───│              │
│         │ <── reward ────────│              │
└─────────┘                    └──────────────┘
```

---

## 🔧 Les 5 Méthodes Essentielles

Tout environnement Gymnasium doit implémenter ces méthodes :

### 1. `reset()` - Réinitialiser
```python
observation, info = env.reset()
```
- **Quand** : Au début de chaque épisode
- **Retourne** : État initial de l'environnement
- **Exemple** : Dans votre projet, réinitialise la simulation SUMO

### 2. `step(action)` - Exécuter une Action
```python
observation, reward, terminated, truncated, info = env.step(action)
```
- **Quand** : À chaque pas de temps
- **Paramètre** : `action` - L'action choisie par l'agent
- **Retourne** :
  - `observation` : Nouvel état après l'action
  - `reward` : Récompense obtenue
  - `terminated` : Episode terminé naturellement ?
  - `truncated` : Episode arrêté artificiellement ?
  - `info` : Informations supplémentaires (debug)

### 3. `render()` - Visualiser
```python
env.render()
```
- **Quand** : Pour afficher l'environnement (optionnel)
- **Exemple** : Afficher la simulation SUMO avec GUI

### 4. `close()` - Fermer
```python
env.close()
```
- **Quand** : À la fin, pour libérer les ressources
- **Exemple** : Fermer la connexion SUMO

### 5. `action_space` & `observation_space` - Espaces
```python
print(env.action_space)      # Discrete(4) ou Box(...)
print(env.observation_space)  # Box(low=0, high=1, shape=(498,))
```
- **Rôle** : Définir les dimensions et limites des actions/observations

---

## 📦 Types d'Espaces dans Gymnasium

### `Discrete(n)` - Actions Discrètes
```python
from gymnasium.spaces import Discrete

# 4 actions possibles : 0, 1, 2, 3
action_space = Discrete(4)

# Dans votre projet : 4 phases de feu
# Action 0 = Phase Nord-Sud
# Action 1 = Phase Est-Ouest
# Action 2 = Phase Nord-Sud + Tournant
# Action 3 = Phase Est-Ouest + Tournant
```

### `Box` - Valeurs Continues
```python
from gymnasium.spaces import Box
import numpy as np

# Observations continues (ex: vitesses, positions)
observation_space = Box(
    low=0.0,           # Valeur minimale
    high=1.0,          # Valeur maximale
    shape=(498,),      # 498 valeurs
    dtype=np.float32
)

# Dans votre projet : 
# - Files d'attente normalisées [0, 1]
# - Temps d'attente normalisés [0, 1]
# - Phases encodées [0, 1]
```

### `Dict` - Espaces Composés
```python
from gymnasium.spaces import Dict, Discrete, Box

# Pour multi-agents
observation_space = Dict({
    'agent_1': Box(low=0, high=1, shape=(498,)),
    'agent_2': Box(low=0, high=1, shape=(496,)),
    # ... 16 agents dans votre projet
})
```

---

## 🚦 Exemple Concret : Votre Projet

### Dans `modules/environment.py`

```python
class Environment:
    def __init__(self, ...):
        # Crée l'environnement SUMO-RL (compatible Gymnasium)
        self.env = sumo_rl.SumoEnvironment(...)
        
        # Définit les espaces pour chaque agent
        self.action_spaces = {
            'A0': Discrete(4),  # 4 phases possibles
            'A1': Discrete(5),  # 5 phases possibles
            # ... pour les 16 intersections
        }
        
        self.observation_spaces = {
            'A0': Box(low=0, high=1, shape=(498,)),
            'A1': Box(low=0, high=1, shape=(499,)),
            # ... dimensions différentes par intersection
        }
    
    def reset(self):
        """Réinitialise la simulation SUMO"""
        observations = self.env.reset()
        return observations, {}
    
    def step(self, actions):
        """
        Exécute les actions de tous les agents
        
        actions = {
            'A0': 2,  # Intersection A0 choisit phase 2
            'A1': 0,  # Intersection A1 choisit phase 0
            # ... pour les 16 intersections
        }
        """
        obs, rewards, terms, infos = self.env.step(actions)
        truncs = {agent: False for agent in self.agents}
        return obs, rewards, terms, truncs, infos
```

### Utilisation dans l'Entraînement

```python
from modules.environment import Environment

# 1. Créer l'environnement
env = Environment(use_emergency_vehicles=True, use_gui=False)

# 2. Réinitialiser
observations, info = env.reset()
# observations = {
#     'A0': array([0.2, 0.5, ..., 0.1]),  # 498 valeurs
#     'A1': array([0.3, 0.4, ..., 0.2]),  # 499 valeurs
#     ...
# }

# 3. Boucle d'interaction
for step in range(1800):  # 1800 pas = 30 minutes
    # Agent choisit des actions
    actions = {
        agent: agent_network.select_action(observations[agent])
        for agent in env.agents
    }
    # actions = {'A0': 2, 'A1': 0, 'A2': 1, ...}
    
    # Exécuter dans l'environnement
    obs, rewards, terms, truncs, infos = env.step(actions)
    
    # Apprendre des résultats
    for agent in env.agents:
        agent_network.learn(
            state=observations[agent],
            action=actions[agent],
            reward=rewards[agent],
            next_state=obs[agent]
        )
    
    observations = obs

# 4. Fermer
env.close()
```

---

## 🎓 Pourquoi Gymnasium est Important

### 1. **Standardisation**
Tous les environnements RL suivent la même interface → code réutilisable

### 2. **Compatibilité**
Fonctionne avec toutes les bibliothèques RL :
- Stable-Baselines3
- RLlib (Ray)
- TensorFlow Agents
- Votre code personnalisé (comme Co-DQL)

### 3. **Environnements Pré-construits**
```python
import gymnasium as gym

# Jeux Atari
env = gym.make('ALE/Pong-v5')

# Contrôle classique
env = gym.make('CartPole-v1')

# Robotique
env = gym.make('FetchReach-v2')

# Votre environnement personnalisé
env = Environment()  # Compatible Gymnasium !
```

### 4. **Outils de Debug**
```python
from gymnasium.wrappers import RecordVideo, TimeLimit

# Enregistrer des vidéos
env = RecordVideo(env, 'videos/')

# Limiter le temps
env = TimeLimit(env, max_episode_steps=1000)
```

---

## 📊 Comparaison : Gym vs Gymnasium

| Aspect | OpenAI Gym (ancien) | Gymnasium (nouveau) |
|--------|---------------------|---------------------|
| **Maintenance** | ❌ Abandonné (2022) | ✅ Actif |
| **API** | `done` (bool) | `terminated`, `truncated` |
| **Version** | 0.26.2 (finale) | 1.2.3+ |
| **Recommandation** | ⚠️ Ne plus utiliser | ✅ Utiliser |

**Votre projet utilise Gymnasium 1.2.3** ✅

---

## 🔗 Dans Votre Projet

### Fichiers qui utilisent Gymnasium

1. **`modules/observation.py`**
   ```python
   import gymnasium as gym
   
   def observation_space(self):
       return gym.spaces.Box(
           low=0.0, high=1.0,
           shape=(self.get_observation_size(),),
           dtype=np.float32
       )
   ```

2. **`modules/environment.py`**
   ```python
   # SUMO-RL retourne des espaces Gymnasium
   self.action_spaces = {
       agent: self.env.action_spaces(agent) 
       for agent in self.agents
   }
   ```

3. **`custom_env_wrapper.py`**
   ```python
   # Wrapper pour multi-environnements
   # Maintient la compatibilité Gymnasium
   ```

---

## 🎯 Résumé

**Gymnasium = Interface standard pour RL**

✅ Définit comment l'agent interagit avec l'environnement  
✅ Fournit des types d'espaces (Discrete, Box, Dict)  
✅ Permet la réutilisation de code entre projets  
✅ Compatible avec toutes les bibliothèques RL  

**Dans votre projet** :
- SUMO-RL utilise Gymnasium en interne
- Vos 16 agents interagissent via l'interface Gymnasium
- Chaque intersection a son propre `action_space` et `observation_space`

---

**Gymnasium est la fondation qui permet à votre système RL de fonctionner !** 🏗️
