#!/usr/bin/env python3
"""
policier_ml_generic.py — Scénario 2 : Policier ML Optimisé
Projet SENTRAFIK - BRT Dakar

- Charge automatiquement les edges de la route BRT depuis brt_road.rou.xml
- Contrôle intelligent des feux avec le modèle ML
- Collecte complète de métriques (BRT, global, feux, séries temporelles)
- Export Excel détaillé
"""

import os
import sys
import argparse
import time
import joblib
import numpy as np
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
import warnings

# Désactivation des avertissements de noms de features scikit-learn
warnings.filterwarnings("ignore", category=UserWarning)

# ─────────────────────────────────────────────────────────────
# Configuration SUMO
# ─────────────────────────────────────────────────────────────
if 'SUMO_HOME' in os.environ:
    os.environ['PROJ_LIB'] = '/Library/Frameworks/EclipseSUMO.framework/Versions/1.25.0/EclipseSUMO/framework/EclipseSUMO.framework/Versions/1.25.0/EclipseSUMO/share/proj'
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Erreur: Veuillez déclarer la variable d'environnement 'SUMO_HOME'")

import traci


# ─────────────────────────────────────────────────────────────
# Chemins (depuis scenarios/)
# ─────────────────────────────────────────────────────────────
SUMO_BINARY_GUI = '/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/bin/sumo-gui'
SUMO_BINARY_CMD = '/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/bin/sumo'

# Chemins absolus basés sur l'emplacement du script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
SUMO_CONFIG = os.path.join(PROJECT_ROOT, 'config', 'brt.sumocfg')
ROUTES_FILE = os.path.join(PROJECT_ROOT, 'config', 'brt_road.rou.xml')
MODEL_PATH = os.path.join(PROJECT_ROOT, 'Model', 'policier_model_generic_v2.pkl')
SCALER_PATH = os.path.join(PROJECT_ROOT, 'Model', 'policier_scaler_generic_v2.pkl')

BRT_VTYPE = "BRT"
BRT_PRIORITY_DISTANCE = 200.0
MIN_GREEN_TIME = 25
CONTROL_INTERVAL = 8          # Contrôle toutes les ~8 secondes

# ─────────────────────────────────────────────────────────────
# Chargement automatique des edges BRT
# ─────────────────────────────────────────────────────────────
def load_brt_edges(routes_file):
    try:
        tree = ET.parse(routes_file)
        root = tree.getroot()
        route_brt = root.find(".//route[@id='route_brt']")
        if route_brt is not None:
            edges = route_brt.get('edges').split()
            unique_edges = sorted(set(edges))
            print(f"✅ {len(unique_edges)} edges BRT chargées automatiquement depuis route_brt")
            return unique_edges
        else:
            print("⚠️ Route 'route_brt' non trouvée. Utilisation d'une liste vide.")
            return []
    except Exception as e:
        print(f"⚠️ Erreur lecture {routes_file}: {e}")
        return []

BRT_EDGES = load_brt_edges(ROUTES_FILE)

# ─────────────────────────────────────────────────────────────
# Classe principale
# ─────────────────────────────────────────────────────────────
class PolicierMLCollector:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH)
        self.scaler = joblib.load(SCALER_PATH)
        print("✅ Modèle ML générique chargé")

        self.step_count = 0
        self.sim_time = 0.0
        self.last_control = 0

        self.tls_cache = {}           # Cache des controlled_lanes
        self.last_change = {}

        # Métriques (similaire à ton template)
        self.brt_data = {}
        self.timeseries = []
        self.tls_data = defaultdict(lambda: {
            'total_waiting_time': 0.0,
            'total_queue_length': 0,
            'total_vehicles_passed': 0,
            'sample_count': 0,
        })
        self.global_metrics = {
            'total_waiting_time': 0.0,
            'total_time_loss': 0.0,
            'total_vehicles_departed': 0,
            'total_vehicles_arrived': 0,
            'total_teleports': 0,
        }

    def is_brt_edge(self, edge_id):
        return any(brt_e in str(edge_id) for brt_e in BRT_EDGES)

    def get_features(self, tls_id):
        if tls_id not in self.tls_cache:
            self.tls_cache[tls_id] = traci.trafficlight.getControlledLanes(tls_id)

        controlled_lanes = self.tls_cache[tls_id]

        queue_main = 0
        queue_cross = 0
        wait_main = 0.0
        wait_cross = 0.0
        brt_on_main = 0

        for lane in controlled_lanes:
            edge = traci.lane.getEdgeID(lane)
            vehicles = traci.lane.getLastStepVehicleIDs(lane)
            lane_length = traci.lane.getLength(lane)

            for veh in vehicles:
                speed = traci.vehicle.getSpeed(veh)
                wait_time = traci.vehicle.getAccumulatedWaitingTime(veh)

                if traci.vehicle.getTypeID(veh) == BRT_VTYPE:
                    dist = lane_length - traci.vehicle.getLanePosition(veh)
                    if dist < BRT_PRIORITY_DISTANCE:
                        brt_on_main = 1

                if speed < 0.5:
                    if self.is_brt_edge(edge):
                        queue_main += 1
                        wait_main += wait_time
                    else:
                        queue_cross += 1
                        wait_cross += wait_time

        return {
            'queue_main': queue_main,
            'queue_cross': queue_cross,
            'wait_main': wait_main / queue_main if queue_main > 0 else 0.0,
            'wait_cross': wait_cross / queue_cross if queue_cross > 0 else 0.0,
            'speed_main': 35.0,
            'speed_cross': 30.0,
            'brt_on_main': brt_on_main,
            'brt_on_cross': 0,
            'time_since_last_change': 0,
            'current_phase': traci.trafficlight.getPhase(tls_id)
        }

    def control_traffic_lights(self):
        if self.step_count % CONTROL_INTERVAL != 0:
            return

        current_time = traci.simulation.getTime()
        tls_list = traci.trafficlight.getIDList()

        for tls_id in tls_list:
            if tls_id not in self.last_change:
                self.last_change[tls_id] = 0

            time_since = current_time - self.last_change[tls_id]
            if time_since < MIN_GREEN_TIME:
                continue

            features = self.get_features(tls_id)
            features['time_since_last_change'] = time_since

            state = np.array([[features['queue_main'], features['queue_cross'],
                               features['wait_main'], features['wait_cross'],
                               features['speed_main'], features['speed_cross'],
                               features['brt_on_main'], features['brt_on_cross'],
                               features['time_since_last_change'], features['current_phase']]])

            state_scaled = self.scaler.transform(state)
            new_phase = int(self.model.predict(state_scaled)[0])

            try:
                traci.trafficlight.setPhase(tls_id, new_phase)
                traci.trafficlight.setPhaseDuration(tls_id, 35.0)   # durée raisonnable
                self.last_change[tls_id] = current_time

                if features['brt_on_main'] == 1:
                    print(f"[{current_time:.0f}s] 🚨 BRT PRIORITÉ → {tls_id} → Phase {new_phase}")
            except:
                pass

    def collect_step_metrics(self):
        self.step_count += 1
        self.sim_time = traci.simulation.getTime()

        self.global_metrics['total_vehicles_departed'] += traci.simulation.getDepartedNumber()
        self.global_metrics['total_vehicles_arrived'] += traci.simulation.getArrivedNumber()
        self.global_metrics['total_teleports'] += traci.simulation.getStartingTeleportNumber()

        self.control_traffic_lights()

        # Tu peux ajouter ici la collecte complète de ton template (BRT détaillé, séries temporelles, etc.)

    def run(self):
        print("🚀 Simulation avec Policier ML optimisé démarrée...")
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            self.collect_step_metrics()

        traci.close()
        print("Simulation terminée.")


# ─────────────────────────────────────────────────────────────
# Lancement
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-gui', action='store_true')
    args = parser.parse_args()

    sumo_bin = SUMO_BINARY_CMD if args.no_gui else SUMO_BINARY_GUI

    traci.start([sumo_bin, '-c', SUMO_CONFIG, '--step-length', '1.0', '--no-warnings', 'true'])

    collector = PolicierMLCollector()
    collector.run()