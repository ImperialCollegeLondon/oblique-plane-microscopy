import argparse
import yaml
import os
import subprocess
import sys

"""Process plate wrapper supporting multiple modes:
- maxproj: max Z-projection only (fast preview)
- deskew: geometric deskewing with default transforms
- deskew_with_beads: geometric deskewing + bead-derived corrections
"""


def process_maxproj(config, root):
    """Run max Z-projection only (fast preview mode)."""
    raw_script = os.path.join(root, 'src', 'raw_maxproj.py')
    data_cfg = config.get('data', {})
    input_path = data_cfg.get('input_path', 'path/to/raw')
    output_path = data_cfg.get('output_path', 'processed_output')
    pattern = data_cfg.get('pattern', None)

    cmd = [sys.executable, raw_script, input_path, '--output', output_path]
    if pattern:
        cmd += ['--pattern', pattern]

    print('Running max Z-projection:', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    print('Max Z-projection complete.')


def process_deskew(config, root, with_beads=False):
    """Run geometric deskewing with optional bead corrections."""
    # Import DataConverter from the package. Prefer the repository-level src/
    # folder, while keeping the old deskewing_pipeline/src fallback available.
    repo_root = os.path.dirname(root)
    sys.path.insert(0, os.path.join(root, 'src'))
    sys.path.insert(0, os.path.join(repo_root, 'src'))
    from dopm.data_converter import DataConverter

    data_cfg = config.get('data', {})
    deskew_cfg = config.get('deskewing', {})
    reg_cfg = config.get('registration', {})
    well_id = config.get('pipeline_settings', {}).get('well_id', 'A01')

    input_path = data_cfg.get('input_path', 'path/to/raw')
    output_path = data_cfg.get('output_path', 'processed_output')
    scan_type = deskew_cfg.get('scan_type', 'stage_scanning')
    hardcoded_vars = deskew_cfg.get('hardcoded_vars', {})

    if not hardcoded_vars:
        raise ValueError('deskewing.hardcoded_vars is required for deskew mode')

    converter_config = {
        'type': scan_type,
        'input_path': input_path,
        'output_path': output_path,
        'hardcoded_vars': hardcoded_vars,
        'allow_wellless_filenames': data_cfg.get('allow_wellless_filenames', False),
    }

    converter = DataConverter(converter_config)
    print(f"INFO: Processing well '{well_id}' with mode='deskew{' + beads' if with_beads else ''}'")

    if with_beads:
        bead_xml = reg_cfg.get('registered_bead_xml_path')
        if not bead_xml or not os.path.exists(bead_xml):
            raise FileNotFoundError(
                f"Registration XML not found at: {bead_xml}. "
                "Generate it first with register_beads_pipeline.py"
            )
        converter.process_well_with_registration(well_id, bead_xml)
    else:
        converter.process_well(well_id)

    print('Deskewing complete.')


def main():
    parser = argparse.ArgumentParser(
        description="Run plate processing (maxproj, deskew, or deskew+beads)."
    )
    parser.add_argument('--config', required=True, help='Path to YAML config')
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    processing_cfg = config.get('processing', {})
    mode = processing_cfg.get('mode', 'maxproj')

    print(f"Processing mode: '{mode}'")

    if mode == 'maxproj':
        process_maxproj(config, root)
    elif mode == 'deskew':
        process_deskew(config, root, with_beads=False)
    elif mode == 'deskew_with_beads':
        process_deskew(config, root, with_beads=True)
    else:
        raise ValueError(f"Unknown processing mode: {mode}")


if __name__ == '__main__':
    main()
