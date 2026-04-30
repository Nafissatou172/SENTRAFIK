# Realistic Traffic Simulation Configuration

This directory contains configuration files for a realistic traffic simulation with **2000 vehicles** and **500 pedestrians** distributed across a 4x4 grid network.

## Files Overview

### Main Configuration Files

1. **`grid4x4_realistic.rou.xml`** - Route file with vehicle and pedestrian flows
2. **`grid4x4_realistic.add.xml`** - Additional elements (bus stops, parking areas, detectors, etc.)
3. **`sumo_realistic.sumocfg`** - SUMO configuration file that ties everything together
4. **`grid4x4.net.xml`** - Network file (4x4 grid with external connections)

## Simulation Features

### Vehicle Distribution (2000 total vehicles)

The simulation includes diverse vehicle types and flows:

#### Vehicle Types
- **Standard Cars** (60%): Regular passenger vehicles
- **Fast Cars** (20%): Sportier vehicles with higher speeds
- **Buses** (5%): Public transportation
- **Trucks** (10%): Heavy vehicles
- **Delivery Vans** (5%): Commercial delivery vehicles

#### Traffic Patterns
- **West-East flows**: 500 vehicles (left to right)
- **East-West flows**: 500 vehicles (right to left)
- **South-North flows**: 500 vehicles (bottom to top)
- **North-South flows**: 500 vehicles (top to bottom)
- **Diagonal routes**: Complex cross-grid movements
- **Bus routes**: 3 dedicated public transportation lines
- **Delivery routes**: Local delivery patterns

### Pedestrian Distribution (500 total pedestrians)

Pedestrians are distributed across the grid with realistic walking patterns:

- **Row-based movements**: Pedestrians moving along A, B, C, D rows
- **Cross-grid movements**: Diagonal pedestrian flows
- **Commercial area density**: Higher pedestrian concentration in B2-C2 area (simulating shopping/business district)

### Realistic Urban Features

The `.add.xml` file includes:

#### Traffic Management
- **Variable Speed Signs**: Dynamic speed adjustments on key roads
- **Rerouters**: Traffic redirection with 10% probability
- **Calibrators**: Maintaining consistent traffic flow at entry points

#### Urban Infrastructure
- **6 Bus Stops**: Strategically placed for public transportation
- **3 Parking Areas**: 60 total parking spaces
- **2 Charging Stations**: For electric vehicles (8 charging spots)

#### Monitoring Systems
- **Induction Loop Detectors**: Traffic volume monitoring
- **Lane Area Detectors**: Multi-lane traffic analysis

#### Visualization Elements
- **Buildings**: Commercial center, office buildings
- **Green Spaces**: Park area
- **POIs**: Hospital, school, shopping mall, train station

## How to Use

### Option 1: Run with SUMO GUI (Visual Mode)

```bash
sumo-gui -c sumo_realistic.sumocfg
```

This will open the SUMO graphical interface where you can:
- Start/pause/stop the simulation
- Adjust simulation speed
- View traffic statistics in real-time
- Click on vehicles to see their routes

### Option 2: Run without GUI (Headless Mode)

```bash
sumo -c sumo_realistic.sumocfg
```

This runs the simulation without visualization (faster, good for data collection).

### Option 3: Run with Python (for RL Training)

```python
import traci

# Start SUMO with your configuration
sumo_cmd = ["sumo", "-c", "configuration files/sumo_realistic.sumocfg"]
traci.start(sumo_cmd)

# Your simulation/training loop
for step in range(3600):
    traci.simulationStep()
    # Your RL agent actions here
    
traci.close()
```

## Simulation Parameters

- **Duration**: 3600 seconds (1 hour)
- **Time step**: 1.0 second
- **Network**: 4x4 grid (16 intersections)
- **Total edges**: 80 (64 internal + 16 external)
- **Vehicle spawning**: Continuous flow throughout simulation
- **Pedestrian spawning**: Continuous flow with varying densities

## Traffic Volume Details

### Peak Traffic Areas

1. **B2-C2 Junction**: Highest traffic concentration (commercial center)
   - ~200 vehicles/hour
   - ~100 pedestrians/hour
   
2. **External Entry Points**: 
   - Left entries: ~450-500 vehicles/hour
   - Bottom entries: ~400-450 vehicles/hour
   - Right entries: ~400-450 vehicles/hour
   - Top entries: ~400-450 vehicles/hour

### Traffic Distribution by Time

The simulation maintains relatively constant traffic throughout the hour, with:
- Some vehicles entering at the start
- Continuous flow maintained by calibrators
- Natural variations from routing decisions

## Customization

### Adjusting Vehicle Count

To change the number of vehicles, edit the `number` attribute in vehicle flows in `grid4x4_realistic.rou.xml`:

```xml
<flow id="flow_left0_right" type="car" begin="0" end="3600" number="120" .../>
```

### Adjusting Pedestrian Count

To change pedestrian density, edit the `personsPerHour` attribute:

```xml
<personFlow id="ped_a_row_1" begin="0" end="3600" personsPerHour="30">
```

### Adding New Routes

Add new flows to `grid4x4_realistic.rou.xml`:

```xml
<flow id="new_flow" type="car" begin="0" end="3600" number="100" from="ORIGIN_EDGE" to="DEST_EDGE"/>
```

Available edges can be found by examining `grid4x4.net.xml`.

## Validation

To verify your configuration:

```bash
# Check if the route file is valid
sumo -c sumo_realistic.sumocfg --duration-log.statistics --no-step-log

# Count total vehicles
grep -c "<flow" grid4x4_realistic.rou.xml

# Count pedestrian flows
grep -c "personFlow" grid4x4_realistic.rou.xml
```

## Expected Output Statistics

After a complete run, you should observe:
- **Total vehicles**: ~2000 (some may not complete their journey in 1 hour)
- **Total pedestrians**: ~500
- **Average waiting time**: 30-60 seconds (depends on traffic light settings)
- **Average speed**: 8-12 m/s (28-43 km/h)
- **Throughput**: Variable by junction

## Troubleshooting

### Issue: "Edge not found" errors

**Solution**: Verify edge names in `grid4x4.net.xml` match those used in route file.

```bash
grep 'edge id=' grid4x4.net.xml | grep -v "internal"
```

### Issue: Too many vehicles stuck

**Solution**: Adjust `time-to-teleport` in `sumo_realistic.sumocfg` or increase simulation time.

### Issue: Pedestrians not appearing

**Solution**: Ensure network has sidewalks/walking areas:
- Check that `walkingareas` is enabled in network
- Verify pedestrian routes use valid edges with sidewalks

### Issue: Low frame rate in GUI

**Solution**: 
- Reduce detail level: View → Show → reduce checked items
- Run without GUI for data collection
- Reduce number of vehicles/pedestrians

## Integration with RL Training

To use this configuration with your traffic control RL agent:

```python
import sumo_rl

env = sumo_rl.parallel_env(
    net_file='configuration_files/grid4x4.net.xml',
    route_file='configuration files/grid4x4_realistic.rou.xml',
    additional_file='configuration files/grid4x4_realistic.add.xml',
    use_gui=False,
    num_seconds=3600,
    # ... other parameters
)
```

## Statistics Collection

To collect detailed statistics, add to `sumo_realistic.sumocfg`:

```xml
<output>
    <summary-output value="summary.xml"/>
    <tripinfo-output value="tripinfo.xml"/>
    <statistic-output value="statistics.xml"/>
</output>
```

## License and Attribution

These configuration files are part of a traffic control research project using SUMO (Simulation of Urban MObility).

For more information about SUMO: https://www.eclipse.org/sumo/

## Contact

For questions or issues with this configuration, please refer to the main project documentation.

