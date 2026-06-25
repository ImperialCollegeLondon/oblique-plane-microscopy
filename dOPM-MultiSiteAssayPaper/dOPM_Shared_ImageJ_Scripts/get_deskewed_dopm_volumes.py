#@ PrefService prefs
from fiji.util.gui import GenericDialogPlus
from ij import IJ
import os
from os.path import isfile
from sys import path
from java.lang.System import getProperty

code_path = getProperty('fiji.dir') + '/plugins/Scripts/dOPM'

ScriptPath = code_path + "/dopmmvr$py.class"
path.append(code_path)

if isfile(ScriptPath):
    os.remove(ScriptPath)

from dopmmvr import mvrgetvolumes


def split_dataset_path(xmlpath_):
    datapath_ = os.path.dirname(xmlpath_)
    dataset_ = os.path.basename(xmlpath_)

    if dataset_ == '':
        raise ValueError("Please select a dataset XML file, not just a folder.")

    if not dataset_.lower().endswith('.xml'):
        raise ValueError("Selected file is not an XML dataset: " + xmlpath_)

    if not os.path.exists(xmlpath_):
        raise ValueError("Selected dataset XML does not exist: " + xmlpath_)

    return datapath_, dataset_


def build_mvrgetvolumes(xmlpath_, savepath_, binning_):
    datapath_, dataset_ = split_dataset_path(xmlpath_)

    data = mvrgetvolumes(
        datapath=datapath_,
        savepath=savepath_,
        binning=binning_,
        dataset=dataset_
    )
    return data


def find_dataset_xmls(folder):
    xmls = []
    for each in os.listdir(folder):
        if each.startswith('dataset') and each.lower().endswith('.xml'):
            full = os.path.join(folder, each)
            if os.path.isfile(full):
                xmls.append(each)
    xmls.sort()
    return xmls


def make_xml_specific_savepath(savepath_root, dataset_name):
    dataset_stem = os.path.splitext(dataset_name)[0]
    xml_savepath = os.path.join(savepath_root, dataset_stem)
    if not os.path.exists(xml_savepath):
        os.makedirs(xml_savepath)
    return xml_savepath


def run_subset_dialog(data, mode, view_=None):
    subset_choices = ["no", "yes"]

    gui = GenericDialogPlus("Do you want to process a subset?")
    gui.addChoice("Do you want to process a subset of times and tiles?", subset_choices, subset_choices[0])
    gui.showDialog()

    if not gui.wasOKed():
        return

    do_subset = (gui.getNextChoice() == subset_choices[1])

    if do_subset:
        gui = GenericDialogPlus("processing a subset")
        [tiles, times, angles, tile_name_map, timepoint_choice_map] = data.getXMLinfo()
        tiles = [str(x) for x in tiles]
        times = [str(x) for x in times]

        gui.addChoice("tiles found", tiles, str(tiles[0]))
        gui.addToSameRow()
        gui.addStringField("Enter tiles as csv '1,2' or hyphen '1-2':", "")
        gui.addChoice("times found", times, str(times[0]))
        gui.addToSameRow()
        gui.addStringField("Enter times as csv '1,2' or hyphen '1-2':", "")
        gui.showDialog()

        if gui.wasOKed():
            gui.getNextChoice()
            tiles_chosen = gui.getNextString()
            gui.getNextChoice()
            times_chosen = gui.getNextString()

            selection = data.CheckTimesTilesSubsets(tiles_chosen, times_chosen)

            if selection:
                print 'fusing subset'
                if mode == "fused":
                    data.getFusedVolumesSubset(selection[1], selection[2])
                elif mode == "single":
                    data.getSingleViewSubset(view_, selection[1], selection[2])
                elif mode == "both":
                    data.getSingleViewSubset("0", selection[1], selection[2])
                    data.getSingleViewSubset("1", selection[1], selection[2])
    else:
        print 'fusing entire dataset'
        if mode == "fused":
            data.getFusedVolumes()
        elif mode == "single":
            data.getSingleView(view_)
        elif mode == "both":
            data.getSingleView("0")
            data.getSingleView("1")


def run_whole_dataset(data, mode, view_=None):
    if mode == "fused":
        data.getFusedVolumes()
    elif mode == "single":
        data.getSingleView(view_)
    elif mode == "both":
        data.getSingleView("0")
        data.getSingleView("1")


def run_batch_for_all_xmls(xml_folder_, savepath_, binning_, mode, view_=None):
    xmls = find_dataset_xmls(xml_folder_)

    if len(xmls) == 0:
        raise ValueError("No dataset XML files found in folder: " + xml_folder_)

    IJ.log("Found dataset XMLs: " + ", ".join(xmls))

    for dataset_name in xmls:
        IJ.log("Processing dataset XML: " + dataset_name)

        xml_savepath = make_xml_specific_savepath(savepath_, dataset_name)

        data = mvrgetvolumes(
            datapath=xml_folder_,
            savepath=xml_savepath,
            binning=binning_,
            dataset=dataset_name
        )

        run_whole_dataset(data, mode, view_=view_)

        IJ.log("Finished dataset XML: " + dataset_name)


def main():
    view_choices = ["0", "1"]
    crop_choices = ["no", "yes"]
    choices = [
        "fused",
        "single view",
        "single view both",
        "batch fused (all xmls in folder)",
        "batch single view (all xmls in folder)",
        "batch single view both (all xmls in folder)"
    ]
    binning_choices = ["1", "2", "4", "8", "16"]

    gui = GenericDialogPlus("Extract deskewed dOPM data using multi-view reconstruction plugin as tiff zstacks")
    gui.addChoice("How do you want to extract the tiff stacks", choices, choices[0])
    gui.addChoice("Do you want to apply a bounding box?", crop_choices, crop_choices[0])
    gui.showDialog()

    if gui.wasOKed():
        inChoice = gui.getNextChoice()
        cropChoice = gui.getNextChoice()

        if cropChoice == crop_choices[1]:
            BB = "My Bounding Box"
        else:
            BB = 'All Views'

        mvrgetvolumes.BB = BB

        if inChoice == choices[0]:
            gui = GenericDialogPlus(inChoice)
            gui.addFileField("Select xml dataset", prefs.get(None, "xmlpath_", ""))
            gui.addDirectoryField("Select save path", prefs.get(None, "savepath_", ""))
            gui.addChoice("Choose voxel binning factor", binning_choices, binning_choices[0])
            gui.showDialog()

            if gui.wasOKed():
                xmlpath_ = gui.getNextString()
                savepath_ = gui.getNextString()
                binning_ = gui.getNextChoice()

                prefs.put(None, "xmlpath_", xmlpath_)
                prefs.put(None, "savepath_", savepath_)
                prefs.put(None, "binning_", binning_)

                data = build_mvrgetvolumes(xmlpath_, savepath_, binning_)
                run_subset_dialog(data, mode="fused")

        elif inChoice == choices[1]:
            gui = GenericDialogPlus(inChoice)
            gui.addFileField("Select xml dataset", prefs.get(None, "xmlpath_", ""))
            gui.addDirectoryField("Select save path", prefs.get(None, "savepath_", ""))
            gui.addChoice("Choose voxel binning factor", binning_choices, binning_choices[0])
            gui.addChoice("Choose view", view_choices, view_choices[0])
            gui.showDialog()

            if gui.wasOKed():
                xmlpath_ = gui.getNextString()
                savepath_ = gui.getNextString()
                binning_ = gui.getNextChoice()
                view_ = gui.getNextChoice()

                prefs.put(None, "xmlpath_", xmlpath_)
                prefs.put(None, "savepath_", savepath_)
                prefs.put(None, "binning_", binning_)
                prefs.put(None, "view_", view_)

                data = build_mvrgetvolumes(xmlpath_, savepath_, binning_)
                run_subset_dialog(data, mode="single", view_=view_)

        elif inChoice == choices[2]:
            gui = GenericDialogPlus(inChoice)
            gui.addFileField("Select xml dataset", prefs.get(None, "xmlpath_", ""))
            gui.addDirectoryField("Select save path", prefs.get(None, "savepath_", ""))
            gui.addChoice("Choose voxel binning factor", binning_choices, binning_choices[0])
            gui.showDialog()

            if gui.wasOKed():
                xmlpath_ = gui.getNextString()
                savepath_ = gui.getNextString()
                binning_ = gui.getNextChoice()

                prefs.put(None, "xmlpath_", xmlpath_)
                prefs.put(None, "savepath_", savepath_)
                prefs.put(None, "binning_", binning_)

                data = build_mvrgetvolumes(xmlpath_, savepath_, binning_)
                run_subset_dialog(data, mode="both")

        elif inChoice == choices[3]:
            gui = GenericDialogPlus(inChoice)
            gui.addDirectoryField("Select folder containing dataset xmls", prefs.get(None, "xmlfolder_", ""))
            gui.addDirectoryField("Select save path", prefs.get(None, "savepath_", ""))
            gui.addChoice("Choose voxel binning factor", binning_choices, binning_choices[0])
            gui.showDialog()

            if gui.wasOKed():
                xmlfolder_ = gui.getNextString()
                savepath_ = gui.getNextString()
                binning_ = gui.getNextChoice()

                prefs.put(None, "xmlfolder_", xmlfolder_)
                prefs.put(None, "savepath_", savepath_)
                prefs.put(None, "binning_", binning_)

                run_batch_for_all_xmls(xmlfolder_, savepath_, binning_, mode="fused")

        elif inChoice == choices[4]:
            gui = GenericDialogPlus(inChoice)
            gui.addDirectoryField("Select folder containing dataset xmls", prefs.get(None, "xmlfolder_", ""))
            gui.addDirectoryField("Select save path", prefs.get(None, "savepath_", ""))
            gui.addChoice("Choose voxel binning factor", binning_choices, binning_choices[0])
            gui.addChoice("Choose view", view_choices, view_choices[0])
            gui.showDialog()

            if gui.wasOKed():
                xmlfolder_ = gui.getNextString()
                savepath_ = gui.getNextString()
                binning_ = gui.getNextChoice()
                view_ = gui.getNextChoice()

                prefs.put(None, "xmlfolder_", xmlfolder_)
                prefs.put(None, "savepath_", savepath_)
                prefs.put(None, "binning_", binning_)
                prefs.put(None, "view_", view_)

                run_batch_for_all_xmls(xmlfolder_, savepath_, binning_, mode="single", view_=view_)

        elif inChoice == choices[5]:
            gui = GenericDialogPlus(inChoice)
            gui.addDirectoryField("Select folder containing dataset xmls", prefs.get(None, "xmlfolder_", ""))
            gui.addDirectoryField("Select save path", prefs.get(None, "savepath_", ""))
            gui.addChoice("Choose voxel binning factor", binning_choices, binning_choices[0])
            gui.showDialog()

            if gui.wasOKed():
                xmlfolder_ = gui.getNextString()
                savepath_ = gui.getNextString()
                binning_ = gui.getNextChoice()

                prefs.put(None, "xmlfolder_", xmlfolder_)
                prefs.put(None, "savepath_", savepath_)
                prefs.put(None, "binning_", binning_)

                run_batch_for_all_xmls(xmlfolder_, savepath_, binning_, mode="both")

        else:
            print 'not implemented yet'


if __name__ in ['__builtin__', '__main__']:
    main()
    IJ.log("Finished")