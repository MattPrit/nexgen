"""
Tools to check and eventually fix NeXus files for Tristan LATRD detector on I19-2 beamline at DLS.
"""

import h5py
import logging

import numpy as np

# Define logger
logger = logging.getLogger("TristanNXSChecks")


def check_definition(nxsfile: h5py.File):
    """
    Checks and eventually fixes that the definition is set to "NXmx"
    """
    definition = nxsfile["entry/definition"][()]
    logger.info(f"Application definition: {definition}")
    if definition != "NXmx":
        del nxsfile["entry/definition"]
        nxsfile["entry"].create_dataset("definition", data="NXmx")
        logger.info("Fixing definition to NXmx")
    logger.info("")


def check_detector_transformations(nxtransf: h5py.Group):
    """
    Checks and eventually fixes the values of detector_z and two_theta fields and their attributes.
    """
    logger.info(
        "On I19-2 the Tristan detector does not sit on two_theta arm, which must be set to 0."
    )
    try:
        ds_name = "two_theta"
        two_theta = nxtransf["two_theta"]
    except KeyError:
        # For older versions of Tristan nexus file
        ds_name = "twotheta"
        two_theta = nxtransf["twotheta"]
    if two_theta[ds_name][()] != 0:
        logger.info("Correcting the value of two_theta arm ...")
        d = {}
        for k in two_theta[ds_name].attrs.keys():
            d[k] = two_theta[ds_name].attrs[k]
        del two_theta[ds_name]
        tt = two_theta.create_dataset(ds_name, data=[(0.0)])
        for k, v in d.items():
            tt.attrs[k] = v
        del d

    logger.info("Additionally, the detector_z vector should be [0,0,-1]")
    det_z = nxtransf["detector_z/det_z"]
    if np.any(det_z.attrs["vector"] != [0, 0, -1]):
        logger.info("Overwriting det_z vector ...")
        det_z.attrs["vector"] = [0, 0, -1]

    logger.info("Checking dependency tree of detector for typos ...")
    if two_theta[ds_name].attrs["depends_on"] != b".":
        logger.info("Setting two_theta as base ...")
        two_theta[ds_name].attrs["depends_on"] = np.string_(".")
    if (
        det_z.attrs["depends_on"]
        != b"/entry/instrument/detector/transformations/two_theta/two_theta"
    ):
        logger.info("Fixing typo in det_z dependency ...")
        det_z.attrs["depends_on"] == np.string_(
            "/entry/instrument/detector/transformations/two_theta/two_theta"
        )


def check_sample_depends_on(nxsample: h5py.Group):
    """
    Check that the sample depends_on field exists and is correct.
    For I19-2 Tristan it should be "/entry/sample/transformations/phi"
    """
    try:
        dep = nxsample["depends_on"][()]
        if dep != b"/entry/sample/transformations/phi":
            logger.info("Fixing sample depends_on field ...")
            del nxsample["depends_on"]
            nxsample.create_dataset(
                "depends_on", data=np.string_("/entry/sample/transformations/phi")
            )
    except KeyError:
        logger.info("Sample depends_on field did not exist, creating now ...")
        nxsample.create_dataset(
            "depends_on", data=np.string_("/entry/sample/transformations/phi")
        )


def check_I19_dependency_tree(nxtransf: h5py.Group):
    """
    Check and fix that the dependency tree in "entry/sample/transformations" is consistent with I19-2.
    """
    # FIXME Quick hard coded way, works for now but needs to be generalized.
    logger.info("The dependency tree on I19-2 should follow this order:")
    logger.info("x - y - z - phi - kappa - omega")
    if nxtransf["omega"].attrs["depends_on"] != b".":
        nxtransf["omega"].attrs["depends_on"] = np.string_(".")
    if nxtransf["kappa"].attrs["depends_on"] != b"/entry/sample/transformations/omega":
        nxtransf["kappa"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/omega"
        )
    if nxtransf["phi"].attrs["depends_on"] != b"/entry/sample/transformations/kappa":
        nxtransf["phi"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/kappa"
        )
    if nxtransf["sam_x"].attrs["depends_on"] != b"/entry/sample/transformations/sam_y":
        nxtransf["sam_x"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/sam_y"
        )
    if nxtransf["sam_y"].attrs["depends_on"] != b"/entry/sample/transformations/sam_z":
        nxtransf["sam_y"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/sam_z"
        )
    if nxtransf["sam_z"].attrs["depends_on"] != b"/entry/sample/transformations/phi":
        nxtransf["sam_z"].attrs["depends_on"] = np.string_(
            "/entry/sample/transformations/phi"
        )


def run_checks(tristan_nexus_file):
    """
    Instigates the functions to check nexus files generated after binning of Tristan data.
    """
    wdir = tristan_nexus_file.parent
    logfile = wdir / "NeXusChecks.log"  # widr is a PosixPath
    logging.basicConfig(
        filename=logfile, format="%(message)s", level="DEBUG", filemode="w"
    )
    logger.info(f"Running checks on {tristan_nexus_file} ...")

    with h5py.File(tristan_nexus_file, "r+") as nxsfile:
        logger.info("Check application definition")
        check_definition(nxsfile)
        logger.info("-" * 10)
        logger.info(
            "Check that detector_z and two_theta fields are correctly set to I19-2 configuration for Tristan."
        )
        try:
            # According to NXmx Gold Standard
            check_detector_transformations(
                nxsfile["entry/instrument/detector/transformations"]
            )
        except KeyError:
            # For earlier versions of the Tristan nexus file (before June 2021):
            # NXtransformations group was placed under NXinstrument group
            check_detector_transformations(nxsfile["entry/instrument/transformations"])
        logger.info("-" * 10)
        logger.info("Check sample depends on")
        check_sample_depends_on(nxsfile["entry/sample"])
        logger.info("-" * 10)
        logger.info("Check goniometer dependency tree")
        check_I19_dependency_tree(nxsfile["entry/sample/transformations"])
        logger.info("EOF")