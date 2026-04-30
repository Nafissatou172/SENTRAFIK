# Step 1: Add modules to provide access to specific libraries and functions
import os # Module provides functions to handle file paths, directories, environment variables
import sys # Module provides access to Python-specific system parameters and functions

# Step 2: Establish path to SUMO (SUMO_HOME)
if 'SUMO_HOME' in os.environ:
    os.environ['PROJ_LIB'] = '/Library/Frameworks/EclipseSUMO.framework/Versions/1.25.0/EclipseSUMO/framework/EclipseSUMO.framework/Versions/1.25.0/EclipseSUMO/share/proj'
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# Step 3: Add Traci module to provide access to specific libraries and functions
import traci # Module for controlling SUMO simulations via TraCI

# Step 4: Define SUMO configuration
Sumo_config = [
    '/Library/Frameworks/EclipseSUMO.framework/Versions/Current/EclipseSUMO/bin/sumo-gui',
    '-c', 'brt.sumocfg',
    '--step-length', '1',
    '--delay', '500'
]

# Step 5: Open connection between SUMO and Traci
traci.start(Sumo_config)

# Step 6: Define Variables
vehicle_speed = 0
total_speed = 0

# Step 7: Define Functions
def update_speed():
    global vehicle_speed, total_speed
    if 'brt_flow_b1' in traci.vehicle.getIDList():
        vehicle_speed = traci.vehicle.getSpeed('brt_flow_b1')
        total_speed = total_speed + vehicle_speed
    # step_count = step_count + 1
    print(f"Vehicle speed: {vehicle_speed} m/s")


# Step 8: Take simulation steps until there are no more vehicles in the network
while traci.simulation.getMinExpectedNumber() > 0:
    traci.simulationStep() # Move simulation forward 1 step
    # Here you can decide what to do with simulation data at each step
    update_speed()

# Step 9: Close connection between SUMO and Traci
traci.close()