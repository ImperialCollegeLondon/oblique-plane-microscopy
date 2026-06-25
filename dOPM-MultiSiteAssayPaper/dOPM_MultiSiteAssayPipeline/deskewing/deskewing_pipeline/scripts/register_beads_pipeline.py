import argparse
import os
import sys

import yaml

"""Convert and register bead ND2 data as a BDV dataset.

This is the bead-registration path used by ``deskew_with_beads``. It mirrors
manual/main-branch usage:

1. Convert bead ND2 files to a BDV XML/H5 dataset with DataConverter.
2. Run Fiji/BigStitcher interest-point registration on that bead BDV XML.
3. Leave the registered transforms in the bead BDV XML so sample deskewing can
   use ``DataConverter.process_well_with_registration()``.

The XML used by ``registration.registered_bead_xml_path`` should therefore be a
real BDV dataset XML, for example ``D:\\temp\\test_data\\bead_output\\dataset_WellC2.xml``.
"""


def build_bead_converter_config(config: dict) -> dict:
    """Build the DataConverter config for bead XML creation.

    Prefer the original/main-repo convention where ``bead_data`` is already a
    complete DataConverter config. Fall back to ``deskewing`` only for the
    publication-style combined YAMLs where common scan settings are shared.
    The scan type and hardcoded variables are important because they define the
    calibration/geometric transform written into the bead BDV XML.
    """
    bead_cfg = dict(config.get('bead_data', {}))
    deskew_cfg = config.get('deskewing', {})

    if 'type' not in bead_cfg:
        if 'scan_type' in bead_cfg:
            bead_cfg['type'] = bead_cfg['scan_type']
        elif 'scan_type' in deskew_cfg:
            bead_cfg['type'] = deskew_cfg['scan_type']
        else:
            raise ValueError(
                'Bead conversion requires bead_data.type or deskewing.scan_type.'
            )

    if 'hardcoded_vars' not in bead_cfg:
        if 'hardcoded_vars' in deskew_cfg:
            bead_cfg['hardcoded_vars'] = deskew_cfg['hardcoded_vars']
        else:
            raise ValueError(
                'Bead conversion requires bead_data.hardcoded_vars or '
                'deskewing.hardcoded_vars.'
            )

    if not bead_cfg.get('hardcoded_vars'):
        raise ValueError('Bead conversion requires non-empty hardcoded_vars.')
    if not bead_cfg.get('input_path'):
        raise ValueError('Config must specify bead_data.input_path')
    if not bead_cfg.get('output_path'):
        raise ValueError('Config must specify bead_data.output_path')

    bead_cfg['allow_wellless_filenames'] = bead_cfg.get('allow_wellless_filenames', False)
    bead_cfg.pop('scan_type', None)

    return bead_cfg


def resolve_bead_well(config: dict) -> str:
    pipeline_cfg = config.get('pipeline_settings', {})
    bead_cfg = config.get('bead_data', {})

    return (
        bead_cfg.get('well_id')
        or pipeline_cfg.get('bead_well_id')
        or pipeline_cfg.get('well_id')
        or 'A01'
    )


def main():
    parser = argparse.ArgumentParser(description='Convert and register bead BDV dataset.')
    parser.add_argument('--config', required=True, help='Path to YAML config')
    parser.add_argument(
        '--skip-fiji-registration',
        action='store_true',
        help='Only convert beads to BDV XML/H5; do not run Fiji registration.',
    )
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(root)
    sys.path.insert(0, os.path.join(root, 'src'))
    sys.path.insert(0, os.path.join(repo_root, 'src'))
    from dopm.data_converter import DataConverter

    bead_well = resolve_bead_well(config)
    converter_config = build_bead_converter_config(config)
    fiji_path = config.get('fiji_executable_path')

    converter = DataConverter(converter_config)

    print(f"INFO: Converting bead data as logical well '{bead_well}'")
    bead_xml_path = converter.process_well(bead_well)

    expected_xml = config.get('registration', {}).get('registered_bead_xml_path')
    if expected_xml and os.path.abspath(expected_xml) != os.path.abspath(bead_xml_path):
        print(f"WARNING: Config registration XML differs from generated bead XML.")
        print(f"  - Config:    {expected_xml}")
        print(f"  - Generated: {bead_xml_path}")
        print("  - deskew_with_beads should usually point to the generated BDV XML.")

    if args.skip_fiji_registration:
        print(f"OK: Bead BDV conversion complete: {bead_xml_path}")
        return

    if not fiji_path:
        raise ValueError('Config must specify fiji_executable_path to run bead registration')
    if not os.path.exists(fiji_path):
        raise FileNotFoundError(f"Fiji executable not found at: {fiji_path}")

    print(f"INFO: Running Fiji bead registration on: {bead_xml_path}")
    converter.register_dataset(bead_xml_path, fiji_path)
    print(f"OK: Bead registration complete: {bead_xml_path}")


if __name__ == '__main__':
    main()
