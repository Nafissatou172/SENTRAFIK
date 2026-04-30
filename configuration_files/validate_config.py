#!/usr/bin/env python3
"""
Validation and Analysis Script for Realistic Traffic Simulation Configuration

This script validates the configuration files and provides statistics about:
- Total expected vehicles and pedestrians
- Route distributions
- Time distributions
- Network coverage
"""

import xml.etree.ElementTree as ET
import os
import sys
from collections import defaultdict

class ConfigValidator:
    def __init__(self, config_dir="."):
        self.config_dir = config_dir
        self.net_file = os.path.join(config_dir, "grid4x4.net.xml")
        self.route_file = os.path.join(config_dir, "grid4x4_realistic.rou.xml")
        self.add_file = os.path.join(config_dir, "grid4x4_realistic.add.xml")
        self.sumocfg_file = os.path.join(config_dir, "sumo_realistic.sumocfg")
        
        self.edges = set()
        self.junctions = set()
        self.vehicle_flows = []
        self.pedestrian_flows = []
        self.vehicle_types = {}
        
    def validate_network(self):
        """Validate and parse network file."""
        print("=" * 70)
        print("NETWORK VALIDATION")
        print("=" * 70)
        
        if not os.path.exists(self.net_file):
            print(f"❌ Network file not found: {self.net_file}")
            return False
            
        try:
            tree = ET.parse(self.net_file)
            root = tree.getroot()
            
            # Count edges (excluding internal edges)
            for edge in root.findall(".//edge[@id]"):
                edge_id = edge.get('id')
                if not edge_id.startswith(':'):  # Exclude internal edges
                    self.edges.add(edge_id)
            
            # Count junctions
            for junction in root.findall(".//junction[@id]"):
                junction_id = junction.get('id')
                if not junction_id.startswith(':'):  # Exclude internal junctions
                    self.junctions.add(junction_id)
            
            print(f"✓ Network file loaded successfully")
            print(f"  - Total edges: {len(self.edges)}")
            print(f"  - Total junctions: {len(self.junctions)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing network file: {e}")
            return False
    
    def validate_routes(self):
        """Validate and analyze route file."""
        print("\n" + "=" * 70)
        print("ROUTE FILE VALIDATION")
        print("=" * 70)
        
        if not os.path.exists(self.route_file):
            print(f"❌ Route file not found: {self.route_file}")
            return False
            
        try:
            tree = ET.parse(self.route_file)
            root = tree.getroot()
            
            # Parse vehicle types
            for vtype in root.findall(".//vType"):
                vtype_id = vtype.get('id')
                vtype_class = vtype.get('vClass', 'passenger')
                max_speed = float(vtype.get('maxSpeed', 13.89))
                self.vehicle_types[vtype_id] = {
                    'vClass': vtype_class,
                    'maxSpeed': max_speed
                }
            
            # Parse vehicle flows
            total_vehicles = 0
            invalid_edges = []
            
            for flow in root.findall(".//flow"):
                flow_id = flow.get('id')
                flow_type = flow.get('type')
                begin = float(flow.get('begin', 0))
                end = float(flow.get('end', 3600))
                number = int(flow.get('number', 0))
                from_edge = flow.get('from')
                to_edge = flow.get('to')
                
                # Validate edges
                if from_edge not in self.edges:
                    invalid_edges.append(f"Flow {flow_id}: from_edge '{from_edge}' not in network")
                if to_edge not in self.edges:
                    invalid_edges.append(f"Flow {flow_id}: to_edge '{to_edge}' not in network")
                
                self.vehicle_flows.append({
                    'id': flow_id,
                    'type': flow_type,
                    'begin': begin,
                    'end': end,
                    'number': number,
                    'from': from_edge,
                    'to': to_edge
                })
                
                total_vehicles += number
            
            # Parse pedestrian flows
            total_pedestrians = 0
            
            for pflow in root.findall(".//personFlow"):
                pflow_id = pflow.get('id')
                begin = float(pflow.get('begin', 0))
                end = float(pflow.get('end', 3600))
                persons_per_hour = int(pflow.get('personsPerHour', 0))
                
                # Calculate total persons
                duration_hours = (end - begin) / 3600.0
                persons = int(persons_per_hour * duration_hours)
                
                trip = pflow.find('personTrip')
                if trip is not None:
                    from_edge = trip.get('from')
                    to_edge = trip.get('to')
                    
                    self.pedestrian_flows.append({
                        'id': pflow_id,
                        'begin': begin,
                        'end': end,
                        'personsPerHour': persons_per_hour,
                        'totalPersons': persons,
                        'from': from_edge,
                        'to': to_edge
                    })
                    
                    total_pedestrians += persons
            
            print(f"✓ Route file loaded successfully")
            print(f"\n📊 Vehicle Types: {len(self.vehicle_types)}")
            for vtype_id, vtype_data in self.vehicle_types.items():
                print(f"  - {vtype_id}: {vtype_data['vClass']} (max speed: {vtype_data['maxSpeed']:.2f} m/s)")
            
            print(f"\n🚗 Vehicle Flows: {len(self.vehicle_flows)}")
            print(f"  - Total vehicles: {total_vehicles}")
            
            print(f"\n🚶 Pedestrian Flows: {len(self.pedestrian_flows)}")
            print(f"  - Total pedestrians: {total_pedestrians}")
            
            if invalid_edges:
                print(f"\n⚠️  Warning: {len(invalid_edges)} invalid edge references:")
                for error in invalid_edges[:5]:  # Show first 5
                    print(f"  - {error}")
                if len(invalid_edges) > 5:
                    print(f"  ... and {len(invalid_edges) - 5} more")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing route file: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def analyze_traffic_patterns(self):
        """Analyze traffic patterns and distributions."""
        print("\n" + "=" * 70)
        print("TRAFFIC PATTERN ANALYSIS")
        print("=" * 70)
        
        # Analyze by vehicle type
        type_counts = defaultdict(int)
        for flow in self.vehicle_flows:
            type_counts[flow['type']] += flow['number']
        
        print("\n🚗 Vehicle Distribution by Type:")
        total = sum(type_counts.values())
        for vtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  - {vtype:15s}: {count:4d} vehicles ({percentage:5.1f}%)")
        
        # Analyze by direction
        direction_patterns = {
            'West→East': 0,
            'East→West': 0,
            'South→North': 0,
            'North→South': 0,
            'Diagonal': 0,
            'Local': 0
        }
        
        for flow in self.vehicle_flows:
            from_edge = flow['from']
            to_edge = flow['to']
            
            if 'left' in from_edge and 'right' in to_edge:
                direction_patterns['West→East'] += flow['number']
            elif 'right' in from_edge and 'left' in to_edge:
                direction_patterns['East→West'] += flow['number']
            elif 'bottom' in from_edge and 'top' in to_edge:
                direction_patterns['South→North'] += flow['number']
            elif 'top' in from_edge and 'bottom' in to_edge:
                direction_patterns['North→South'] += flow['number']
            elif ('left' in from_edge or 'right' in from_edge) and ('top' in to_edge or 'bottom' in to_edge):
                direction_patterns['Diagonal'] += flow['number']
            elif ('top' in from_edge or 'bottom' in from_edge) and ('left' in to_edge or 'right' in to_edge):
                direction_patterns['Diagonal'] += flow['number']
            else:
                direction_patterns['Local'] += flow['number']
        
        print("\n➡️  Vehicle Distribution by Direction:")
        for direction, count in sorted(direction_patterns.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  - {direction:15s}: {count:4d} vehicles ({percentage:5.1f}%)")
        
        # Pedestrian density by area
        print("\n🚶 Pedestrian Distribution:")
        ped_total = sum(p['totalPersons'] for p in self.pedestrian_flows)
        
        area_peds = defaultdict(int)
        for pflow in self.pedestrian_flows:
            # Determine area based on edges
            from_edge = pflow['from']
            if from_edge:
                area = from_edge[0] if len(from_edge) > 0 else 'Unknown'
                area_peds[area] += pflow['totalPersons']
        
        for area, count in sorted(area_peds.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / ped_total * 100) if ped_total > 0 else 0
            print(f"  - Row {area}: {count:3d} pedestrians ({percentage:5.1f}%)")
    
    def validate_additional_file(self):
        """Validate additional file."""
        print("\n" + "=" * 70)
        print("ADDITIONAL FILE VALIDATION")
        print("=" * 70)
        
        if not os.path.exists(self.add_file):
            print(f"❌ Additional file not found: {self.add_file}")
            return False
            
        try:
            tree = ET.parse(self.add_file)
            root = tree.getroot()
            
            counts = {
                'busStop': len(root.findall(".//busStop")),
                'parkingArea': len(root.findall(".//parkingArea")),
                'chargingStation': len(root.findall(".//chargingStation")),
                'inductionLoop': len(root.findall(".//inductionLoop")),
                'laneAreaDetector': len(root.findall(".//laneAreaDetector")),
                'rerouter': len(root.findall(".//rerouter")),
                'variableSpeedSign': len(root.findall(".//variableSpeedSign")),
                'calibrator': len(root.findall(".//calibrator")),
                'poly': len(root.findall(".//poly")),
                'poi': len(root.findall(".//poi"))
            }
            
            print(f"✓ Additional file loaded successfully")
            print(f"\n📍 Urban Infrastructure:")
            for element_type, count in counts.items():
                if count > 0:
                    print(f"  - {element_type:20s}: {count}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing additional file: {e}")
            return False
    
    def validate_sumo_config(self):
        """Validate SUMO configuration file."""
        print("\n" + "=" * 70)
        print("SUMO CONFIGURATION VALIDATION")
        print("=" * 70)
        
        if not os.path.exists(self.sumocfg_file):
            print(f"❌ SUMO config file not found: {self.sumocfg_file}")
            return False
            
        try:
            tree = ET.parse(self.sumocfg_file)
            root = tree.getroot()
            
            # Check required files
            input_elem = root.find(".//input")
            if input_elem is not None:
                net_file = input_elem.find("net-file")
                route_files = input_elem.find("route-files")
                add_files = input_elem.find("additional-files")
                
                print(f"✓ SUMO config file loaded successfully")
                print(f"\n📁 Input Files:")
                if net_file is not None:
                    print(f"  - Network: {net_file.get('value')}")
                if route_files is not None:
                    print(f"  - Routes: {route_files.get('value')}")
                if add_files is not None:
                    print(f"  - Additional: {add_files.get('value')}")
            
            # Check time settings
            time_elem = root.find(".//time")
            if time_elem is not None:
                begin = time_elem.find("begin")
                end = time_elem.find("end")
                step = time_elem.find("step-length")
                
                print(f"\n⏰ Time Settings:")
                if begin is not None:
                    print(f"  - Begin: {begin.get('value')}s")
                if end is not None:
                    print(f"  - End: {end.get('value')}s")
                if step is not None:
                    print(f"  - Step length: {step.get('value')}s")
            
            return True
            
        except Exception as e:
            print(f"❌ Error parsing SUMO config file: {e}")
            return False
    
    def run_validation(self):
        """Run complete validation."""
        print("\n")
        print("╔" + "=" * 68 + "╗")
        print("║" + " " * 10 + "REALISTIC TRAFFIC SIMULATION VALIDATOR" + " " * 19 + "║")
        print("╚" + "=" * 68 + "╝")
        
        results = []
        
        results.append(self.validate_network())
        results.append(self.validate_routes())
        
        if all(results):
            self.analyze_traffic_patterns()
        
        results.append(self.validate_additional_file())
        results.append(self.validate_sumo_config())
        
        # Summary
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        
        if all(results):
            print("✅ All validations passed!")
            print("\n🎯 Your simulation is ready to run:")
            print("   sumo-gui -c sumo_realistic.sumocfg")
        else:
            print("❌ Some validations failed. Please check the errors above.")
            return 1
        
        print("\n" + "=" * 70)
        return 0


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate and analyze realistic traffic simulation configuration'
    )
    parser.add_argument(
        '--config-dir',
        default='.',
        help='Directory containing configuration files (default: current directory)'
    )
    
    args = parser.parse_args()
    
    validator = ConfigValidator(args.config_dir)
    exit_code = validator.run_validation()
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()

