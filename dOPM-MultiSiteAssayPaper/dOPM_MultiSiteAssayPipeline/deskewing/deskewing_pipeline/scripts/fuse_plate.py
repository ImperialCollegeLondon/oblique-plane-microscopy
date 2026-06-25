import argparse
import yaml
import os
import sys

"""Minimal fuse_plate wrapper for publication.
Takes a BDV deskewed dataset and fuses multi-view stacks using Fiji.
"""


def main():
    parser = argparse.ArgumentParser(description="Fuse multi-view BDV dataset using Fiji.")
    parser.add_argument('--config', required=True, help='Path to fusion YAML config')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Setup import path. Prefer repository-level src/.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(root)
    sys.path.insert(0, os.path.join(root, 'src'))
    sys.path.insert(0, os.path.join(repo_root, 'src'))
    from dopm.fusion import FusionProcessor

    # Get paths and settings
    fusion_cfg = config.get('fusion', {})
    bdv_xml_path = fusion_cfg.get('bdv_dataset_xml', None)
    
    if not bdv_xml_path:
        raise ValueError("Config must specify 'fusion.bdv_dataset_xml' path")
    
    if not os.path.exists(bdv_xml_path):
        raise FileNotFoundError(f"BDV XML file not found: {bdv_xml_path}")

    fiji_path = config.get('fiji_executable_path', 'fiji-2.9.0-win64/Fiji.app')
    
    if not os.path.exists(fiji_path):
        raise FileNotFoundError(f"Fiji executable not found at: {fiji_path}")
    
    fusion_settings = {
        'binning': fusion_cfg.get('binning', 1)
    }
    
    # Run fusion
    print(f"INFO: Starting fusion of BDV dataset: {bdv_xml_path}")
    print(f"   Fiji: {fiji_path}")
    print(f"   Binning: {fusion_settings['binning']}")
    
    processor = FusionProcessor(fiji_path, fusion_settings)
    processor.fuse_volumes(bdv_xml_path, output_prefix='fused')
    
    print(f"OK: Fusion complete.")


if __name__ == '__main__':
    main()
