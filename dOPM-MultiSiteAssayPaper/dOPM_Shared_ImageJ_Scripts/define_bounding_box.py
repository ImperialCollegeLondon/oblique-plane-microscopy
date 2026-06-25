#@ PrefService prefs
from fiji.util.gui import GenericDialogPlus
from ij import IJ
import os
from os.path import isfile
from sys import path
from java.lang.System import getProperty

# code_path = 'C:/Users/CRICKOPMuser/Documents/GitHub/dOPM_Shared_ImageJ_Scripts/testing'
code_path = getProperty('fiji.dir') + '/plugins/Scripts/dOPM'

# Delete the compiled class file otherwise we can not dynamically update the imported module
ScriptPath = code_path + "/dopmmvr$py.class"
path.append(code_path)

if isfile(ScriptPath):
    os.remove(ScriptPath)

from dopmmvr import defineboundingbox


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


def find_dataset_xmls(folder):
    xmls = []
    for each in os.listdir(folder):
        if each.startswith('dataset') and each.lower().endswith('.xml'):
            full = os.path.join(folder, each)
            if os.path.isfile(full):
                xmls.append(each)
    xmls.sort()
    return xmls



def get_geometry_parameters_dialog(title):
    gui = GenericDialogPlus(title)
    gui.addNumericField("Raw Z planes / raw stack depth", prefs.getFloat(None, "rawzplanes_", 0), 0)
    gui.addNumericField("Prism angle (degrees)", prefs.getFloat(None, "prismangle_", 0), 2)
    gui.showDialog()

    if not gui.wasOKed():
        return None

    rawzplanes_ = gui.getNextNumber()
    prismangle_ = gui.getNextNumber()

    prefs.put(None, "rawzplanes_", rawzplanes_)
    prefs.put(None, "prismangle_", prismangle_)

    if rawzplanes_ <= 0:
        raise ValueError("Raw Z planes must be greater than zero for automatic geometry bounding box.")

    return rawzplanes_, prismangle_

def apply_bb_to_dataset(datapath_, dataset_, BB):
    bb_obj = defineboundingbox(dataset=dataset_)
    bb_obj.defineBoundingBoxNoInteraction(datapath_)
    bb_obj.modifyBoundingBox(datapath_, BB)
    IJ.log("Applied bounding box to: " + dataset_)


def compute_geometry_bb(datapath_, dataset_, rawzplanes_, prismangle_):
    bb_obj = defineboundingbox(dataset=dataset_, rawzplanes=rawzplanes_, prismangle=prismangle_)
    BB = bb_obj.OptimalBoundingBox(datapath_)
    bb_obj.defineBoundingBoxNoInteraction(datapath_)
    bb_obj.modifyBoundingBox(datapath_, BB)
    IJ.log("Computed and applied geometry bounding box for: " + dataset_)
    return BB


def copy_existing_bb_from_reference(reference_xml_, target_xml_):
    ref_datapath_, ref_dataset_ = split_dataset_path(reference_xml_)
    target_datapath_, target_dataset_ = split_dataset_path(target_xml_)

    ref_bb_obj = defineboundingbox(dataset=ref_dataset_)
    BB = ref_bb_obj.getXMLBoundingBox(ref_datapath_)

    if BB is None:
        raise ValueError("Reference XML does not contain 'My Bounding Box': " + reference_xml_)

    apply_bb_to_dataset(target_datapath_, target_dataset_, BB)


def define_interactively_from_reference(reference_xml_, target_xml_):
    ref_datapath_, ref_dataset_ = split_dataset_path(reference_xml_)
    target_datapath_, target_dataset_ = split_dataset_path(target_xml_)

    ref_bb_obj = defineboundingbox(dataset=ref_dataset_)
    ref_bb_obj.defineBoundingBox(ref_datapath_)
    BB = ref_bb_obj.getXMLBoundingBox(ref_datapath_)

    if BB is None:
        raise ValueError("Interactive bounding box was not found in reference XML: " + reference_xml_)

    apply_bb_to_dataset(target_datapath_, target_dataset_, BB)


def compute_geometry_from_reference_and_apply(reference_xml_, target_xml_, rawzplanes_, prismangle_):
    ref_datapath_, ref_dataset_ = split_dataset_path(reference_xml_)
    target_datapath_, target_dataset_ = split_dataset_path(target_xml_)

    ref_bb_obj = defineboundingbox(dataset=ref_dataset_, rawzplanes=rawzplanes_, prismangle=prismangle_)
    BB = ref_bb_obj.OptimalBoundingBox(ref_datapath_)
    ref_bb_obj.defineBoundingBoxNoInteraction(ref_datapath_)
    ref_bb_obj.modifyBoundingBox(ref_datapath_, BB)

    apply_bb_to_dataset(target_datapath_, target_dataset_, BB)


def batch_apply_existing_bb(reference_xml_, target_folder_):
    ref_datapath_, ref_dataset_ = split_dataset_path(reference_xml_)

    ref_bb_obj = defineboundingbox(dataset=ref_dataset_)
    BB = ref_bb_obj.getXMLBoundingBox(ref_datapath_)

    if BB is None:
        raise ValueError("Reference XML does not contain 'My Bounding Box': " + reference_xml_)

    target_xmls = find_dataset_xmls(target_folder_)
    if len(target_xmls) == 0:
        raise ValueError("No dataset XML files found in folder: " + target_folder_)

    IJ.log("Applying existing bounding box from reference XML to:")
    IJ.log(", ".join(target_xmls))

    for dataset_ in target_xmls:
        apply_bb_to_dataset(target_folder_, dataset_, BB)


def batch_define_interactively_from_reference(reference_xml_, target_folder_):
    ref_datapath_, ref_dataset_ = split_dataset_path(reference_xml_)

    ref_bb_obj = defineboundingbox(dataset=ref_dataset_)
    ref_bb_obj.defineBoundingBox(ref_datapath_)
    BB = ref_bb_obj.getXMLBoundingBox(ref_datapath_)

    if BB is None:
        raise ValueError("Interactive bounding box was not found in reference XML: " + reference_xml_)

    target_xmls = find_dataset_xmls(target_folder_)
    if len(target_xmls) == 0:
        raise ValueError("No dataset XML files found in folder: " + target_folder_)

    IJ.log("Applying interactively defined bounding box to:")
    IJ.log(", ".join(target_xmls))

    for dataset_ in target_xmls:
        apply_bb_to_dataset(target_folder_, dataset_, BB)


def batch_geometry_from_reference(reference_xml_, target_folder_, rawzplanes_, prismangle_):
    ref_datapath_, ref_dataset_ = split_dataset_path(reference_xml_)

    ref_bb_obj = defineboundingbox(dataset=ref_dataset_, rawzplanes=rawzplanes_, prismangle=prismangle_)
    BB = ref_bb_obj.OptimalBoundingBox(ref_datapath_)
    ref_bb_obj.defineBoundingBoxNoInteraction(ref_datapath_)
    ref_bb_obj.modifyBoundingBox(ref_datapath_, BB)

    target_xmls = find_dataset_xmls(target_folder_)
    if len(target_xmls) == 0:
        raise ValueError("No dataset XML files found in folder: " + target_folder_)

    IJ.log("Applying geometry-derived bounding box from reference XML to:")
    IJ.log(", ".join(target_xmls))

    for dataset_ in target_xmls:
        apply_bb_to_dataset(target_folder_, dataset_, BB)


def batch_geometry_per_xml(target_folder_, rawzplanes_, prismangle_):
    target_xmls = find_dataset_xmls(target_folder_)
    if len(target_xmls) == 0:
        raise ValueError("No dataset XML files found in folder: " + target_folder_)

    IJ.log("Computing geometry-derived bounding box independently for:")
    IJ.log(", ".join(target_xmls))

    for dataset_ in target_xmls:
        compute_geometry_bb(target_folder_, dataset_, rawzplanes_, prismangle_)


def main():
    mode_choices = [
        "single dataset",
        "batch apply to all xmls in folder"
    ]
    method_choices = [
        "define box",
        "use existing box",
        "automatic based dopm geometry"
    ]

    gui = GenericDialogPlus("Define bounding box for dataset")
    gui.addChoice("Mode", mode_choices, mode_choices[0])
    gui.addChoice("Method", method_choices, method_choices[0])
    gui.showDialog()

    if not gui.wasOKed():
        return

    mode_choice = gui.getNextChoice()
    method_choice = gui.getNextChoice()

    if mode_choice == mode_choices[0]:
        gui = GenericDialogPlus("Define bounding box for single dataset")
        gui.addFileField("Apply bounding box to dataset xml:", prefs.get(None, "target_xml_", ""))
        gui.addFileField("Get bounding box from reference/bead dataset xml:", prefs.get(None, "reference_xml_", ""))
        gui.showDialog()

        if gui.wasOKed():
            target_xml_ = gui.getNextString()
            reference_xml_ = gui.getNextString()

            prefs.put(None, "target_xml_", target_xml_)
            prefs.put(None, "reference_xml_", reference_xml_)

            if method_choice == method_choices[0]:
                define_interactively_from_reference(reference_xml_, target_xml_)
            elif method_choice == method_choices[1]:
                copy_existing_bb_from_reference(reference_xml_, target_xml_)
            elif method_choice == method_choices[2]:
                params = get_geometry_parameters_dialog("Automatic geometry bounding box parameters")
                if params is None:
                    return
                compute_geometry_from_reference_and_apply(reference_xml_, target_xml_, params[0], params[1])

    elif mode_choice == mode_choices[1]:
        if method_choice == method_choices[2]:
            gui = GenericDialogPlus("Batch geometry bounding box")
            gui.addDirectoryField("Folder containing target dataset xmls:", prefs.get(None, "target_folder_", ""))
            gui.addFileField("Optional reference/bead dataset xml (leave blank to compute per target xml):", prefs.get(None, "reference_xml_", ""))
            gui.showDialog()

            if gui.wasOKed():
                target_folder_ = gui.getNextString()
                reference_xml_ = gui.getNextString().strip()

                prefs.put(None, "target_folder_", target_folder_)
                prefs.put(None, "reference_xml_", reference_xml_)

                params = get_geometry_parameters_dialog("Automatic geometry bounding box parameters")
                if params is None:
                    return

                if reference_xml_:
                    batch_geometry_from_reference(reference_xml_, target_folder_, params[0], params[1])
                else:
                    batch_geometry_per_xml(target_folder_, params[0], params[1])

        else:
            gui = GenericDialogPlus("Batch copy bounding box to all xmls in folder")
            gui.addDirectoryField("Folder containing target dataset xmls:", prefs.get(None, "target_folder_", ""))
            gui.addFileField("Reference/bead dataset xml:", prefs.get(None, "reference_xml_", ""))
            gui.showDialog()

            if gui.wasOKed():
                target_folder_ = gui.getNextString()
                reference_xml_ = gui.getNextString()

                prefs.put(None, "target_folder_", target_folder_)
                prefs.put(None, "reference_xml_", reference_xml_)

                if method_choice == method_choices[0]:
                    batch_define_interactively_from_reference(reference_xml_, target_folder_)
                elif method_choice == method_choices[1]:
                    batch_apply_existing_bb(reference_xml_, target_folder_)


if __name__ in ['__builtin__', '__main__']:
    main()
    IJ.log("Finished")