#!/usr/bin/env python3
"""
fqi_collector.py — Phase 1 : Collecte de Données pour FQI
===========================================================
Lance la simulation SUMO avec une politique ε-greedy basée
sur les files d'attente et sauvegarde toutes les transitions
(état, action, récompense, nouvel_état) dans un fichier pickle.

Usage:
    python fqi_collector.py [--episodes N] [--output transitions.pkl]
"""

import os
import sys
import math
import random
import pickle
import logging
import argparse
import numpy as np
from typing import Dict, List, Tuple
import xml.etree.ElementTree as ET

# ── SUMO / TraCI ──────────────────────────────────────────────────────────────
if 'SUMO_HOME' in os.environ:
    os.environ['PROJ_LIB'] = '/Library/Frameworks/EclipseSUMO.framework/Versions/1.25.0/EclipseSUMO/framework/EclipseSUMO.framework/Versions/1.25.0/EclipseSUMO/share/proj'
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Erreur: Veuillez déclarer la variable d'environnement 'SUMO_HOME'")

import traci

# ═════════════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

SUMO_BINARY = "/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/bin/sumo"
SUMO_CFG    = "brt.sumocfg"
NET_XML     = "output-new.net.xml"

STEP_LENGTH     = 1       # pas de simulation en secondes
MIN_GREEN_STEPS = 15      # durée minimale d'une phase (sécurité)
NEIGHBOR_RADIUS = 600     # rayon en mètres pour voisinage géographique
MAX_NEIGHBORS   = 4       # nb max de voisins intégrés dans l'état
EPSILON         = 0.20    # taux d'exploration (plus élevé pour bien explorer)
BRT_PREFIXES    = ['brt_flow_b1', 'brt_flow_b2', 'brt_flow_b3']

DECISION_INTERVAL = 5     # prendre une décision tous les N pas (évite l'oscillation)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
#  EXTRACTION DE LA TOPOLOGIE
# ═════════════════════════════════════════════════════════════════════════════

def load_topology(net_xml_path: str):
    """
    Retourne :
      agents_info : {tls_id -> {'x', 'y', 'incLanes', 'n_phases', 'neighbors'}}
    """
    log.info(f"Chargement de la topologie depuis {net_xml_path} ...")
    tree = ET.parse(net_xml_path)
    root = tree.getroot()

    # 1. Jonctions avec feux
    junctions = {}
    for junc in root.findall("junction"):
        if "traffic_light" in junc.get("type", ""):
            jid = junc.get("id")
            junctions[jid] = {
                "x": float(junc.get("x", 0)),
                "y": float(junc.get("y", 0)),
                "incLanes": junc.get("incLanes", "").split(),
            }

    # 2. Nombre de phases par feu (seuls les vrais TLS)
    num_phases = {}
    for tl in root.findall("tlLogic"):
        tlid = tl.get("id")
        num_phases[tlid] = len(tl.findall("phase"))

    # 3. Filtrer : ne garder que les jonctions avec un tlLogic
    valid_ids = set(num_phases.keys())
    junctions = {jid: info for jid, info in junctions.items() if jid in valid_ids}

    # 4. Voisinage par edges directs + distance
    neighbors = {jid: set() for jid in valid_ids}
    for edge in root.findall("edge"):
        if edge.get("function") in ("internal", "walkingarea"):
            continue
        frm, to = edge.get("from"), edge.get("to")
        if frm in valid_ids and to in valid_ids and frm != to:
            neighbors[frm].add(to)
            neighbors[to].add(frm)

    # Compléter par distance euclidienne
    tl_list = list(valid_ids)
    for i, a in enumerate(tl_list):
        ax, ay = junctions[a]["x"], junctions[a]["y"]
        for b in tl_list[i + 1:]:
            bx, by = junctions[b]["x"], junctions[b]["y"]
            if math.hypot(ax - bx, ay - by) <= NEIGHBOR_RADIUS:
                neighbors[a].add(b)
                neighbors[b].add(a)

    # Trier par distance et limiter
    for jid in valid_ids:
        neighbors[jid].discard(jid)
        neighbors[jid] = sorted(
            list(neighbors[jid]),
            key=lambda nb: math.hypot(
                junctions[jid]["x"] - junctions[nb]["x"],
                junctions[jid]["y"] - junctions[nb]["y"],
            ),
        )[:MAX_NEIGHBORS]

    # 5. Assembler
    agents_info = {}
    for jid in valid_ids:
        agents_info[jid] = {
            "x": junctions[jid]["x"],
            "y": junctions[jid]["y"],
            "incLanes": junctions[jid]["incLanes"],
            "n_phases": num_phases[jid],
            "neighbors": neighbors.get(jid, []),
        }

    log.info(f"Topologie : {len(agents_info)} feux actifs, "
             f"voisinage moy={sum(len(v['neighbors']) for v in agents_info.values())/max(len(agents_info),1):.1f}")
    return agents_info


# ═════════════════════════════════════════════════════════════════════════════
#  FONCTIONS UTILITAIRES
# ═════════════════════════════════════════════════════════════════════════════

def get_queues(inc_lanes: List[str]) -> List[float]:
    """Lit les files d'attente pour chaque voie entrante."""
    queues = []
    for lane in inc_lanes:
        try:
            queues.append(float(traci.lane.getLastStepHaltingNumber(lane)))
        except traci.exceptions.TraCIException:
            queues.append(0.0)
    return queues


def build_state(tls_id: str, info: dict, shared_states: dict) -> np.ndarray:
    """
    Construit le vecteur d'état pour un agent :
      [queue_lane_0, ..., queue_lane_N, phase_norm, n_phases_norm,
       brt_present,
       voisin_0_queue_mean, voisin_0_phase_norm, ..., voisin_K]
    """
    queues = get_queues(info["incLanes"])
    try:
        phase = traci.trafficlight.getPhase(tls_id)
    except traci.exceptions.TraCIException:
        phase = 0

    n_phases = info["n_phases"]
    vec = list(queues)
    vec.append(phase / max(n_phases - 1, 1))       # phase normalisée
    vec.append(n_phases / 10.0)                      # nb phases normalisé

    # Détection BRT sur les voies entrantes
    brt_present = 0.0
    for lane in info["incLanes"]:
        try:
            for veh_id in traci.lane.getLastStepVehicleIDs(lane):
                if any(veh_id.startswith(p) for p in BRT_PREFIXES):
                    brt_present = 1.0
                    break
        except traci.exceptions.TraCIException:
            pass
        if brt_present > 0:
            break
    vec.append(brt_present)

    # Infos voisins
    for nb_id in info["neighbors"]:
        if nb_id in shared_states:
            ns = shared_states[nb_id]
            vec.append(ns["queue_mean"])
            vec.append(ns["phase_norm"])
        else:
            vec.extend([0.0, 0.0])

    # Compléter si moins de MAX_NEIGHBORS voisins
    while len(info["neighbors"]) < MAX_NEIGHBORS:
        vec.extend([0.0, 0.0])
        info["neighbors"].append(None)  # placeholder

    return np.array(vec, dtype=np.float32), queues, phase


def compute_reward(queues: List[float], brt_present: float) -> float:
    """
    Récompense = -(somme des files) avec bonus si BRT passe sans attente.
    """
    total_q = sum(queues)
    brt_bonus = 5.0 if brt_present > 0 and total_q < 3 else 0.0
    zero_bonus = sum(1 for q in queues if q == 0) * 0.3
    return -total_q + zero_bonus + brt_bonus


def greedy_action(queues: List[float], phase: int, n_phases: int,
                  last_switch: int, step: int) -> int:
    """
    Politique de comportement (Behavior Policy) :
    - ε du temps : action aléatoire (exploration)
    - sinon : garder la phase si les files sont faibles, changer sinon
    """
    if step - last_switch < MIN_GREEN_STEPS:
        return 0  # Forcer le maintien de la phase

    if random.random() < EPSILON:
        return random.choice([0, 1])

    # Heuristique : si la file totale est > 5, on change de phase
    total_q = sum(queues)
    if total_q > 5:
        return 1  # Changer de phase
    return 0      # Garder la phase


def apply_action(tls_id: str, action: int, n_phases: int,
                 last_switch: int, step: int) -> int:
    """Applique l'action et retourne le nouveau last_switch."""
    if action == 0 or step - last_switch < MIN_GREEN_STEPS:
        return last_switch
    try:
        current = traci.trafficlight.getPhase(tls_id)
        next_phase = (current + 1) % n_phases
        traci.trafficlight.setPhase(tls_id, next_phase)
        return step
    except traci.exceptions.TraCIException:
        return last_switch


# ═════════════════════════════════════════════════════════════════════════════
#  BOUCLE DE COLLECTE
# ═════════════════════════════════════════════════════════════════════════════

def collect_episode(agents_info: dict) -> dict:
    """
    Exécute un épisode complet de simulation et retourne les transitions
    par agent : {tls_id -> [(state, action, reward, next_state), ...]}
    """
    transitions = {tls_id: [] for tls_id in agents_info}
    last_switches = {tls_id: -MIN_GREEN_STEPS for tls_id in agents_info}

    step = 0
    total_reward = 0.0

    while traci.simulation.getMinExpectedNumber() > 0:
        # 1. Broadcast des états locaux
        shared_states = {}
        for tls_id, info in agents_info.items():
            queues = get_queues(info["incLanes"])
            try:
                phase = traci.trafficlight.getPhase(tls_id)
            except traci.exceptions.TraCIException:
                phase = 0
            shared_states[tls_id] = {
                "queue_mean": float(np.mean(queues)) if queues else 0.0,
                "phase_norm": phase / max(info["n_phases"] - 1, 1),
            }

        # 2. Décision + Application (tous les DECISION_INTERVAL pas)
        if step % DECISION_INTERVAL == 0:
            pre_states = {}
            pre_queues = {}
            actions = {}

            for tls_id, info in agents_info.items():
                state_vec, queues, phase = build_state(tls_id, info, shared_states)
                action = greedy_action(queues, phase, info["n_phases"],
                                       last_switches[tls_id], step)

                pre_states[tls_id] = state_vec
                pre_queues[tls_id] = queues
                actions[tls_id] = action

                last_switches[tls_id] = apply_action(
                    tls_id, action, info["n_phases"],
                    last_switches[tls_id], step
                )

            # 3. Avancer la simulation de DECISION_INTERVAL pas
            for _ in range(DECISION_INTERVAL):
                traci.simulationStep()
                if traci.simulation.getMinExpectedNumber() == 0:
                    break

            # 4. Nouvel état + récompense
            shared_states_new = {}
            for tls_id, info in agents_info.items():
                queues = get_queues(info["incLanes"])
                try:
                    phase = traci.trafficlight.getPhase(tls_id)
                except traci.exceptions.TraCIException:
                    phase = 0
                shared_states_new[tls_id] = {
                    "queue_mean": float(np.mean(queues)) if queues else 0.0,
                    "phase_norm": phase / max(info["n_phases"] - 1, 1),
                }

            for tls_id, info in agents_info.items():
                new_state_vec, new_queues, _ = build_state(tls_id, info, shared_states_new)
                brt_flag = pre_states[tls_id][-1 - MAX_NEIGHBORS * 2]  # brt_present dans le vecteur
                reward = compute_reward(new_queues, brt_flag)

                transitions[tls_id].append((
                    pre_states[tls_id],
                    actions[tls_id],
                    reward,
                    new_state_vec
                ))
                total_reward += reward

        else:
            traci.simulationStep()

        step += 1

        # Logging
        if step % 500 == 0:
            arrived = traci.simulation.getTime()
            log.info(f"  Pas {step:6d} | Temps sim: {arrived/60:.0f} min | "
                     f"Reward cumul: {total_reward:.0f}")

    return transitions


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="FQI Collector — Collecte de transitions")
    parser.add_argument('--episodes', type=int, default=1,
                        help="Nombre d'épisodes de collecte (défaut: 1)")
    parser.add_argument('--output', '-o', default='data/transitions.pkl',
                        help="Fichier de sortie (défaut: data/transitions.pkl)")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)

    # Charger la topologie
    agents_info = load_topology(NET_XML)

    all_transitions = {tls_id: [] for tls_id in agents_info}

    for ep in range(args.episodes):
        log.info(f"\n{'='*60}")
        log.info(f"  ÉPISODE {ep+1}/{args.episodes}")
        log.info(f"{'='*60}")

        sumo_cmd = [
            SUMO_BINARY,
            "-c", SUMO_CFG,
            "--step-length", str(STEP_LENGTH),
            "--no-warnings", "true",
        ]
        traci.start(sumo_cmd)

        episode_transitions = collect_episode(agents_info)

        traci.close()

        # Accumuler les transitions
        for tls_id in agents_info:
            all_transitions[tls_id].extend(episode_transitions[tls_id])

        total_trans = sum(len(v) for v in all_transitions.values())
        log.info(f"  Épisode {ep+1} terminé. Total transitions: {total_trans}")

    # Sauvegarder
    # On sauvegarde aussi les infos des agents pour reconstruire les dimensions
    output_data = {
        "transitions": all_transitions,
        "agents_info": {k: {kk: vv for kk, vv in v.items() if kk != "neighbors"}
                        for k, v in agents_info.items()},
        "state_dim_example": len(next(iter(all_transitions.values()))[0][0]),
        "n_actions": 2,
    }

    with open(args.output, 'wb') as f:
        pickle.dump(output_data, f)

    total = sum(len(v) for v in all_transitions.values())
    log.info(f"\n✅ Transitions sauvegardées dans : {args.output}")
    log.info(f"   Total : {total} transitions pour {len(agents_info)} agents")
    log.info(f"   Moyenne : {total // max(len(agents_info), 1)} transitions/agent")


if __name__ == "__main__":
    main()
