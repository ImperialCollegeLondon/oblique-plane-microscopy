# In src/dopm/metadata.py

import nd2
import numpy as np
import os
import re
from collections import defaultdict


class Metadata:
    """
    A class to extract metadata from .nd2 files and from filename patterns.
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        with nd2.ND2File(self.file_path) as f:
            self._experiment_loop = f.experiment
            self.attributes = f.attributes
            self.metadata = f.metadata

    def get_stack_dimensions(self) -> dict:
        """Returns the image dimensions (X, Y, Z)."""
        return {'X': self.attributes.widthPx, 'Y': self.attributes.heightPx, 'Z': self.attributes.sequenceCount}

    def get_z_step(self) -> float:
        """
        Returns the step size of the Z-stack in microns by finding the
        ZStackLoop event and reading its 'stepUm' parameter.
        """
        zstackloop = next((item for item in self._experiment_loop if item.type == 'ZStackLoop'), None)
        if zstackloop:
            return zstackloop.parameters.stepUm

        print("WARNING: ZStackLoop event not found. Calculating Z-step from frame positions.")
        if self.attributes.sequenceCount > 1:
            return abs(self._experiment_loop[1].z - self._experiment_loop[0].z)

        return 1.0

    def get_channel_names(self) -> list:
        """Returns a list of the channel names."""
        if self.metadata and hasattr(self.metadata, 'channels'):
            return [ch.channel.name for ch in self.metadata.channels]
        return []

    def get_all_metadata(self) -> dict:
        """
        Processes the .nd2 file and returns a clean dictionary of all
        necessary parameters.
        """
        return {
            "stack_dimensions": self.get_stack_dimensions(),
            "z_step": self.get_z_step(),
            "channel_names": self.get_channel_names()
        }

    @staticmethod
    def get_dataset_dimensions_from_filenames(
        directory: str,
        well: str,
        allow_wellless: bool = False,
    ) -> dict:
        """
        Scans a directory to find all unique times, tiles and angles for a
        logical well.

        Supported filename styles:

            spim_Time0000_Tile0000_angle0__WellF5.nd2
            spim_Time0000_Tile0000_angle0_WellF5.nd2
            spim_Time0000_Tile0000_angle0.nd2

        The well-tagged patterns are always tried first. If no files are found
        for the requested well and ``allow_wellless`` is True, all matching
        Time/Tile/angle ND2 files in the folder are treated as one logical well.
        This allows bead or sample folders without WellXX suffixes to be
        processed while still using ``well`` as the output dataset label.
        """
        def collect(pattern: re.Pattern) -> dict:
            dimensions = defaultdict(set)

            for filename in os.listdir(directory):
                if not filename.lower().endswith(".nd2"):
                    continue

                match = pattern.match(filename)
                if match:
                    dimensions["times"].add(int(match.group(1)))
                    dimensions["tiles"].add(int(match.group(2)))
                    dimensions["angles"].add(int(match.group(3)))

            return {key: sorted(list(value)) for key, value in dimensions.items()}

        well_pattern = re.compile(
            r".*?_Time(\d+)_Tile(\d+)_angle(\d+)_{1,2}Well"
            + re.escape(well)
            + r".*\.nd2$",
            re.IGNORECASE,
        )
        dimensions = collect(well_pattern)
        if dimensions:
            return dimensions

        if not allow_wellless:
            return {}

        wellless_pattern = re.compile(
            r"^(?!.*_{1,2}Well[A-Z]\d+).*?_Time(\d+)_Tile(\d+)_angle(\d+).*\.nd2$",
            re.IGNORECASE,
        )
        dimensions = collect(wellless_pattern)
        if dimensions:
            print(
                f"INFO: No files tagged with Well{well} were found in {directory}; "
                "using well-less filenames as one logical well."
            )

        return dimensions

    @staticmethod
    def discover_wells(directory: str, allow_wellless: bool = False) -> list:
        """
        Scans a directory and finds all unique well IDs from .nd2 filenames.

        If ``allow_wellless`` is True and ND2 files are present but no WellXX
        tags are found, [None] is returned so callers can explicitly process the
        folder as a single logical well.
        """
        pattern = re.compile(r"_{1,2}Well([A-Z]\d+)", re.IGNORECASE)
        wells = set()
        nd2_files_found = False

        for filename in os.listdir(directory):
            if not filename.lower().endswith(".nd2"):
                continue

            nd2_files_found = True
            match = pattern.search(filename)
            if match:
                wells.add(match.group(1).upper())

        if wells:
            return sorted(list(wells))

        if allow_wellless and nd2_files_found:
            print(f"INFO: No wells discovered in {directory}; treating folder as a well-less dataset.")
            return [None]

        print(f"WARNING: No wells discovered in directory: {directory}")
        return []
