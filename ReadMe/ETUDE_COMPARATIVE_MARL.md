# 🧠 Étude Comparative : MARL pour le Contrôle du Trafic

Cette étude compare l'algorithme actuel (**Co-DQL**) avec les standards de l'état de l'art (**QMIX**, **VDN**, **MAPPO**) pour déterminer le plus adapté à une carte réelle complexe (comme le scénario BRT).

---

## 📊 Tableau Comparatif des Algorithmes

| Algorithme | Type | Coordination | Scalabilité (Carde Réelle) | Point Fort |
| :--- | :--- | :--- | :--- | :--- |
| **Co-DQL** (actuel) | Value-based | Spatiale (Voisins) | **Excellente** | Conçu pour les grands réseaux |
| **QMIX** | Value-based | Centralisée (Mixer) | Moyenne (Lent sur 100+ agents) | Coordination parfaite |
| **VDN** | Value-based | Additive | Bonne | Simplicité, stable |
| **MAPPO** | Policy-based | Centralized Critic | **Excellente** | Adapté aux états continus |

---

## 🔍 Analyse Détaillée

### 1. Co-DQL (Cooperative Double Q-Learning) - *Votre projet*
L'algorithme actuel utilise une approche de **Mean Field Approximation** et de **Neighborhood Communication**.
*   **Fonctionnement** : Chaque agent communique avec ses voisins directs pour coordonner ses actions.
*   **Avantage pour la carte BRT** : Très scalable. Si vous avez 100 intersections, Co-DQL traite 100 petits problèmes locaux coordonnés au lieu d'un seul problème massif.
*   **Limite** : La coordination est limitée au voisinage immédiat.

### 2. QMIX (Monotonic Value Factorization)
Considéré comme l'un des plus puissants pour la coopération.
*   **Fonctionnement** : Un réseau "Mixer" combine les Q-valeurs de tous les agents pour maximiser la récompense totale.
*   **Avantage** : Garantit mathématiquement que l'action optimale de chaque feu sert l'intérêt global du réseau.
*   **Limite sur carte réelle** : Le Mixer devient mathématiquement complexe à entraîner quand le nombre d'agents augmente (comme sur votre carte BRT de 38 Mo).

### 3. MAPPO (Multi-Agent PPO)
L'équivalent multi-agent de PPO, très populaire chez OpenAI.
*   **Fonctionnement** : Utilise un "Critique Centralisé" qui voit tout le réseau pendant l'entraînement, mais les feux prennent des décisions locales pendant l'exécution.
*   **Avantage** : Très robuste au bruit et aux changements de trafic. Gère mieux les observations complexes que les méthodes basées sur la Q-valeur.
*   **Recommandation** : C'est souvent l'alternative #1 à tester pour les réseaux urbains massifs.

---

## 🎯 Recommandation pour la carte "BRT"

La carte `new_config_files/output.net.xml` est **massive** (38 Mo). Voici le verdict :

### Pourquoi Co-DQL (actuel) est déjà un excellent choix :
Pour une ville réelle, la **communication par voisinage** (ce que fait Co-DQL) est souvent plus efficace qu'une centralisation totale (QMIX). Un feu à un bout de la ville n'a pas besoin de savoir ce que fait un feu à 5 km pour prendre une bonne décision.

### Quelle amélioration choisir ?
Si vous trouvez que Co-DQL stagne, l'algorithme le plus adapté pour passer à l'échelle supérieure serait **MAPPO**.

**Pourquoi MAPPO ?**
1.  **Stabilité** : Sur une carte réelle, le trafic est très instable. MAPPO est connu pour sa stabilité d'apprentissage.
2.  **Gestion du Temps** : MAPPO gère mieux les séquences temporelles longues (utile pour les bus BRT qui traversent toute la carte).
3.  **Scalabilité** : Il gère très bien un grand nombre d'agents grâce au partage de paramètres.

---

## 🛠️ Conclusion Technique

1.  **Conservez Co-DQL** pour vos premières expérimentations sur la grille 4x4 et le début du BRT. Il est spécifiquement optimisé pour la topologie de grille/réseau.
2.  **Envisagez MAPPO** si vous visez une implémentation de niveau "production" sur une ville entière, car il surpasse souvent les méthodes de Q-Learning sur des observations très riches et des dynamiques complexes de bus (BRT).

> **Note** : Passer à QMIX pour la carte BRT serait risqué car la complexité du réseau pourrait faire exploser le temps de calcul du "Mixer Network".
