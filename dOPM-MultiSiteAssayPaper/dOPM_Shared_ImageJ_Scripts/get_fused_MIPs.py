#@ File(label='Choose a directory for the folder of tiff stacks', style='directory') datapath
datapath = datapath.getAbsolutePath()

from ij import IJ
from ij.io import FileSaver, Opener
from net.haesleinhuepf.clij2 import CLIJ2
from fiji.util.gui import GenericDialogPlus
import os
import glob


def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print('Error: Creating directory. ' + directory)


def getStackList(stackdir):
    files = glob.glob(os.path.join(stackdir, "*.tif"))
    files += glob.glob(os.path.join(stackdir, "*.tiff"))

    tiff_set = []
    for a_string in files:
        norm = os.path.normpath(a_string)
        parts = norm.split(os.sep)
        if 'MIP' in parts:
            continue
        tiff_set.append(norm)

    tiff_set.sort()
    return tiff_set


def getPathParts(path):
    path = os.path.normpath(path)
    drive, path_and_file = os.path.splitdrive(path)
    path, file = os.path.split(path_and_file)
    return [drive, path, file]


def openImageRobust(path_):
    path_ = os.path.normpath(path_)

    imp = None

    try:
        imp = Opener().openImage(path_)
    except:
        imp = None

    if imp is None:
        try:
            imp = IJ.openImage(path_)
        except:
            imp = None

    return imp


def getMIPsonFolder(datapath):
    MIPfolder = 'MIP'
    pathname = os.path.join(datapath, MIPfolder)
    createFolder(pathname)

    stackdir = os.path.normpath(datapath)
    tiff_set = getStackList(stackdir)

    if len(tiff_set) == 0:
        IJ.log("No TIFF stacks found in: " + stackdir)
        return

    IJ.log("Processing folder: " + datapath)

    for tiff_stack in tiff_set:
        clij2 = CLIJ2.getInstance()
        imp = openImageRobust(tiff_stack)

        if imp is None:
            IJ.log("Could not open: " + tiff_stack)
            continue

        try:
            dims = imp.getDimensions()  # x,y,c,z,t
            imageInput = clij2.push(imp)

            imageOutput1 = clij2.create([dims[0], dims[1]], imageInput.getNativeType())
            clij2.maximumZProjection(imageInput, imageOutput1)

            imageOutput2 = clij2.create([dims[3], dims[1]], imageInput.getNativeType())
            clij2.maximumXProjection(imageInput, imageOutput2)

            imageOutput3 = clij2.create([dims[0], dims[3]], imageInput.getNativeType())
            clij2.maximumYProjection(imageInput, imageOutput3)

            imageOutput4 = clij2.create([dims[0] + dims[3], dims[1]], imageInput.getNativeType())
            clij2.combineHorizontally(imageOutput1, imageOutput2, imageOutput4)

            imageOutput5 = clij2.create([dims[3], dims[1]], imageInput.getNativeType())
            imageOutput6 = clij2.create([dims[0] + dims[3], dims[1]], imageInput.getNativeType())
            clij2.combineHorizontally(imageOutput3, imageOutput5, imageOutput6)

            imageOutput7 = clij2.create([dims[0] + dims[3], dims[1] + dims[1]], imageInput.getNativeType())
            clij2.combineVertically(imageOutput4, imageOutput6, imageOutput7)

            final_imp = clij2.pull(imageOutput7)

            pathparts = getPathParts(tiff_stack)
            fname = pathparts[2].split('.', 1)
            filename = os.path.join(pathname, fname[0])

            FileSaver(final_imp).saveAsTiff(filename + '.tif')

            final_imp.close()

        finally:
            try:
                imp.close()
            except:
                pass
            clij2.clear()


def find_dataset_output_folders(root_folder, volume_type, binning):
    """
    Looks for:
        dataset_*/dataset_*_<suffix>

    where suffix is one of:
        fused_binning_X
        view_1_binning_X
        view_2_binning_X
    """
    matches = []

    if volume_type == 'fused':
        suffix = '_fused_binning_' + str(binning)
    elif volume_type == 'view_1':
        suffix = '_view_1_binning_' + str(binning)
    elif volume_type == 'view_2':
        suffix = '_view_2_binning_' + str(binning)
    else:
        raise ValueError("Unknown volume_type: " + str(volume_type))

    for each in os.listdir(root_folder):
        dataset_dir = os.path.join(root_folder, each)

        if not os.path.isdir(dataset_dir):
            continue

        if not each.startswith('dataset'):
            continue

        candidate = os.path.join(dataset_dir, each + suffix)
        if os.path.isdir(candidate):
            matches.append(candidate)

    matches.sort()
    return matches


def processRootForBinning(root_folder, volume_type, binning):
    folders = find_dataset_output_folders(root_folder, volume_type, binning)

    if len(folders) == 0:
        IJ.log("No matching dataset output folders found.")
        IJ.log("Root: " + root_folder)
        IJ.log("Type: " + volume_type)
        IJ.log("Binning: " + str(binning))
        return

    IJ.log("Found matching folders:")
    for folder in folders:
        IJ.log(folder)

    for folder in folders:
        getMIPsonFolder(folder)


def chooseModeAndRun(default_root):
    mode_choices = ["single folder", "search root for dataset folders"]
    volume_choices = ["fused", "view_1", "view_2"]
    binning_choices = ["1", "2", "4", "8", "16"]

    gui = GenericDialogPlus("Generate MIPs from deskewed dOPM TIFF stacks")
    gui.addChoice("Mode", mode_choices, mode_choices[0])
    gui.addDirectoryField("Folder", default_root)
    gui.addChoice("Volume type", volume_choices, volume_choices[0])
    gui.addChoice("Binning", binning_choices, binning_choices[0])
    gui.showDialog()

    if not gui.wasOKed():
        return

    mode = gui.getNextChoice()
    folder = gui.getNextString()
    volume_type = gui.getNextChoice()
    binning = gui.getNextChoice()

    if mode == mode_choices[0]:
        getMIPsonFolder(folder)
    else:
        processRootForBinning(folder, volume_type, binning)


if __name__ in ['__builtin__', '__main__']:
    chooseModeAndRun(datapath)