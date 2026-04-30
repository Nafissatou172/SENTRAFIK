import os
import sys

# Configuration SUMO
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Erreur: Veuillez déclarer la variable d'environnement 'SUMO_HOME'")

import traci

def dump_tls_info():
    sumo_cmd = ['/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/bin/sumo', '-c', 'brt.sumocfg']
    traci.start(sumo_cmd)
    
    tls_ids = traci.trafficlight.getIDList()
    print(f"Total TLS: {len(tls_ids)}")
    
    for tls_id in tls_ids:
        print(f"\nTLS: {tls_id}")
        lanes = traci.trafficlight.getControlledLanes(tls_id)
        print(f"Lanes: {set(lanes)}")
        
        # Get logic
        logic = traci.trafficlight.getAllProgramLogics(tls_id)[0]
        for i, phase in enumerate(logic.phases):
            print(f"Phase {i}: {phase.state} (duration={phase.duration})")
            
    traci.close()

if __name__ == "__main__":
    dump_tls_info()
