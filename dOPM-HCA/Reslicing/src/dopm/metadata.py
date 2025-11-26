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
        
        print("⚠️ WARNING: ZStackLoop event not found. Calculating Z-step from frame positions.")
        if self.attributes.sequenceCount > 1:
            return abs(self._experiment_loop[1].z - self._experiment_loop[0].z)
        
        return 1.0

    def get_channel_names(self) -> list:
        """Returns a list of the channel names."""
        if self.metadata and hasattr(self.metadata, 'channels'):
            return [ch.channel.name for ch in self.metadata.channels]
        return []

    # --- THIS METHOD IS NOW INCLUDED ---
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
    def get_dataset_dimensions_from_filenames(directory: str, well: str) -> dict:
        """
        Scans a directory to find all unique times, tiles, angles, etc., for a
        given well based on the filename pattern.
        """
        pattern = re.compile(r".*?_Time(\d+)_Tile(\d+)_angle(\d+)_{1,2}Well(" + re.escape(well) + r").*\.nd2")
        dimensions = defaultdict(set)
        
        for filename in os.listdir(directory):
            match = pattern.match(filename)
            if match:
                dimensions["times"].add(int(match.group(1)))
                dimensions["tiles"].add(int(match.group(2)))
                dimensions["angles"].add(int(match.group(3)))
        
        return {key: sorted(list(value)) for key, value in dimensions.items()}
    
    # --- ADD THIS NEW METHOD TO THE METADATA CLASS ---
    @staticmethod
    def discover_wells(directory: str) -> list:
        """
        Scans a directory and finds all unique well IDs from .nd2 filenames.
        """
        # A regex to find the '_WellA6' or '__WellA6' pattern
        pattern = re.compile(r"_{1,2}Well([A-Z]\d+)")
        wells = set()
        for filename in os.listdir(directory):
            if not filename.endswith(".nd2"):
                continue
            
            match = pattern.search(filename)
            if match:
                wells.add(match.group(1))
        
        if not wells:
            print(f"⚠️ WARNING: No wells discovered in directory: {directory}")
        
        return sorted(list(wells))