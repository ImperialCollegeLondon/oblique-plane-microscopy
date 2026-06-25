#@ PrefService prefs
from fiji.util.gui import GenericDialogPlus
import os
import re
import math
import csv
import shutil

from ij import IJ
from ij.io import FileSaver
from ij.plugin import FolderOpener
from ij.plugin import HyperStackConverter

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import MetadataTools
from loci.formats import ImageReader

from array import array
from os.path import isfile
from xml.etree import ElementTree as ET
from xml.dom import minidom
from ome.units import UNITS


def readdopmxml(filename):
    tree = ET.parse(filename)

    settings = {}
    for elem in tree.iter():
        if elem.text:
            settings.update({elem.tag: elem.text})

    filterstrings = [
        'extension',
        'boundingboxmin',
        'boundingboxmax',
        'filepattern',
        'pixelsize',
        'prismangle',
        'rawzplanes'
    ]

    settings = {k: v for k, v in settings.iteritems() if k in filterstrings}

    IJ.log('settings read:')
    IJ.log(str(settings))
    return settings


def writedopmxml(filename, settings):
    data = ET.Element('dOPMconfig')
    items = ET.SubElement(data, 'parameters')

    ET.SubElement(items, 'pixelsize').text = settings.get("pixelsize")
    ET.SubElement(items, 'rawzplanes').text = settings.get("rawzplanes")
    ET.SubElement(items, 'prismangle').text = settings.get("prismangle")
    ET.SubElement(items, 'extension').text = settings.get("extension")
    ET.SubElement(items, 'filepattern').text = settings.get("filepattern")

    boundingbox = ET.SubElement(items, 'BoundingBoxes')

    if settings.get("BoundingBoxDefinition") is not None:
        bb_def = ET.SubElement(boundingbox, 'BoundingBoxDefinition')
        ET.SubElement(bb_def, 'boundingboxmin').text = settings.get("boundingboxmin")
        ET.SubElement(bb_def, 'boundingboxmax').text = settings.get("boundingboxmax")
        bb_def.set('name', "My Bounding Box")

    xmlstr = minidom.parseString(
        ET.tostring(data)
    ).toprettyxml(indent="   ", encoding='UTF-8')

    with open(filename, "w") as f:
        f.write(xmlstr)

    IJ.log('settings written:')
    IJ.log(str(settings))


class mvrsetup(object):

    def __init__(self, **kwargs):
        valid_keys = [
            "datapath",
            "regpath",
            "filepattern",
            "extension",
            "px",
            "py",
            "angle",
            "well_suffix",
            "well_tail",
            "dataset_basename",
            "bead_reference_timepoint",
            "registration_source_csv",
            "registration_source_xml",
            "view_mode",
            "target_angle"
        ]
        for key in valid_keys:
            setattr(self, key, kwargs.get(key))

        self.regpath = self.regpath or self.datapath
        self.filepattern_ = self.filepattern
        self.well_suffix = self.well_suffix
        self.well_tail = getattr(self, 'well_tail', None)
        self.bead_reference_timepoint = self.bead_reference_timepoint
        self.registration_source_csv = getattr(self, 'registration_source_csv', None)
        self.registration_source_xml = getattr(self, 'registration_source_xml', None)

        if self.well_tail:
            self.filepattern = self.filepattern_ + self.well_tail + self.extension
        else:
            self.filepattern = self.filepattern_ + self.extension

        dataset_root = kwargs.get("dataset_basename")
        if dataset_root:
            self.dataset_root = dataset_root
        elif self.well_suffix:
            self.dataset_root = "dataset_" + self.well_suffix
        else:
            self.dataset_root = "dataset"

        self.dataset = self.dataset_root + ".xml"
        self.registration_csv = self.dataset_root + "_registrations.csv"
        self.calibration_csv = self.dataset_root + "_calibrations.csv"

        self.calibfile = os.path.normpath(os.path.join(self.datapath, self.calibration_csv))

        if self.registration_source_csv:
            self.regfile = os.path.normpath(self.registration_source_csv)
        else:
            self.regfile = os.path.normpath(os.path.join(self.regpath, self.registration_csv))

        if self.registration_source_xml:
            self.regxml = os.path.normpath(self.registration_source_xml)
        else:
            self.regxml = None

        self.view_mode = getattr(self, 'view_mode', None)
        if self.view_mode is None:
            self.view_mode = 'two_view'

        self.target_angle = getattr(self, 'target_angle', None)
        if self.target_angle is not None:
            self.target_angle = str(self.target_angle).strip()
            if self.target_angle == '':
                self.target_angle = None
            else:
                self.target_angle = str(int(float(self.target_angle)))

        self.detected_angles = []
        self.dims = self.GetImageInfo()
        if self.dims:
            self.validate_view_mode()

    @staticmethod
    def parse_spim_filename_static(filename):
        stem = os.path.splitext(os.path.basename(filename))[0]

        info = {
            'time': None,
            'tile': None,
            'channel': None,
            'angle': None,
            'well': None,
            'well_tail': ''
        }

        parts = [p for p in re.split(r'_+', stem) if p]

        for p in parts:
            m = re.match(r'^Time(\d+)$', p)
            if m:
                info['time'] = str(int(m.group(1)))
                continue

            m = re.match(r'^Tile(\d+)$', p)
            if m:
                info['tile'] = str(int(m.group(1)))
                continue

            m = re.match(r'^channel(\d+)$', p)
            if m:
                info['channel'] = str(int(m.group(1)))
                continue

            m = re.match(r'^angle(\d+)$', p)
            if m:
                info['angle'] = str(int(m.group(1)))
                continue

            m = re.match(r'^Well.+$', p)
            if m:
                info['well'] = p
                continue

        m = re.search(r'(_+Well[^_]+)$', stem)
        if m:
            info['well_tail'] = m.group(1)

        return info

    def _parse_spim_filename(self, filename):
        return self.parse_spim_filename_static(filename)

    def _has_explicit_channel_token(self):
        return self.filepattern_.find('channel') != -1

    def list_input_files(self):
        files = []
        for each in os.listdir(self.datapath):
            if each.startswith('spim') and each.endswith(self.extension):
                parsed = self._parse_spim_filename(each)

                if parsed['time'] is None or parsed['tile'] is None or parsed['angle'] is None:
                    continue

                if self._has_explicit_channel_token() and parsed['channel'] is None:
                    continue

                if self.target_angle is not None and parsed['angle'] != self.target_angle:
                    continue

                parsed_tail = parsed['well_tail']
                if parsed_tail == '':
                    parsed_tail = None

                if self.well_tail is None:
                    if parsed_tail is not None:
                        continue
                else:
                    if parsed_tail != self.well_tail:
                        continue

                files.append(each)

        files.sort()
        return files

    @staticmethod
    def group_files_by_well(datapath, extension):
        groups = {}

        for each in os.listdir(datapath):
            if not each.startswith('spim') or not each.endswith(extension):
                continue

            parsed = mvrsetup.parse_spim_filename_static(each)
            well = parsed['well']

            if not groups.has_key(well):
                groups[well] = []
            groups[well].append(each)

        for key in groups:
            groups[key].sort()

        return groups

    @staticmethod
    def detect_well_suffixes(datapath, extension):
        groups = mvrsetup.group_files_by_well(datapath, extension)
        suffixes = groups.keys()

        def _sort_key(x):
            if x is None:
                return ""
            return x

        suffixes.sort(key=_sort_key)
        return suffixes

    @staticmethod
    def detect_well_tails(datapath, extension):
        tails = []

        for each in os.listdir(datapath):
            if not each.startswith('spim') or not each.endswith(extension):
                continue

            parsed = mvrsetup.parse_spim_filename_static(each)
            tail = parsed['well_tail']
            if tail == '':
                tail = None
            tails.append(tail)

        tails = list(set(tails))

        def _sort_key(x):
            if x is None:
                return ""
            return x

        tails.sort(key=_sort_key)
        return tails

    def _expected_second_angle(self):
        return str(int(round(4 * self.angle)))

    def _expected_dopm_angles(self):
        return ['0', self._expected_second_angle()]

    def _sorted_unique_numeric_strings(self, values):
        out = []
        for value in values:
            if value is None:
                continue
            value = str(int(value))
            if value not in out:
                out.append(value)
        out.sort(key=lambda x: int(x))
        return out

    def validate_view_mode(self):
        expected = self._expected_dopm_angles()

        if len(self.detected_angles) == 0:
            raise ValueError("No angle tokens were detected in the input files.")

        if self.view_mode == 'single_view':
            if self.target_angle is not None:
                IJ.log("Single-view requested angle filter: angle" + str(self.target_angle))

            if len(self.detected_angles) != 1:
                raise ValueError(
                    "Single-view mode needs one angle to process, but found " +
                    str(self.detected_angles) + ". If the folder contains both views, " +
                    "set the single-view angle field to 0 or " + expected[1] + "."
                )
            if self.detected_angles[0] not in expected:
                raise ValueError(
                    "Single-view mode currently supports dOPM angle0 or angle" + expected[1] +
                    " files. Found angle" + str(self.detected_angles[0]) + "."
                )
            IJ.log("Single-view dataset mode: using angle" + str(self.detected_angles[0]))
            return

        if self.view_mode == 'two_view':
            if len(self.detected_angles) != 2:
                raise ValueError(
                    "Two-view mode expects exactly two acquisition angles " + str(expected) +
                    ", but found " + str(self.detected_angles) +
                    ". Use 'Transform one-view data' for a single angle dataset."
                )
            for angle_value in expected:
                if angle_value not in self.detected_angles:
                    raise ValueError(
                        "Two-view mode expects angle tokens " + str(expected) +
                        ", but found " + str(self.detected_angles) + "."
                    )
            IJ.log("Two-view dataset mode: using angles " + str(self.detected_angles))
            return

        raise ValueError("Unknown view_mode: " + str(self.view_mode))

    def _get_angles_string_for_dataset(self):
        # Preserve the legacy two-view range syntax for existing workflows.
        # Single-view mode returns the one detected angle, e.g. "0" or "70".
        expected = self._expected_dopm_angles()
        if self.view_mode == 'two_view' and self.detected_angles == expected:
            return "0-" + expected[1] + ":" + expected[1]
        return ','.join(self.detected_angles)

    def choose_first_timepoint_from_current_files(self):
        times = []
        for each in self.list_input_files():
            parsed = self._parse_spim_filename(each)
            if parsed['time'] is not None:
                times.append(int(parsed['time']))

        if len(times) == 0:
            return None

        times = sorted(set(times))
        return str(times[0])

    def GetImageInfo(self):
        results = self.list_input_files()
        channels = []
        times = []
        tiles = []
        angles = []
        hyperstack = -1

        for each in results:
            parsed = self._parse_spim_filename(each)

            if parsed['time'] is None:
                raise ValueError("Could not parse time from file: " + each)
            if parsed['tile'] is None:
                raise ValueError("Could not parse tile from file: " + each)

            times.append(parsed['time'])
            tiles.append(parsed['tile'])
            angles.append(parsed['angle'])

            if self._has_explicit_channel_token():
                if parsed['channel'] is None:
                    raise ValueError("Expected channel token in file: " + each)
                channels.append(parsed['channel'])

        T = ','.join(sorted(set(times), key=lambda x: int(x)))
        Tiles = ','.join(sorted(set(tiles), key=lambda x: int(x)))
        self.detected_angles = self._sorted_unique_numeric_strings(angles)

        print results

        if len(results) == 0:
            print 'error in image format - does not match expected types'
            return []

        file = os.path.join(self.datapath, results[0])
        print file

        tiff_names = ['.tif', '.tiff']

        if any(self.extension == i for i in tiff_names):
            file = file.replace('\\', '/')
            imp = IJ.openImage(file)

            szX = imp.getCalibration().pixelWidth
            szY = imp.getCalibration().pixelHeight
            szZ = imp.getCalibration().pixelDepth
            X = imp.getWidth()
            Y = imp.getHeight()
            Z = imp.getImageStackSize()
            imp.close()

            hyperstack = 0
            print 'processing tif zstacks'

            if self._has_explicit_channel_token():
                C = ','.join(sorted(set(channels), key=lambda x: int(x)))
            else:
                C = '0'

        elif self.extension == '.nd2':
            reader = ImageReader()
            omeMeta = MetadataTools.createOMEXMLMetadata()
            reader.setMetadataStore(omeMeta)
            reader.setId(file)

            X = reader.getSizeX()
            Y = reader.getSizeY()
            Z = reader.getSizeZ()

            szX = omeMeta.getPixelsPhysicalSizeX(0).value()
            szY = omeMeta.getPixelsPhysicalSizeY(0).value()
            szZ = omeMeta.getPixelsPhysicalSizeZ(0).value()

            if reader.getSizeC() > 1 and not self._has_explicit_channel_token():
                print 'processing nd2 hyperstacks'
                hyperstack = 1
                c_list = []
                for c in range(reader.getSizeC()):
                    c_list.append(str(c))
                C = ','.join(c_list)

            elif reader.getSizeC() == 1 and self._has_explicit_channel_token():
                print 'processing nd2 zstacks'
                hyperstack = 0
                C = ','.join(sorted(set(channels), key=lambda x: int(x)))

            elif reader.getSizeC() == 1 and not self._has_explicit_channel_token():
                print 'processing nd2 single-channel files without explicit channel token'
                hyperstack = 1
                C = '0'

            else:
                reader.close()
                raise ValueError("Unsupported ND2 layout for file pattern: " + self.filepattern_)

            reader.close()

        else:
            print 'error in image format - does not match expected types'
            return []

        print [X, Y, Z, T, C, szX, szY, szZ, self.detected_angles]
        return [X, Y, Z, T, C, szX, szY, szZ, Tiles, hyperstack]

    def createXMLdataset(self):
        times = self.dims[3]
        tiles = self.dims[8]
        channels = self.dims[4]
        pz = self.dims[7]
        angles = self._get_angles_string_for_dataset()

        px = IJ.d2s(self.px, 4)
        py = IJ.d2s(self.py, 4)
        pz = IJ.d2s(pz, 4)

        tiff_names = ['.tif', '.tiff']

        if any(self.extension == i for i in tiff_names):
            IJ.run(
                "Define Multi-View Dataset",
                "define_dataset=[Manual Loader (TIFF only, ImageJ Opener)] "
                "project_filename=[" + self.dataset + "] "
                "multiple_timepoints=[YES (one file per time-point)] "
                "multiple_channels=[YES (one file per channel)] "
                "_____multiple_illumination_directions=[NO (one illumination direction)] "
                "multiple_angles=[YES (one file per angle)] "
                "multiple_tiles=[YES (one file per tile)] "
                "image_file_directory=[" + self.datapath + "] "
                "image_file_pattern=" + self.filepattern + " "
                "timepoints_=" + times + " "
                "channels_=" + channels + " "
                "acquisition_angles_=" + angles + " "
                "tiles_=" + tiles + " "
                "calibration_type=[Same voxel-size for all views] "
                "calibration_definition=[Load voxel-size(s) from file(s) and display for verification] "
                "imglib2_data_container=[ArrayImg (faster)] "
                "pixel_distance_x=" + px + " "
                "pixel_distance_y=" + py + " "
                "pixel_distance_z=" + pz + " "
                "pixel_unit=microns"
            )
        elif self.dims[9] == 1:
            IJ.run(
                "Define Multi-View Dataset",
                "define_dataset=[Manual Loader (Bioformats based)] "
                "project_filename=[" + self.dataset + "] "
                "multiple_timepoints=[YES (one file per time-point)] "
                "multiple_channels=[YES (all channels in one file)] "
                "_____multiple_illumination_directions=[NO (one illumination direction)] "
                "multiple_angles=[YES (one file per angle)] "
                "multiple_tiles=[YES (one file per tile)] "
                "image_file_directory=[" + self.datapath + "] "
                "image_file_pattern=" + self.filepattern + " "
                "timepoints_=" + times + " "
                "channels_=" + channels + " "
                "acquisition_angles_=" + angles + " "
                "tiles_=" + tiles + " "
                "calibration_type=[Same voxel-size for all views] "
                "calibration_definition=[Load voxel-size(s) from file(s) and display for verification] "
                "imglib2_data_container=[ArrayImg (faster)] "
                "pixel_distance_x=" + px + " "
                "pixel_distance_y=" + py + " "
                "pixel_distance_z=" + pz + " "
                "pixel_unit=microns"
            )
        elif self.dims[9] == 0:
            IJ.run(
                "Define Multi-View Dataset",
                "define_dataset=[Manual Loader (Bioformats based)] "
                "project_filename=[" + self.dataset + "] "
                "multiple_timepoints=[YES (one file per time-point)] "
                "multiple_channels=[YES (one file per channel)] "
                "_____multiple_illumination_directions=[NO (one illumination direction)] "
                "multiple_angles=[YES (one file per angle)] "
                "multiple_tiles=[YES (one file per tile)] "
                "image_file_directory=[" + self.datapath + "] "
                "image_file_pattern=" + self.filepattern + " "
                "timepoints_=" + times + " "
                "channels_=" + channels + " "
                "acquisition_angles_=" + angles + " "
                "tiles_=" + tiles + " "
                "calibration_type=[Same voxel-size for all views] "
                "calibration_definition=[Load voxel-size(s) from file(s) and display for verification] "
                "imglib2_data_container=[ArrayImg (faster)] "
                "pixel_distance_x=" + px + " "
                "pixel_distance_y=" + py + " "
                "pixel_distance_z=" + pz + " "
                "pixel_unit=microns"
            )
        else:
            print 'wrong image format during createXMLdataset'

    def createFolder(self, newpath):
        try:
            if not os.path.exists(newpath):
                os.makedirs(newpath)
        except OSError:
            print('Error: Creating directory. ' + newpath)

    def csvtoarray(self, csv_string, type_):
        values = csv_string.split(',')
        out = []
        for i in values:
            if type_ == 'int':
                out.append(int(i))
            elif type_ == 'float':
                out.append(float(i))
            elif type_ == 'string':
                out.append(str(i))
        return out

    def _format_affine_text_for_ij(self, affine_text):
        """
        Convert a BigStitcher XML affine string into the comma-separated form
        expected by the ImageJ/Fiji macro argument parser.

        BigStitcher XML usually stores affine values separated by whitespace:
            1.0 0.0 0.0 ...

        The Apply Transformations command is safer when given:
            1.0,0.0,0.0,...

        Without this conversion, the macro parser can collapse whitespace and
        BigStitcher sees one long token such as 1.00.00.0..., causing:
            Cannot parse ..., has 1 numbers, but should be 12
        """
        if affine_text is None:
            raise ValueError("Affine text is None")

        parts = re.split(r'[\s,]+', affine_text.strip())
        parts = [p for p in parts if p != '']

        if len(parts) != 12:
            raise ValueError(
                "Expected 12 affine numbers, found " + str(len(parts)) +
                " in affine text: " + str(affine_text)
            )

        return ','.join(parts)

    def _read_first_calibration_affine_from_xml(self):
        """
        Read the initial voxel calibration affine directly from the just-created
        BigStitcher XML.

        This replaces the old getCalibrations() -> dataset_calibrations.csv ->
        ApplyCalibration() round trip. It preserves the original behaviour: use
        the final transform from the first ViewRegistration as the calibration
        transform, then reapply it globally after clearing existing transforms.

        The calibration operation is still intentionally retained because the
        plugin workflow may not carry the calibration forward reliably. Only the
        temporary CSV sidecar is removed.
        """
        file = os.path.join(self.datapath, self.dataset)

        if not os.path.exists(file):
            raise IOError("Dataset XML not found: " + file)

        root = ET.parse(file).getroot()

        for node in root.findall('./ViewRegistrations/ViewRegistration'):
            elem = None
            for transform_node in node:
                affine_node = transform_node.find('affine')
                if affine_node is not None and affine_node.text is not None:
                    elem = affine_node.text

            if elem is not None:
                return self._format_affine_text_for_ij(elem)

        raise ValueError("No calibration affine found in dataset XML: " + file)

    def getAffineTransformations(self):
        file = os.path.join(self.datapath, self.dataset)
        root = ET.parse(file).getroot()
        affine_list = []
        spacer = 'NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN'

        for node in root.findall('./ViewRegistrations/ViewRegistration'):
            node_lines = []
            for i in node:
                elem = i.find('affine').text
                node_lines.append(elem)

            if len(node_lines) > 1:
                node_lines = node_lines[:-1]

            for elem in node_lines:
                affine_list.append(elem)

            affine_list.append(spacer)

        savepath = os.path.normpath(os.path.join(os.path.split(file)[0], self.registration_csv))
        savepath = savepath.replace('\\', '/')

        with open(savepath, "wb") as csv_file:
            writer = csv.writer(csv_file)
            for line in affine_list:
                writer.writerow(line.split())

    def _filter_registration_csv_to_first_timepoint(self, csv_path):
        if not os.path.exists(csv_path):
            raise IOError("Registration CSV not found: " + csv_path)

        rows = []
        with open(csv_path, "rb") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 0:
                    rows.append(row)

        if len(rows) == 0:
            raise ValueError("Registration CSV is empty: " + csv_path)

        filtered = []
        for row in rows:
            filtered.append(row)
            joined = ' '.join(row)
            if joined.startswith('NaN'):
                break

        with open(csv_path, "wb") as f:
            writer = csv.writer(f)
            for row in filtered:
                writer.writerow(row)

    def RegisterDataset(self):
        signal_strength = "[Weak & small (beads)]"
        datapath = os.path.join(self.datapath, self.dataset)

        tp = self.bead_reference_timepoint
        if tp is None:
            tp = self.choose_first_timepoint_from_current_files()

        if tp is None:
            raise ValueError("Could not determine bead reference timepoint.")

        IJ.log("Using bead reference timepoint: " + str(tp))

        IJ.run(
            "Detect Interest Points for Registration",
            "select=[" + datapath + "] "
            "process_angle=[All angles] "
            "process_channel=[All channels] "
            "process_illumination=[All illuminations] "
            "process_tile=[All tiles] "
            "process_timepoint=[Single Timepoint (Select from List)] "
            "type_of_interest_point_detection=Difference-of-Gaussian "
            "label_interest_points=beads "
            "subpixel_localization=[3-dimensional quadratic fit] "
            "interest_point_specification=" + signal_strength + " "
            "downsample_xy=1x downsample_z=1x "
            "compute_on=[CPU (Java)]"
        )

        IJ.run(
            "Register Dataset based on Interest Points",
            "select=[" + datapath + "] "
            "process_angle=[All angles] "
            "process_channel=[All channels] "
            "process_illumination=[All illuminations] "
            "process_tile=[All tiles] "
            "process_timepoint=[Single Timepoint (Select from List)] "
            "registration_algorithm=[Fast descriptor-based (rotation invariant)] "
            "registration_in_between_views=[Only compare overlapping views (according to current transformations)] "
            "interest_points=beads "
            "fix_views=[Fix first view] "
            "map_back_views=[Do not map back (use this if views are fixed)] "
            "transformation=Affine "
            "regularize_model model_to_regularize_with=Rigid "
            "lamba=0.10 redundancy=0 significance=10 "
            "allowed_error_for_ransac=5 "
            "number_of_ransac_iterations=Normal"
        )

    def _single_view_angle_for_macro(self):
        """
        Return the angle label that exists in the single-view XML and should be
        used in BigStitcher macro parameter names.

        Important: in a single-view XML there is only one ViewSetup, but the
        physical acquisition angle still matters.  We therefore avoid
        apply_to_angle=[All angles] in the single-view branch because some
        BigStitcher versions silently keep the default identity/zero model for
        All-angles parameters when only one angle is present.  Targeting the
        explicit angle gives the same transform stack that the corresponding
        physical angle receives in a normal two-view dataset.
        """
        if len(self.detected_angles) != 1:
            raise ValueError(
                "Single-view transform expected exactly one detected angle, found " +
                str(self.detected_angles)
            )
        return str(self.detected_angles[0])

    def _time_channel_prefix_and_flags(self, include_angle_flags):
        """
        Build the BigStitcher macro parameter prefix used by Apply
        Transformations.

        include_angle_flags is True for legacy/two-view all-angle commands.
        For single-view commands this must be False: each transform is applied
        to the explicit XML angle, not to [All angles].
        """
        channels = self.dims[4]
        times = self.dims[3]
        tiles = self.dims[8]

        single_time = (times.find('-') == -1 and times.find(',') == -1)
        multi_channel = (len(self.csvtoarray(channels, 'int')) > 1)
        multi_tile = (len(self.csvtoarray(tiles, 'int')) > 1)

        if single_time and multi_channel:
            prefix = "timepoint_" + times + "_all_channels_illumination_0"
            same_flags = "same_transformation_for_all_channels "
        elif single_time and not multi_channel:
            prefix = "timepoint_" + times + "_channel_" + channels + "_illumination_0"
            same_flags = ""
        elif (not single_time) and multi_channel:
            prefix = "all_timepoints_all_channels_illumination_0"
            same_flags = "same_transformation_for_all_timepoints same_transformation_for_all_channels "
        else:
            prefix = "all_timepoints_channel_" + channels + "_illumination_0"
            same_flags = "same_transformation_for_all_timepoints "

        if multi_tile:
            same_flags += "same_transformation_for_all_tiles "

        if include_angle_flags:
            same_flags += "same_transformation_for_all_angles "

        return prefix, same_flags

    def ApplyCalibrationFromXML(self):
        channels = self.dims[4]
        times = self.dims[3]
        tiles = self.dims[8]
        dataset = os.path.join(self.datapath, self.dataset)

        registration = self._read_first_calibration_affine_from_xml()

        if self.view_mode == 'single_view':
            # Do not use apply_to_angle=[All angles] for single-view datasets.
            # In testing, BigStitcher can silently apply the default identity
            # model for all-angle macro parameters when the XML has only one
            # angle.  Target the explicit XML angle so the calibration becomes
            # the first transform in the single physical view's stack.
            angle_label = self._single_view_angle_for_macro()
            prefix, same_flags = self._time_channel_prefix_and_flags(False)
            IJ.log("Applying single-view calibration to XML angle " + angle_label)
            IJ.run(
                "Apply Transformations",
                "select=[" + dataset + "] "
                "apply_to_angle=[Single angle (Select from List)] "
                "apply_to_channel=[All channels] apply_to_illumination=[All illuminations] "
                "apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] "
                "processing_angle=[angle " + angle_label + "] "
                "transformation=Affine apply=[Identity transform (removes any existing transforms)] " +
                same_flags + prefix + "_angle_" + angle_label + "=[" + registration + "]"
            )
            return

        if (times.find('-') == -1 and times.find(',') == -1) and (len(self.csvtoarray(channels, 'int')) == 1):
            if len(self.csvtoarray(tiles, 'int')) == 1:
                IJ.run("Apply Transformations", "select=[" + dataset + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Identity transform (removes any existing transforms)] same_transformation_for_all_angles timepoint_" + times + "_channel_" + channels + "_illumination_0_all_angles=[" + registration + "]")
            else:
                IJ.run("Apply Transformations", "select=[" + dataset + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Identity transform (removes any existing transforms)] same_transformation_for_all_angles same_transformation_for_all_tiles timepoint_" + times + "_channel_" + channels + "_illumination_0_all_angles=[" + registration + "]")
        elif (times.find('-') == -1 and times.find(',') == -1) and (len(self.csvtoarray(channels, 'int')) > 1):
            IJ.run("Apply Transformations", "select=[" + dataset + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Identity transform (removes any existing transforms)] same_transformation_for_all_channels same_transformation_for_all_angles same_transformation_for_all_tiles timepoint_" + times + "_all_channels_illumination_0_all_angles=[" + registration + "]")
        elif (times.find('-') != -1 or times.find(',') != -1) and (len(self.csvtoarray(channels, 'int')) == 1):
            IJ.run("Apply Transformations", "select=[" + dataset + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Identity transform (removes any existing transforms)] same_transformation_for_all_timepoints same_transformation_for_all_angles same_transformation_for_all_tiles all_timepoints_channel_" + channels + "_illumination_0_all_angles=[" + registration + "]")
        elif (times.find('-') != -1 or times.find(',') != -1) and (len(self.csvtoarray(channels, 'int')) > 1):
            IJ.run("Apply Transformations", "select=[" + dataset + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Identity transform (removes any existing transforms)] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_angles same_transformation_for_all_tiles all_timepoints_all_channels_illumination_0_all_angles=[" + registration + "]")
        else:
            print 'Unexpected calibration application case'

    def ApplyCalibration(self):
        """
        Backward-compatible alias. The calibration is now read directly from the
        dataset XML instead of from dataset_calibrations.csv.
        """
        self.ApplyCalibrationFromXML()

    def _read_registration_csv_first_block(self, csv_path):
        """
        Backward-compatible reader for the old *_registrations.csv format.
        Returns only the first block, matching the original ApplyBeadRegCSV()
        behaviour.
        """
        if not os.path.exists(csv_path):
            raise IOError("Bead registration file not found: " + csv_path)

        registration_list = []
        Reader = csv.reader(open(csv_path), delimiter=' ', quotechar='|')
        for registration in Reader:
            if len(registration) > 0:
                registration_list.append(registration[0])

        filtered = []
        for row in registration_list:
            filtered.append(row)
            if row.startswith('NaN'):
                break

        return filtered

    def _read_registration_xml_first_block(self, xml_path):
        """
        Read the live/current bead registration directly from a BigStitcher XML.

        This intentionally mirrors getAffineTransformations() + the first-block
        filtering previously used by ApplyBeadRegCSV(), but without writing or
        reading an intermediate CSV. Therefore, if you reopen the bead XML/HDF5
        in Fiji, optimise the registration, and save the XML, this function will
        use the updated transforms.
        """
        if not os.path.exists(xml_path):
            raise IOError("Bead registration XML not found: " + xml_path)

        root = ET.parse(xml_path).getroot()
        spacer = 'NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN NaN'
        registration_list = []

        for node in root.findall('./ViewRegistrations/ViewRegistration'):
            node_lines = []
            for transform_node in node:
                affine_node = transform_node.find('affine')
                if affine_node is not None and affine_node.text is not None:
                    node_lines.append(affine_node.text)

            # Preserve the old CSV extraction semantics exactly:
            # keep all transforms except the final one, then stop after the
            # first ViewRegistration block.
            if len(node_lines) > 1:
                node_lines = node_lines[:-1]

            for elem in node_lines:
                registration_list.append(elem)

            registration_list.append(spacer)
            break

        if len(registration_list) == 0:
            raise ValueError("No affine transforms found in bead registration XML: " + xml_path)

        return registration_list

    def _apply_bead_registration_list(self, registration_list):
        channels = self.dims[4]
        times = self.dims[3]
        dataset = os.path.join(self.datapath, self.dataset)

        idx = 0
        for registration in registration_list:
            idx += 1

            if registration.startswith('NaN'):
                continue

            channel = IJ.d2s(int(math.floor((idx - 1) / 2)), 0)
            angle_index = (idx - 1) % 2
            if angle_index == 0:
                angle_name = "0"
            else:
                angle_name = IJ.d2s(4 * self.angle, 0)

            if (times.find('-') == -1 and times.find(',') == -1):
                IJ.run(
                    "Apply Transformations",
                    "select=[" + dataset + "] "
                    "apply_to_angle=[Single angle (Select from List)] "
                    "apply_to_channel=[Single channel (Select from List)] "
                    "apply_to_illumination=[All illuminations] "
                    "apply_to_tile=[All tiles] "
                    "apply_to_timepoint=[All Timepoints] "
                    "processing_angle=[angle " + angle_name + "] "
                    "processing_channel=[channel " + channel + "] "
                    "transformation=Affine "
                    "apply=[Current view transformations (appends to current transforms)] "
                    "same_transformation_for_all_tiles "
                    "timepoint_" + times + "_channel_" + channel + "_illumination_0_angle_" + angle_name + "=[" + registration + "]"
                )
            else:
                IJ.run(
                    "Apply Transformations",
                    "select=[" + dataset + "] "
                    "apply_to_angle=[Single angle (Select from List)] "
                    "apply_to_channel=[Single channel (Select from List)] "
                    "apply_to_illumination=[All illuminations] "
                    "apply_to_tile=[All tiles] "
                    "apply_to_timepoint=[All Timepoints] "
                    "processing_angle=[angle " + angle_name + "] "
                    "processing_channel=[channel " + channel + "] "
                    "transformation=Affine "
                    "apply=[Current view transformations (appends to current transforms)] "
                    "same_transformation_for_all_timepoints "
                    "same_transformation_for_all_tiles "
                    "all_timepoints_channel_" + channel + "_illumination_0_angle_" + angle_name + "=[" + registration + "]"
                )

    def ApplyBeadRegCSV(self):
        registration_list = self._read_registration_csv_first_block(self.regfile)
        self._apply_bead_registration_list(registration_list)

    def ApplyBeadRegXML(self, xml_path=None):
        if xml_path is None:
            xml_path = self.regxml
        if xml_path is None:
            raise ValueError("No bead registration XML was provided.")
        registration_list = self._read_registration_xml_first_block(xml_path)
        self._apply_bead_registration_list(registration_list)


    def _copy_element(self, elem):
        """ElementTree deepcopy replacement compatible with Jython/Python 2."""
        return ET.fromstring(ET.tostring(elem))

    def _get_text_anywhere(self, elem, names):
        for name in names:
            child = elem.find(name)
            if child is not None and child.text is not None:
                return child.text
            child = elem.find('.//' + name)
            if child is not None and child.text is not None:
                return child.text
        return None

    def _read_setup_attribute_map(self, root):
        """
        Return setup_id -> {channel, angle, tile} from a BigStitcher/BDV XML.

        The XML produced by different Fiji/BigStitcher versions can place
        angle/channel/tile either directly under ViewSetup or under nested
        attributes. This reader is intentionally permissive.
        """
        setup_map = {}
        for setup in root.findall('.//ViewSetup'):
            sid = self._get_text_anywhere(setup, ['id'])
            if sid is None:
                continue
            sid = str(int(sid))
            ch = self._get_text_anywhere(setup, ['channel', 'Channel'])
            ang = self._get_text_anywhere(setup, ['angle', 'Angle'])
            tile = self._get_text_anywhere(setup, ['tile', 'Tile'])

            if ch is None:
                ch = '0'
            if ang is None:
                ang = '0'
            if tile is None:
                tile = '0'

            setup_map[sid] = {
                'channel': str(int(float(ch))),
                'angle': str(int(float(ang))),
                'tile': str(int(float(tile)))
            }
        return setup_map

    def _find_viewregistration_by_time_setup(self, root, timepoint, setup_id):
        for vr in root.findall('./ViewRegistrations/ViewRegistration'):
            tp = vr.get('timepoint')
            sid = vr.get('setup')
            if tp is None:
                tp = vr.get('timepointid')
            if sid is None:
                sid = vr.get('setupid')
            if tp is not None and sid is not None:
                if str(int(tp)) == str(int(timepoint)) and str(int(sid)) == str(int(setup_id)):
                    return vr
        return None

    def _make_source_transform_map_from_bead_xml(self, bead_xml_, source_timepoint, source_tile):
        """
        Read the current saved bead XML and select exactly one source view per
        channel/angle: source_timepoint + source_tile. The returned mapping is:

            (channel, angle) -> list of ViewTransform XML elements

        This is the global registration model: one bead time/tile gives the
        transform stack for each channel/angle, and those stacks are copied to
        every sample timepoint/tile/well with the same channel/angle.
        """
        if not os.path.exists(bead_xml_):
            raise IOError("Bead/reference XML not found: " + bead_xml_)

        root = ET.parse(bead_xml_).getroot()
        setup_map = self._read_setup_attribute_map(root)
        if len(setup_map) == 0:
            raise ValueError("Could not read ViewSetup channel/angle/tile metadata from: " + bead_xml_)

        source = {}
        for setup_id in sorted(setup_map.keys(), key=lambda x: int(x)):
            meta = setup_map[setup_id]
            if str(int(meta['tile'])) != str(int(source_tile)):
                continue
            vr = self._find_viewregistration_by_time_setup(root, source_timepoint, setup_id)
            if vr is None:
                continue
            key = (meta['channel'], meta['angle'])
            source[key] = [self._copy_element(child) for child in list(vr)]

        if len(source) == 0:
            raise ValueError(
                "No bead ViewRegistrations found for timepoint " + str(source_timepoint) +
                ", tile " + str(source_tile) + " in: " + bead_xml_
            )
        return source

    def CopyBeadRegistrationXMLGlobal(self, bead_xml_, source_timepoint='0', source_tile='0'):
        """
        Copy the optimised bead registration from bead_xml_ directly into this
        sample dataset XML.

        Important assumption implemented here:
        - bead source = timepoint 0, tile 0 by default;
        - for each channel/angle, that source transform stack is global;
        - the same channel/angle stack is copied to every sample timepoint,
          tile, and well represented in this sample XML.

        This deliberately avoids intermediate CSV files. After editing/saving
        the bead XML in Fiji/BigStitcher, this method uses the current XML.
        """
        sample_xml = os.path.join(self.datapath, self.dataset)
        if not os.path.exists(sample_xml):
            raise IOError("Sample XML not found: " + sample_xml)

        source_map = self._make_source_transform_map_from_bead_xml(
            bead_xml_, source_timepoint, source_tile
        )

        tree = ET.parse(sample_xml)
        root = tree.getroot()
        sample_setup_map = self._read_setup_attribute_map(root)
        if len(sample_setup_map) == 0:
            raise ValueError("Could not read sample ViewSetup metadata from: " + sample_xml)

        changed = 0
        missing = {}
        for vr in root.findall('./ViewRegistrations/ViewRegistration'):
            setup_id = vr.get('setup')
            if setup_id is None:
                setup_id = vr.get('setupid')
            if setup_id is None:
                continue
            setup_id = str(int(setup_id))
            if not sample_setup_map.has_key(setup_id):
                continue
            meta = sample_setup_map[setup_id]
            key = (meta['channel'], meta['angle'])
            if not source_map.has_key(key):
                missing[key] = 1
                continue

            for child in list(vr):
                vr.remove(child)
            for child in source_map[key]:
                vr.append(self._copy_element(child))
            changed += 1

        if changed == 0:
            raise ValueError("No sample ViewRegistrations were updated. Check channel/angle metadata.")

        tree.write(sample_xml)
        IJ.log(
            "Copied global bead registration from timepoint " + str(source_timepoint) +
            ", tile " + str(source_tile) + " to " + str(changed) +
            " sample ViewRegistrations: " + sample_xml
        )
        if len(missing.keys()) > 0:
            IJ.log("Warning: missing bead source transforms for channel/angle keys: " + str(missing.keys()))

    def ResaveXMLtoHDF5(self, exportpath):
        datapath = os.path.join(self.datapath, self.dataset)
        exportpath = os.path.join(exportpath, 'hdf5')
        self.createFolder(exportpath)
        exportpath = os.path.join(exportpath, self.dataset)
        IJ.run("As HDF5", "select=[" + datapath + "] resave_angle=[All angles] resave_channel=[All channels] resave_illumination=[All illuminations] resave_tile=[All tiles] resave_timepoint=[All Timepoints] subsampling_factors=[{ {1,1,1}, {2,2,1} }] hdf5_chunk_sizes=[{ {32,16,8}, {16,16,16} }] timepoints_per_partition=1 setups_per_partition=0 use_deflate_compression export_path=[" + exportpath + "]")

    def _apply_single_angle_affine(self, dataset, angle_label, prefix, same_flags, matrix):
        IJ.run(
            "Apply Transformations",
            "select=[" + dataset + "] "
            "apply_to_angle=[Single angle (Select from List)] "
            "apply_to_channel=[All channels] apply_to_illumination=[All illuminations] "
            "apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] "
            "processing_angle=[angle " + angle_label + "] "
            "transformation=Affine apply=[Current view transformations (appends to current transforms)] " +
            same_flags + prefix + "_angle_" + angle_label + "=[" + matrix + "]"
        )

    def _apply_single_angle_translation(self, dataset, angle_label, prefix, same_flags, vector):
        IJ.run(
            "Apply Transformations",
            "select=[" + dataset + "] "
            "apply_to_angle=[Single angle (Select from List)] "
            "apply_to_channel=[All channels] apply_to_illumination=[All illuminations] "
            "apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] "
            "processing_angle=[angle " + angle_label + "] "
            "transformation=Translation apply=[Current view transformations (appends to current transforms)] " +
            same_flags + prefix + "_angle_" + angle_label + "=[" + vector + "]"
        )

    def _apply_single_angle_rotation_x(self, dataset, angle_label, prefix, same_flags, rotation):
        IJ.run(
            "Apply Transformations",
            "select=[" + dataset + "] "
            "apply_to_angle=[Single angle (Select from List)] "
            "apply_to_channel=[All channels] apply_to_illumination=[All illuminations] "
            "apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] "
            "processing_angle=[angle " + angle_label + "] "
            "transformation=Rigid apply=[Current view transformations (appends to current transforms)] "
            "define=[Rotation around axis] " + same_flags +
            "axis_" + prefix + "_angle_" + angle_label + "=x-axis "
            "rotation_" + prefix + "_angle_" + angle_label + "=" + rotation
        )

    def _apply_single_view_transform(self):
        zplanes = self.dims[2]
        xdim = self.dims[0]
        ydim = self.dims[1]
        pz = self.dims[7]

        Angle_ = 2 * self.angle
        second_angle = self._expected_second_angle()
        physical_angle = str(self.detected_angles[0])
        xml_angle = self._single_view_angle_for_macro()

        zdim = math.floor(zplanes * pz / self.px)
        mirror_angle = (math.pi / 180) * self.angle
        tan0 = math.tan(mirror_angle)
        ydim_deskewed = math.floor(ydim + zdim * tan0)
        zdim_correct_shift = math.floor(zdim / math.cos(mirror_angle))
        tan0 = IJ.d2s(tan0, 6)
        datapath = os.path.join(self.datapath, self.dataset)

        prefix, same_flags = self._time_channel_prefix_and_flags(False)

        IJ.log(
            "Applying single-view dOPM transform for physical angle" + physical_angle +
            " to XML angle " + xml_angle
        )

        # In a two-view dataset these transforms are often applied with
        # apply_to_angle=[All angles].  For a single-view XML, explicitly target
        # the one XML angle.  This gives physical angle0 the same numeric stack
        # as two-view angle0, and physical angle70 the same numeric stack as
        # two-view angle70, while avoiding BigStitcher all-angle macro defaults
        # of identity/zero observed for single-angle XMLs.
        self._apply_single_angle_affine(
            datapath,
            xml_angle,
            prefix,
            same_flags,
            "1.0, 0.0, 0.0, 0.0, 0.0, 1.0," + tan0 + ", 0.0, 0.0, 0.0, 1.0, 0.0"
        )

        if physical_angle == second_angle:
            string = IJ.d2s(zdim_correct_shift, 0)
            self._apply_single_angle_affine(
                datapath,
                xml_angle,
                prefix,
                same_flags,
                "1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0"
            )
            self._apply_single_angle_translation(
                datapath,
                xml_angle,
                prefix,
                same_flags,
                "0,0," + string
            )
            rot = "-" + IJ.d2s(Angle_, 0)
        else:
            rot = IJ.d2s(Angle_, 0)

        string1 = IJ.d2s(math.floor(xdim / 2), 0)
        string2 = IJ.d2s(math.floor(ydim_deskewed / 2), 0)
        string3 = IJ.d2s(math.floor(zdim_correct_shift / 2), 0)

        self._apply_single_angle_translation(
            datapath,
            xml_angle,
            prefix,
            same_flags,
            "-" + string1 + ",-" + string2 + ",-" + string3
        )

        self._apply_single_angle_rotation_x(
            datapath,
            xml_angle,
            prefix,
            same_flags,
            rot
        )

        self._apply_single_angle_translation(
            datapath,
            xml_angle,
            prefix,
            same_flags,
            string1 + "," + string2 + "," + string3
        )

    def transformXMLdataset(self):
        if self.view_mode == 'single_view':
            self._apply_single_view_transform()
            return

        times = self.dims[3]
        channels = self.dims[4]
        zplanes = self.dims[2]
        xdim = self.dims[0]
        ydim = self.dims[1]
        pz = self.dims[7]

        Angle_ = 2 * self.angle
        Angle = IJ.d2s(4 * self.angle, 0)

        zdim = math.floor(zplanes * pz / self.px)
        mirror_angle = (math.pi / 180) * self.angle
        tan0 = math.tan(mirror_angle)
        ydim_deskewed = math.floor(ydim + zdim * tan0)
        zdim_correct_shift = math.floor(zdim / math.cos(mirror_angle))
        tan0 = IJ.d2s(tan0, 6)
        datapath = os.path.join(self.datapath, self.dataset)

        if (times.find('-') == -1 and times.find(',') == -1) and (len(self.csvtoarray(channels, 'int')) > 1):
            print('single time, multiple channel')
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_channels same_transformation_for_all_angles timepoint_" + times + "_all_channels_illumination_0_all_angles=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0," + tan0 + ", 0.0, 0.0, 0.0, 1.0, 0.0]")
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_channels timepoint_" + times + "_all_channels_illumination_0_angle_" + Angle + "=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0]")
            string = IJ.d2s(zdim_correct_shift, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_channels timepoint_" + times + "_all_channels_illumination_0_angle_" + Angle + "=[0,0," + string + "]")
            string1 = IJ.d2s(math.floor(xdim / 2), 0)
            string2 = IJ.d2s(math.floor(ydim_deskewed / 2), 0)
            string3 = IJ.d2s(math.floor(zdim_correct_shift / 2), 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_channels same_transformation_for_all_angles timepoint_" + times + "_all_channels_illumination_0_all_angles=[-" + string1 + ",-" + string2 + ",-" + string3 + "]")
            string = IJ.d2s(Angle_, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle 0] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] same_transformation_for_all_channels axis_timepoint_" + times + "_all_channels_illumination_0_angle_0=x-axis rotation_timepoint_" + times + "_all_channels_illumination_0_angle_0=" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] same_transformation_for_all_channels axis_timepoint_" + times + "_all_channels_illumination_0_angle_" + Angle + "=x-axis rotation_timepoint_" + times + "_all_channels_illumination_0_angle_" + Angle + "=-" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_channels same_transformation_for_all_angles timepoint_" + times + "_all_channels_illumination_0_all_angles=[" + string1 + "," + string2 + "," + string3 + "]")

        elif (times.find('-') == -1 and times.find(',') == -1) and (len(self.csvtoarray(channels, 'int')) == 1):
            print('single time, single channel')
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_angles timepoint_" + times + "_channel_" + channels + "_illumination_0_all_angles=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0," + tan0 + ", 0.0, 0.0, 0.0, 1.0, 0.0]")
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Affine apply=[Current view transformations (appends to current transforms)] timepoint_" + times + "_channel_" + channels + "_illumination_0_angle_" + Angle + "=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0]")
            string = IJ.d2s(zdim_correct_shift, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Translation apply=[Current view transformations (appends to current transforms)] timepoint_" + times + "_channel_" + channels + "_illumination_0_angle_" + Angle + "=[0,0," + string + "]")
            string1 = IJ.d2s(math.floor(xdim / 2), 0)
            string2 = IJ.d2s(math.floor(ydim_deskewed / 2), 0)
            string3 = IJ.d2s(math.floor(zdim_correct_shift / 2), 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_angles timepoint_" + times + "_channel_" + channels + "_illumination_0_all_angles=[-" + string1 + ",-" + string2 + ",-" + string3 + "]")
            string = IJ.d2s(Angle_, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle 0] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] axis_timepoint_" + times + "_channel_" + channels + "_illumination_0_angle_0=x-axis rotation_timepoint_" + times + "_channel_" + channels + "_illumination_0_angle_0=" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] axis_timepoint_" + times + "_channel_" + channels + "_illumination_0_angle_" + Angle + "=x-axis rotation_timepoint_" + times + "_channel_" + channels + "_illumination_0_angle_" + Angle + "=-" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_angles timepoint_" + times + "_channel_" + channels + "_illumination_0_all_angles=[" + string1 + "," + string2 + "," + string3 + "]")

        elif (times.find('-') != -1 or times.find(',') != -1) and (len(self.csvtoarray(channels, 'int')) == 1):
            print('multiple time, single channel')
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_angles all_timepoints_channel_" + channels + "_illumination_0_all_angles=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0," + tan0 + ", 0.0, 0.0, 0.0, 1.0, 0.0]")
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints all_timepoints_channel_" + channels + "_illumination_0_angle_" + Angle + "=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0]")
            string = IJ.d2s(zdim_correct_shift, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints all_timepoints_channel_" + channels + "_illumination_0_angle_" + Angle + "=[0,0," + string + "]")
            string1 = IJ.d2s(math.floor(xdim / 2), 0)
            string2 = IJ.d2s(math.floor(ydim_deskewed / 2), 0)
            string3 = IJ.d2s(math.floor(zdim_correct_shift / 2), 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_angles all_timepoints_channel_" + channels + "_illumination_0_all_angles=[-" + string1 + ",-" + string2 + ",-" + string3 + "]")
            string = IJ.d2s(Angle_, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle 0] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] same_transformation_for_all_timepoints axis_all_timepoints_channel_" + channels + "_illumination_0_angle_0=x-axis rotation_all_timepoints_channel_" + channels + "_illumination_0_angle_0=" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] same_transformation_for_all_timepoints axis_all_timepoints_channel_" + channels + "_illumination_0_angle_" + Angle + "=x-axis rotation_all_timepoints_channel_" + channels + "_illumination_0_angle_" + Angle + "=-" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_angles all_timepoints_channel_" + channels + "_illumination_0_all_angles=[" + string1 + "," + string2 + "," + string3 + "]")

        elif (times.find('-') != -1 or times.find(',') != -1) and (len(self.csvtoarray(channels, 'int')) > 1):
            print('multiple time, multiple channel')
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_angles same_transformation_for_all_tiles all_timepoints_all_channels_illumination_0_all_angles=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0," + tan0 + ", 0.0, 0.0, 0.0, 1.0, 0.0]")
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Affine apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_tiles all_timepoints_all_channels_illumination_0_angle_" + Angle + "=[1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0, 0.0]")
            string = IJ.d2s(zdim_correct_shift, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_tiles all_timepoints_all_channels_illumination_0_angle_" + Angle + "=[0,0," + string + "]")
            string1 = IJ.d2s(math.floor(xdim / 2), 0)
            string2 = IJ.d2s(math.floor(ydim_deskewed / 2), 0)
            string3 = IJ.d2s(math.floor(zdim_correct_shift / 2), 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_angles same_transformation_for_all_tiles all_timepoints_all_channels_illumination_0_all_angles=[-" + string1 + ",-" + string2 + ",-" + string3 + "]")
            string = IJ.d2s(Angle_, 0)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle 0] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_tiles axis_all_timepoints_all_channels_illumination_0_angle_0=x-axis rotation_all_timepoints_all_channels_illumination_0_angle_0=" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[Single angle (Select from List)] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] processing_angle=[angle " + Angle + "] transformation=Rigid apply=[Current view transformations (appends to current transforms)] define=[Rotation around axis] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_tiles axis_all_timepoints_all_channels_illumination_0_angle_" + Angle + "=x-axis rotation_all_timepoints_all_channels_illumination_0_angle_" + Angle + "=-" + string)
            IJ.run("Apply Transformations", "select=[" + datapath + "] apply_to_angle=[All angles] apply_to_channel=[All channels] apply_to_illumination=[All illuminations] apply_to_tile=[All tiles] apply_to_timepoint=[All Timepoints] transformation=Translation apply=[Current view transformations (appends to current transforms)] same_transformation_for_all_timepoints same_transformation_for_all_channels same_transformation_for_all_angles same_transformation_for_all_tiles all_timepoints_all_channels_illumination_0_all_angles=[" + string1 + "," + string2 + "," + string3 + "]")
        else:
            print('incorrect format')


class mvrgetvolumes(object):

    BB = 'All Views'

    def __init__(self, **kwargs):
        valid_keys = ["datapath", "savepath", "binning", "dataset"]
        for key in valid_keys:
            setattr(self, key, kwargs.get(key))

        self.dataset = self._resolve_dataset_name(getattr(self, 'dataset', None))

        info = self.getXMLinfo()
        self.xml_tiles = info[0]
        self.xml_times = info[1]
        self.xml_angles = info[2]
        self.xml_tile_name_map = info[3]
        self.xml_timepoint_choice_map = info[4]

    def _resolve_dataset_name(self, dataset):
        if dataset is not None:
            dataset_path = os.path.join(self.datapath, dataset)
            if not os.path.exists(dataset_path):
                raise IOError("Dataset XML not found: " + dataset_path)
            return dataset

        default_dataset = os.path.join(self.datapath, 'dataset.xml')
        if os.path.exists(default_dataset):
            return 'dataset.xml'

        candidates = []
        for each in os.listdir(self.datapath):
            if each.startswith('dataset_') and each.endswith('.xml'):
                candidates.append(each)

        candidates.sort()

        if len(candidates) == 1:
            IJ.log("Auto-selected dataset: " + candidates[0])
            return candidates[0]

        if len(candidates) == 0:
            raise IOError(
                "No dataset XML found in folder: " + self.datapath +
                ". Expected dataset.xml or dataset_*.xml"
            )

        raise ValueError(
            "Multiple dataset XML files found in folder: " + self.datapath +
            ". Please specify one explicitly using dataset='...'. Found: " +
            ', '.join(candidates)
        )

    def createFolder(self, fusedpath):
        try:
            if not os.path.exists(fusedpath):
                os.makedirs(fusedpath)
        except OSError:
            print('Error: Creating directory. ' + fusedpath)

    def csvtoarray(self, csv_string, type_):
        csv_vals = csv_string.split(',')
        out = []
        for i in csv_vals:
            if type_ == 'int':
                out.append(int(i))
            elif type_ == 'float':
                out.append(float(i))
            elif type_ == 'string':
                out.append(str(i))
        return out

    def _normalize_tile_choice_label(self, raw_label, tile_id):
        if raw_label is None:
            return "tile " + str(tile_id)

        label = str(raw_label).strip()
        if label == "":
            return "tile " + str(tile_id)

        low = label.lower()
        if low.startswith("tile "):
            return label

        # XML often stores tile names as "2", "3", ...
        # but the Fiji chooser expects "tile 2", "tile 3", ...
        return "tile " + label

    def getXMLinfo(self):
        file = os.path.join(self.datapath, self.dataset)
        root = ET.parse(file).getroot()

        tile_ids = []
        times_list = []
        angle_list = []
        tile_name_map = {}
        timepoint_choice_map = {}

        tp_node = root.find('./SequenceDescription/Timepoints')
        if tp_node is None:
            raise ValueError("Could not find Timepoints in XML: " + file)

        integerpattern_node = tp_node.find('integerpattern')
        if integerpattern_node is None or integerpattern_node.text is None:
            raise ValueError("Could not find timepoint integerpattern in XML: " + file)

        times_list = self.csvtoarray(integerpattern_node.text, 'int')
        times_list.sort()

        for node in root.findall('./SequenceDescription/ViewSetups/ViewSetup/attributes'):
            elem = node.find('tile')
            if elem is not None and elem.text is not None:
                tile_ids.append(int(elem.text))

        tile_ids = sorted(list(set(tile_ids)))

        for node in root.findall('./SequenceDescription/ViewSetups/Attributes/Angle'):
            name_node = node.find('name')
            if name_node is not None and name_node.text is not None:
                angle_list.append(name_node.text)

        for node in root.findall('./SequenceDescription/ViewSetups/Attributes/Tile'):
            id_node = node.find('id')
            name_node = node.find('name')
            if id_node is not None and name_node is not None:
                if id_node.text is not None and name_node.text is not None:
                    try:
                        tile_id = int(id_node.text)
                        tile_name_map[tile_id] = self._normalize_tile_choice_label(name_node.text, tile_id)
                    except:
                        pass

        for tp in times_list:
            timepoint_choice_map[tp] = "Timepoint " + str(tp)

        IJ.log("Dataset XML: " + self.dataset)
        IJ.log("Tile ids found: " + str(tile_ids))
        IJ.log("Tile name map: " + str(tile_name_map))
        IJ.log("Timepoints found: " + str(times_list))
        IJ.log("Angles found: " + str(angle_list))

        return [tile_ids, times_list, angle_list, tile_name_map, timepoint_choice_map]

    def getTileChoiceLabel(self, tile_id):
        if tile_id in self.xml_tile_name_map:
            return self.xml_tile_name_map[tile_id]
        return "tile " + str(tile_id)

    def getTimepointChoiceLabel(self, timepoint_id):
        if timepoint_id in self.xml_timepoint_choice_map:
            return self.xml_timepoint_choice_map[timepoint_id]
        return "Timepoint " + str(timepoint_id)

    def getDefaultTileId(self):
        if len(self.xml_tiles) == 0:
            raise ValueError("No tiles found in dataset XML: " + self.dataset)
        return self.xml_tiles[0]

    def getDefaultTimepointId(self):
        if len(self.xml_times) == 0:
            raise ValueError("No timepoints found in dataset XML: " + self.dataset)
        return self.xml_times[0]

    def getFusedVolumes(self):
        datasepath = os.path.join(self.datapath, self.dataset)

        dataset_tag = os.path.splitext(self.dataset)[0]
        fusedfolder = dataset_tag + '_fused_binning_' + self.binning
        fusedpath = os.path.join(self.savepath, fusedfolder)
        self.createFolder(fusedpath)

        tiles = self.xml_tiles
        times = self.xml_times

        if len(tiles) == 1:
            IJ.run(
                "Fuse",
                "select=[" + datasepath + "] "
                "process_angle=[All angles] process_channel=[All channels] "
                "process_illumination=[All illuminations] process_tile=[All tiles] "
                "process_timepoint=[All Timepoints] bounding_box=[" + self.BB + "] "
                "downsampling=" + self.binning + " pixel_type=[16-bit unsigned integer] "
                "interpolation=[Linear Interpolation] image=[Precompute Image] "
                "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                "blend produce=[Each timepoint & channel] "
                "fused_image=[Save as (compressed) TIFF stacks] "
                "output_file_directory=[" + fusedpath + "] "
                "filename_addition=tile_" + str(tiles[0])
            )
        else:
            if len(times) == 1:
                for tile in tiles:
                    tile_label = self.getTileChoiceLabel(tile)
                    IJ.log("Fusing dataset=" + self.dataset + ", tile=" + str(tile) + ", tile_label=" + tile_label)
                    IJ.run(
                        "Fuse",
                        "select=[" + datasepath + "] "
                        "process_angle=[All angles] process_channel=[All channels] "
                        "process_illumination=[All illuminations] "
                        "process_tile=[Single tile (Select from List)] "
                        "process_timepoint=[All Timepoints] "
                        "processing_tile=[" + tile_label + "] "
                        "bounding_box=[" + self.BB + "] "
                        "downsampling=" + self.binning + " "
                        "pixel_type=[16-bit unsigned integer] "
                        "interpolation=[Linear Interpolation] image=[Precompute Image] "
                        "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                        "blend produce=[Each timepoint & channel] "
                        "fused_image=[Save as (compressed) TIFF stacks] "
                        "output_file_directory=[" + fusedpath + "] "
                        "filename_addition=tile_" + str(tile)
                    )
            else:
                for time in times:
                    tp_label = self.getTimepointChoiceLabel(time)
                    for tile in tiles:
                        tile_label = self.getTileChoiceLabel(tile)
                        IJ.log("Fusing dataset=" + self.dataset + ", tile=" + str(tile) + ", tile_label=" + tile_label + ", time=" + str(time))
                        IJ.run(
                            "Fuse",
                            "select=[" + datasepath + "] "
                            "process_angle=[All angles] process_channel=[All channels] "
                            "process_illumination=[All illuminations] "
                            "process_tile=[Single tile (Select from List)] "
                            "process_timepoint=[Single Timepoint (Select from List)] "
                            "processing_tile=[" + tile_label + "] "
                            "processing_timepoint=[" + tp_label + "] "
                            "bounding_box=[" + self.BB + "] "
                            "downsampling=" + self.binning + " "
                            "pixel_type=[16-bit unsigned integer] "
                            "interpolation=[Linear Interpolation] image=[Precompute Image] "
                            "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                            "blend produce=[Each timepoint & channel] "
                            "fused_image=[Save as (compressed) TIFF stacks] "
                            "output_file_directory=[" + fusedpath + "] "
                            "filename_addition=tile_" + str(tile)
                        )

    def getSingleView(self, view):
        datasepath = os.path.join(self.datapath, self.dataset)

        dataset_tag = os.path.splitext(self.dataset)[0]
        fusedfolder = dataset_tag + '_view_' + str(int(view) + 1) + '_binning_' + self.binning
        fusedpath = os.path.join(self.savepath, fusedfolder)
        self.createFolder(fusedpath)

        tiles = self.xml_tiles
        times = self.xml_times

        IJ.log("getSingleView start: dataset=" + self.dataset + ", view=" + str(view) + ", binning=" + str(self.binning))

        if len(tiles) == 1:
            tile_label = self.getTileChoiceLabel(tiles[0])
            IJ.run(
                "Fuse",
                "select=[" + datasepath + "] "
                "process_angle=[Single angle (Select from List)] "
                "process_channel=[All channels] process_illumination=[All illuminations] "
                "process_tile=[Single tile (Select from List)] process_timepoint=[All Timepoints] "
                "processing_angle=[angle " + self.xml_angles[int(view)] + "] "
                "processing_tile=[" + tile_label + "] "
                "bounding_box=[" + self.BB + "] "
                "downsampling=" + self.binning + " "
                "pixel_type=[16-bit unsigned integer] "
                "interpolation=[Linear Interpolation] image=[Precompute Image] "
                "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                "blend produce=[Each timepoint & channel] "
                "fused_image=[Save as (compressed) TIFF stacks] "
                "output_file_directory=[" + fusedpath + "] "
                "filename_addition=tile_" + str(tiles[0])
            )
        else:
            if len(times) == 1:
                for tile in tiles:
                    tile_label = self.getTileChoiceLabel(tile)
                    IJ.log("Single-view fuse dataset=" + self.dataset + ", view=" + str(view) + ", tile=" + str(tile) + ", tile_label=" + tile_label)
                    IJ.run(
                        "Fuse",
                        "select=[" + datasepath + "] "
                        "process_angle=[Single angle (Select from List)] "
                        "process_channel=[All channels] process_illumination=[All illuminations] "
                        "process_tile=[Single tile (Select from List)] "
                        "process_timepoint=[All Timepoints] "
                        "processing_angle=[angle " + self.xml_angles[int(view)] + "] "
                        "processing_tile=[" + tile_label + "] "
                        "bounding_box=[" + self.BB + "] "
                        "downsampling=" + self.binning + " "
                        "pixel_type=[16-bit unsigned integer] "
                        "interpolation=[Linear Interpolation] image=[Precompute Image] "
                        "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                        "blend produce=[Each timepoint & channel] "
                        "fused_image=[Save as (compressed) TIFF stacks] "
                        "output_file_directory=[" + fusedpath + "] "
                        "filename_addition=tile_" + str(tile)
                    )
            else:
                for time in times:
                    tp_label = self.getTimepointChoiceLabel(time)
                    for tile in tiles:
                        tile_label = self.getTileChoiceLabel(tile)
                        IJ.log("Single-view fuse dataset=" + self.dataset + ", view=" + str(view) + ", tile=" + str(tile) + ", tile_label=" + tile_label + ", time=" + str(time))
                        IJ.run(
                            "Fuse",
                            "select=[" + datasepath + "] "
                            "process_angle=[Single angle (Select from List)] "
                            "process_channel=[All channels] process_illumination=[All illuminations] "
                            "process_tile=[Single tile (Select from List)] "
                            "process_timepoint=[Single Timepoint (Select from List)] "
                            "processing_angle=[angle " + self.xml_angles[int(view)] + "] "
                            "processing_tile=[" + tile_label + "] "
                            "processing_timepoint=[" + tp_label + "] "
                            "bounding_box=[" + self.BB + "] "
                            "downsampling=" + self.binning + " "
                            "pixel_type=[16-bit unsigned integer] "
                            "interpolation=[Linear Interpolation] image=[Precompute Image] "
                            "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                            "blend produce=[Each timepoint & channel] "
                            "fused_image=[Save as (compressed) TIFF stacks] "
                            "output_file_directory=[" + fusedpath + "] "
                            "filename_addition=tile_" + str(tile)
                        )

    def getSingleViewSubset(self, view, times, tiles):
        datasepath = os.path.join(self.datapath, self.dataset)

        dataset_tag = os.path.splitext(self.dataset)[0]
        fusedfolder = dataset_tag + '_subset_view_' + str(int(view) + 1) + '_binning_' + self.binning
        fusedpath = os.path.join(self.savepath, fusedfolder)
        self.createFolder(fusedpath)

        for time in times:
            tp_label = self.getTimepointChoiceLabel(time)
            for tile in tiles:
                tile_label = self.getTileChoiceLabel(tile)
                IJ.log("Subset single-view fuse dataset=" + self.dataset + ", view=" + str(view) + ", tile=" + str(tile) + ", tile_label=" + tile_label + ", time=" + str(time))
                IJ.run(
                    "Fuse",
                    "select=[" + datasepath + "] "
                    "process_angle=[Single angle (Select from List)] "
                    "process_channel=[All channels] process_illumination=[All illuminations] "
                    "process_tile=[Single tile (Select from List)] "
                    "process_timepoint=[Single Timepoint (Select from List)] "
                    "processing_angle=[angle " + self.xml_angles[int(view)] + "] "
                    "processing_tile=[" + tile_label + "] "
                    "processing_timepoint=[" + tp_label + "] "
                    "bounding_box=[" + self.BB + "] "
                    "downsampling=" + self.binning + " "
                    "pixel_type=[16-bit unsigned integer] "
                    "interpolation=[Linear Interpolation] image=[Precompute Image] "
                    "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                    "blend produce=[Each timepoint & channel] "
                    "fused_image=[Save as (compressed) TIFF stacks] "
                    "output_file_directory=[" + fusedpath + "] "
                    "filename_addition=tile_" + str(tile)
                )

    def getFusedVolumesSubset(self, times, tiles):
        datasepath = os.path.join(self.datapath, self.dataset)

        dataset_tag = os.path.splitext(self.dataset)[0]
        fusedfolder = dataset_tag + '_subset_fused_binning_' + self.binning
        fusedpath = os.path.join(self.savepath, fusedfolder)
        self.createFolder(fusedpath)

        for time in times:
            tp_label = self.getTimepointChoiceLabel(time)
            for tile in tiles:
                tile_label = self.getTileChoiceLabel(tile)
                IJ.log("Subset fused dataset=" + self.dataset + ", tile=" + str(tile) + ", tile_label=" + tile_label + ", time=" + str(time))
                IJ.run(
                    "Fuse",
                    "select=[" + datasepath + "] "
                    "process_angle=[All angles] process_channel=[All channels] "
                    "process_illumination=[All illuminations] "
                    "process_tile=[Single tile (Select from List)] "
                    "process_timepoint=[Single Timepoint (Select from List)] "
                    "processing_tile=[" + tile_label + "] "
                    "processing_timepoint=[" + tp_label + "] "
                    "bounding_box=[" + self.BB + "] "
                    "downsampling=" + self.binning + " "
                    "pixel_type=[16-bit unsigned integer] "
                    "interpolation=[Linear Interpolation] image=[Precompute Image] "
                    "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
                    "blend produce=[Each timepoint & channel] "
                    "fused_image=[Save as (compressed) TIFF stacks] "
                    "output_file_directory=[" + fusedpath + "] "
                    "filename_addition=tile_" + str(tile)
                )

    def ResaveXMLtoHDF5(self):
        datapath = os.path.join(self.datapath, self.dataset)
        IJ.run(
            "As HDF5",
            "select=[" + datapath + "] "
            "resave_angle=[All angles] resave_channel=[All channels] "
            "resave_illumination=[All illuminations] resave_tile=[All tiles] "
            "resave_timepoint=[All Timepoints] "
            "subsampling_factors=[{ {1,1,1}, {2,2,1} }] "
            "hdf5_chunk_sizes=[{ {32,16,8}, {16,16,16} }] "
            "timepoints_per_partition=1 setups_per_partition=0 "
            "use_deflate_compression export_path=[" + datapath + "]"
        )

    def CheckTimesTilesSubsets(self, tiles_chosen, times_chosen):
        tiles = self.xml_tiles
        times = self.xml_times

        if "-" in tiles_chosen:
            tiles_chosen = tiles_chosen.split('-')
            tiles_chosen = range(int(tiles_chosen[0]), int(tiles_chosen[1]) + 1, 1)
            if set(tiles_chosen) <= set(tiles):
                tiles_chosen = list(set(tiles_chosen))
            else:
                print 'no valid tiles chosen aborting'
                return
        elif "," in tiles_chosen:
            tiles_chosen = tiles_chosen.split(',')
            tiles_chosen = [int(x) for x in tiles_chosen]
            if set(tiles_chosen) <= set(tiles):
                tiles_chosen = list(set(tiles_chosen))
            else:
                print 'no valid tiles chosen aborting'
                return
        elif tiles_chosen:
            if not isinstance(tiles_chosen, list):
                tiles_chosen = [int(tiles_chosen)]
            if set(tiles_chosen) <= set(tiles):
                tiles_chosen = list(set(tiles_chosen))
            else:
                print 'no valid tiles chosen aborting'
                return
        else:
            print 'no valid tiles chosen aborting'
            return

        if "-" in times_chosen:
            times_chosen = times_chosen.split('-')
            times_chosen = range(int(times_chosen[0]), int(times_chosen[1]) + 1, 1)
            if set(times_chosen) <= set(times):
                times_chosen = list(set(times_chosen))
            else:
                print 'no valid times chosen aborting'
                return
        elif "," in times_chosen:
            times_chosen = times_chosen.split(',')
            times_chosen = [int(x) for x in times_chosen]
            if set(times_chosen) <= set(times):
                times_chosen = list(set(times_chosen))
            else:
                print 'no valid times chosen aborting'
                return
        elif times_chosen:
            if not isinstance(times_chosen, list):
                times_chosen = [int(times_chosen)]
            if set(times_chosen) <= set(times):
                times_chosen = list(set(times_chosen))
            else:
                print 'no valid times chosen aborting'
                return
        else:
            print 'no valid times chosen aborting'
            return

        print 'times and tiles valid starting processing.....'
        return [True, sorted(times_chosen), sorted(tiles_chosen)]


class defineboundingbox(object):

    def __init__(self, **kwargs):
        valid_keys = ["datapath", "beadpath", "dataset", "rawzplanes", "prismangle"]
        for key in valid_keys:
            setattr(self, key, kwargs.get(key))

        if getattr(self, 'dataset', None) is None:
            self.dataset = 'dataset.xml'

    def getXMLBoundingBox(self, datapath):
        file = os.path.join(datapath, self.dataset)
        root = ET.parse(file).getroot()

        bb_root = root.find('./BoundingBoxes')
        if bb_root is None:
            return None

        for boundingbox in bb_root:
            if boundingbox.get('name') == 'My Bounding Box':
                min_ = boundingbox.find('min').text.split(' ')
                max_ = boundingbox.find('max').text.split(' ')
                return [min_, max_]
        return None

    def defineBoundingBox(self, datapath):
        datasepath = os.path.join(datapath, self.dataset)
        IJ.run(
            "Define Bounding Box",
            "select=[" + datasepath + "] "
            "process_angle=[All angles] process_channel=[All channels] "
            "process_illumination=[All illuminations] process_tile=[All tiles] "
            "process_timepoint=[All Timepoints] "
            "bounding_box=[Define using the BigDataViewer interactively] "
            "bounding_box_name=[My Bounding Box]"
        )

    def defineBoundingBoxNoInteraction(self, datapath):
        datasepath = os.path.join(datapath, self.dataset)
        IJ.run(
            "Define Bounding Box",
            "select=[" + datasepath + "] "
            "process_angle=[All angles] process_channel=[All channels] "
            "process_illumination=[All illuminations] process_tile=[All tiles] "
            "process_timepoint=[All Timepoints] "
            "bounding_box=[Maximal Bounding Box spanning all transformed views] "
            "bounding_box_name=[My Bounding Box] "
            "minimal_x=0 minimal_y=0 minimal_z=0 "
            "maximal_x=100 maximal_y=100 maximal_z=100"
        )

    def modifyBoundingBox(self, datapath, BB):
        datasepath = os.path.join(datapath, self.dataset)
        IJ.run(
            "Define Bounding Box",
            "select=[" + datasepath + "] "
            "process_angle=[All angles] process_channel=[All channels] "
            "process_illumination=[All illuminations] process_tile=[All tiles] "
            "process_timepoint=[All Timepoints] "
            "bounding_box=[Modify pre-defined Bounding Box] "
            "bounding_box_name=[My Bounding Box] "
            "bounding_box_title=[My Bounding Box] "
            "minimal_x=" + BB[0][0] + " "
            "minimal_y=" + BB[0][1] + " "
            "minimal_z=" + BB[0][2] + " "
            "maximal_x=" + BB[1][0] + " "
            "maximal_y=" + BB[1][1] + " "
            "maximal_z=" + BB[1][2]
        )

    def OptimalBoundingBox(self, datapath):
        IJ.log(str(datapath))

        if getattr(self, 'rawzplanes', None) is not None and getattr(self, 'prismangle', None) is not None:
            zstack_microns = int(self.rawzplanes)
            prism_angle = float(self.prismangle)
        else:
            # Backward-compatible fallback for older callers. The main refactored
            # workflow passes these values directly and no longer depends on
            # dopmsettings.xml.
            settingsfile = os.path.join(datapath, 'dopmsettings.xml')
            IJ.log(str(settingsfile))
            settings = readdopmxml(settingsfile)
            zstack_microns = int(settings['rawzplanes'])
            prism_angle = float(settings['prismangle'])

        datapath_ = os.path.join(datapath, self.dataset)
        IJ.log(str(datapath_))

        helper = mvrgetvolumes(
            datapath=datapath,
            savepath=datapath,
            binning="1",
            dataset=self.dataset
        )

        default_tile = helper.getDefaultTileId()
        default_timepoint = helper.getDefaultTimepointId()
        tile_label = helper.getTileChoiceLabel(default_tile)
        tp_label = helper.getTimepointChoiceLabel(default_timepoint)

        IJ.log("OptimalBoundingBox using tile_label=" + tile_label + ", tp_label=" + tp_label)

        IJ.run(
            "Fuse",
            "select=[" + datapath_ + "] "
            "process_angle=[All angles] "
            "process_channel=[Single channel (Select from List)] "
            "process_illumination=[All illuminations] "
            "process_tile=[Single tile (Select from List)] "
            "process_timepoint=[Single Timepoint (Select from List)] "
            "processing_channel=[channel 0] "
            "processing_tile=[" + tile_label + "] "
            "processing_timepoint=[" + tp_label + "] "
            "bounding_box=[All Views] downsampling=1 "
            "pixel_type=[16-bit unsigned integer] "
            "interpolation=[Linear Interpolation] image=[Precompute Image] "
            "interest_points_for_non_rigid=[-= Disable Non-Rigid =-] "
            "blend produce=[Each timepoint & channel] "
            "fused_image=[Display using ImageJ]"
        )

        imp = IJ.getImage()

        offset = [
            imp.getCalibration().xOrigin / imp.getCalibration().pixelWidth,
            imp.getCalibration().yOrigin / imp.getCalibration().pixelHeight,
            imp.getCalibration().zOrigin / imp.getCalibration().pixelDepth
        ]

        d = round(zstack_microns / imp.getCalibration().pixelDepth)
        d_z = round(d / math.cos(2 * prism_angle * math.pi / 180))

        bb_x = [
            0 - math.floor(offset[0]),
            imp.getWidth() - math.ceil(offset[0])
        ]

        bb_y = [
            -math.floor(offset[1]),
            imp.getHeight() - math.floor(offset[1])
        ]

        bb_z = [
            (imp.getImageStackSize() / 2 - math.floor(d_z / 2)) - math.floor(offset[2]),
            (imp.getImageStackSize() / 2 + math.floor(d_z / 2)) - math.ceil(offset[2])
        ]

        imp.close()

        bb_x = [str(x) for x in bb_x]
        bb_y = [str(x) for x in bb_y]
        bb_z = [str(x) for x in bb_z]

        IJ.log("=========================================================")
        IJ.log("recommended bounding box for diamond for x range is: ")
        IJ.log(' '.join(bb_x))
        IJ.log("recommended bounding box for diamond for y range is: ")
        IJ.log(' '.join(bb_y))
        IJ.log("recommended bounding box for diamond for z range is: ")
        IJ.log(' '.join(bb_z))
        IJ.log("--------------------------------------------------------")

        BB = [[bb_x[0], bb_y[0], bb_z[0]], [bb_x[1], bb_y[1], bb_z[1]]]
        return BB


if __name__ in ['__builtin__', '__main__']:
    IJ.log("Finished")