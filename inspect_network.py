
import xml.etree.ElementTree as ET
import os

def inspect_network(net_file):
    try:
        tree = ET.parse(net_file)
        root = tree.getroot()
        
        # Find all connection elements
        all_connections = root.findall(".//connection")
        b1_conns = [c for c in all_connections if c.get('tl') == 'B1']
        
        print(f"Number of connections for B1: {len(b1_conns)}")
        
        # Sort by linkIndex
        b1_conns.sort(key=lambda x: int(x.get('linkIndex')))
        
        for conn in b1_conns:
            from_edge = conn.get('from')
            to_edge = conn.get('to')
            link_index = conn.get('linkIndex')
            print(f"Link {link_index}: {from_edge} -> {to_edge} ({conn.get('dir', '?')})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    net_path = "/Users/robotsmali/Downloads/files/configuration_files/grid4x4.net.xml"
    if os.path.exists(net_path):
        inspect_network(net_path)
    else:
        print(f"File not found: {net_path}")
