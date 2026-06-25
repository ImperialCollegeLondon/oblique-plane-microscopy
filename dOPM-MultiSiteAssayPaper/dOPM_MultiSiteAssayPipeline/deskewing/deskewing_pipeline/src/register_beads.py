import os
import sys
import subprocess
import yaml
import xml.etree.ElementTree as ET
from datetime import datetime

"""Minimal bead registration script for publication distribution.
This script:
 - runs `raw_maxproj.py` on the bead input
 - writes a simple `registered_beads.xml` file listing generated projection files

Usage: python register_beads.py <input> --output OUTPUT --well WELL_ID
"""


def write_registered_xml(output_dir, proj_files, out_xml_path):
    root = ET.Element('RegisteredBeads')
    meta = ET.SubElement(root, 'GeneratedAt')
    meta.text = datetime.utcnow().isoformat() + 'Z'
    for p in proj_files:
        e = ET.SubElement(root, 'Projection')
        e.text = os.path.abspath(p)
    tree = ET.ElementTree(root)
    tree.write(out_xml_path, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Register bead dataset (minimal, publication-friendly).')
    parser.add_argument('input', help='Bead ND2 file or folder')
    parser.add_argument('--output', default='bead_output', help='Output folder for bead projections')
    parser.add_argument('--well', default='A01', help='Well identifier (for metadata)')
    args = parser.parse_args()

    root = os.path.dirname(os.path.abspath(__file__))
    raw_script = os.path.join(root, 'raw_maxproj.py')

    os.makedirs(args.output, exist_ok=True)

    # Run raw projection on bead data
    cmd = [sys.executable, raw_script, args.input, '--output', args.output]
    print('Running bead projection:', ' '.join(cmd))
    subprocess.run(cmd, check=True)

    # Collect projection files generated
    proj_files = [os.path.join(args.output, f) for f in os.listdir(args.output) if f.lower().endswith('.tif')]
    proj_files = sorted(proj_files)

    xml_path = os.path.join(args.output, 'registered_beads.xml')
    write_registered_xml(args.output, proj_files, xml_path)

    print('Wrote registration XML:', xml_path)
    print('Done.')
