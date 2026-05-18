#!/usr/bin/env python3
"""
fqi_train.py — Phase 2 : Entraînement FQI (Fitted Q-Iteration)
================================================================
Charge les transitions collectées par fqi_collector.py et entraîne
un ExtraTreesRegressor par agent en utilisant l'algorithme FQI offline.

Avantages :
  - Pas besoin de SUMO pour entraîner (très rapide)
  - Réutilise efficacement toutes les données
  - Modèles explicables (feature importance)

Usage :
    python fqi_train.py [--input transitions.pkl] [--iterations 10] [--output models/]
"""

import os
import pickle
import logging
import argparse
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION FQI
# ═════════════════════════════════════════════════════════════════════════════

GAMMA         = 0.90    # facteur d'actualisation
N_ESTIMATORS  = 100     # arbres par forêt
MAX_DEPTH     = 12      # profondeur max des arbres
N_ACTIONS     = 2       # 0=garder phase, 1=changer phase


# ═════════════════════════════════════════════════════════════════════════════
#  ALGORITHME FQI
# ═════════════════════════════════════════════════════════════════════════════

def fqi_train_agent(transitions: list, n_iterations: int, agent_id: str) -> ExtraTreesRegressor:
    """
    Entraîne un ExtraTreesRegressor pour un agent donné via FQI.

    transitions : liste de (state, action, reward, next_state)
    Retourne le modèle entraîné.
    """
    if len(transitions) < 10:
        log.warning(f"  Agent {agent_id}: pas assez de données ({len(transitions)} transitions)")
        return None

    states      = np.array([t[0] for t in transitions], dtype=np.float32)
    actions     = np.array([t[1] for t in transitions], dtype=np.float32)
    rewards     = np.array([t[2] for t in transitions], dtype=np.float32)
    next_states = np.array([t[3] for t in transitions], dtype=np.float32)

    # X = concat(state, action)
    X = np.column_stack([states, actions])

    # Initialiser les cibles Q avec les récompenses immédiates
    y = rewards.copy()

    model = None

    for iteration in range(n_iterations):
        # Entraîner le modèle sur (X, y)
        model = ExtraTreesRegressor(
            n_estimators=N_ESTIMATORS,
            max_depth=MAX_DEPTH,
            n_jobs=-1,
            random_state=42 + iteration,
        )
        model.fit(X, y)

        # Mettre à jour les cibles avec Bellman : y = r + γ * max_a' Q(s', a')
        q_next_values = []
        for a in range(N_ACTIONS):
            X_next = np.column_stack([next_states, np.full(len(next_states), a, dtype=np.float32)])
            q_next_values.append(model.predict(X_next))

        q_next_max = np.max(np.array(q_next_values), axis=0)
        y = rewards + GAMMA * q_next_max

        # Score de qualité
        if iteration % 2 == 0 or iteration == n_iterations - 1:
            train_score = model.score(X, y)
            log.debug(f"    Itération {iteration+1}/{n_iterations} | R² = {train_score:.4f}")

    return model


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="FQI Train — Entraînement offline")
    parser.add_argument('--input', '-i', default='data/transitions.pkl',
                        help="Fichier de transitions (défaut: data/transitions.pkl)")
    parser.add_argument('--iterations', '-n', type=int, default=8,
                        help="Nombre d'itérations FQI (défaut: 8)")
    parser.add_argument('--output', '-o', default='data/fqi_models/',
                        help="Dossier de sortie pour les modèles (défaut: data/fqi_models/)")
    args = parser.parse_args()

    # Charger les données
    log.info(f"Chargement des transitions depuis {args.input} ...")
    with open(args.input, 'rb') as f:
        data = pickle.load(f)

    transitions = data["transitions"]
    state_dim = data.get("state_dim_example", 0)
    total_trans = sum(len(v) for v in transitions.values())
    n_agents = len(transitions)

    log.info(f"  {n_agents} agents, {total_trans} transitions totales")
    log.info(f"  Dimension d'état : {state_dim}")
    log.info(f"  Itérations FQI   : {args.iterations}")

    # Entraîner chaque agent
    os.makedirs(args.output, exist_ok=True)
    models = {}
    trained = 0

    log.info(f"\n{'='*60}")
    log.info(f"  ENTRAÎNEMENT FQI ({args.iterations} itérations)")
    log.info(f"{'='*60}")

    for i, (agent_id, agent_transitions) in enumerate(transitions.items()):
        if len(agent_transitions) < 10:
            continue

        model = fqi_train_agent(agent_transitions, args.iterations, agent_id)
        if model is not None:
            models[agent_id] = model
            trained += 1

            # Sauvegarder le modèle
            model_path = os.path.join(args.output, f"{agent_id}.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

        if (i + 1) % 25 == 0 or i == n_agents - 1:
            log.info(f"  Progression : {i+1}/{n_agents} agents traités, {trained} entraînés")

    # Sauvegarder les métadonnées
    meta = {
        "n_agents": n_agents,
        "trained": trained,
        "iterations": args.iterations,
        "gamma": GAMMA,
        "n_estimators": N_ESTIMATORS,
        "max_depth": MAX_DEPTH,
        "state_dim": state_dim,
    }
    with open(os.path.join(args.output, "meta.pkl"), 'wb') as f:
        pickle.dump(meta, f)

    log.info(f"\n✅ Entraînement terminé !")
    log.info(f"   {trained}/{n_agents} modèles entraînés")
    log.info(f"   Sauvegardés dans : {args.output}")

    # Feature importance (top 5 agents)
    log.info(f"\n── Importances des features (top 5 agents) ──")
    sorted_models = sorted(models.items(), key=lambda x: len(transitions[x[0]]), reverse=True)
    for agent_id, model in sorted_models[:5]:
        imps = model.feature_importances_
        n_features = len(imps)
        log.info(f"\n  Agent {agent_id} ({len(transitions[agent_id])} transitions):")
        log.info(f"    Features locales (moy)  : {np.mean(imps[:n_features-1-8]):.3f}")
        log.info(f"    Action                  : {imps[-1]:.3f}")


if __name__ == "__main__":
    main()
