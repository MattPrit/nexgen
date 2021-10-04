"""
Writer for NeXus format files.
"""

import h5py
import numpy as np

from pathlib import Path
from typing import List, Tuple, Union

from . import find_scan_axis, calculate_scan_range

# from data_tools import data_writer, find_number_of_images
from ..nxs_write.data_tools import data_writer, find_number_of_images

# from NXclassWriters import (
from ..nxs_write.NXclassWriters import (
    write_NXdata,
    write_NXinstrument,
    write_NXsample,
    write_NXsource,
    write_NXdetector,
    write_NXdetector_module,
)

# General writing
def write_NXmx_nexus(
    nxsfile: h5py.File,
    datafiles: List[Path],
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
    timestamps: tuple,
    coordinate_frame: str = "mcstas",
    vds: str = None,
):
    """
    Write a new NeXus file.

    This function writes a new nexus file from the information contained in the phil scopes passed as input.
    External links to HDF5 data files.

    Args:
        nxsfile:            NeXus file to be written.
        datafiles:          List of at least 1 Path object to a HDF5 data file.
        goniometer:         Scope extract
        detector:           Scope extract
        module:             Scope extract
        source:             Scope extract
        beam:               Scope extract
        attenuator:         Scope extract
        timestamps:         (start, end) tuple containing timestamps for start and end time.
        coordinate_frame:   String indicating which coordinate system is being used.
        vds:                If passed, a Virtual Dataset will also be written.
    """
    # Find total number of images that have been written across the files.
    if len(datafiles) == 1:
        with h5py.File(datafiles[0], "r") as f:
            num_images = f["data"].shape[0]
    else:
        num_images = find_number_of_images(datafiles)

    data_type = ("images", num_images)

    # Identify scan axis
    osc_axis = find_scan_axis(goniometer.axes, goniometer.starts, goniometer.ends)

    # Compute scan_range
    idx = goniometer.axes.index(osc_axis)
    if goniometer.increments[idx] != 0.0:
        scan_range = calculate_scan_range(
            goniometer.starts[idx],
            goniometer.ends[idx],
            axis_increment=goniometer.increments[idx],
        )
    else:
        scan_range = calculate_scan_range(
            goniometer.starts[idx], goniometer.ends[idx], n_images=num_images
        )

    # Set default attribute
    nxsfile.attrs["default"] = "entry"

    # Start writing the NeXus tree with NXentry at the top level
    nxentry = nxsfile.create_group("entry")
    nxentry.attrs["NX_class"] = np.string_("NXentry")
    nxentry.attrs["default"] = np.string_("data")
    # create_attributes(nxentry, ("NX_class", "default"), ("NXentry", "data"))

    # Application definition: /entry/definition
    nxentry.create_dataset("definition", data=np.string_("NXmx"))

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        osc_axis,
        scan_range,
        data_type,
        goniometer,
        detector,
        module,
        source,
        beam,
        attenuator,
        vds,
    )

    # NX_DATE_TIME: /entry/start_time and /entry/end_time
    if timestamps[0] is not None:
        nxentry.create_dataset("start_time", data=np.string_(timestamps[0]))
    if timestamps[1] is not None:
        nxentry.create_dataset("end_time", data=np.string_(timestamps[1]))


def write_nexus_demo(
    nxsfile: h5py.File,
    datafiles: List[Path],
    data_type: Tuple[str, int],
    coordinate_frame: str,
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
    vds: str = None,
):
    """
    Write a new example NeXus format file with blank data.

    This function writes a new nexus file from the information contained in the phil scopes passed as input.
    It also writes a specified number of blank data HDF5 files.
    The nuber of these files can be passed as input parameter, if it isn't it defaults to 1.

    Args:
        nxsfile:            NeXus file to be written.
        datafiles:          List of at least 1 Path object to a HDF5 data file.
        data_type:          Tuple (str, int) indicating whether the mode is images or events (and eventually how many).
        coordinate_frame:   String indicating which coordinate system is being used.
        goniometer:         Scope extract
        detector:           Scope extract
        module:             Scope extract
        source:             Scope extract
        beam:               Scope extract
        attenuator:         Scope extract
        vds:                If passed, a Virtual Dataset will also be written.
    """
    # Identify scan axis
    osc_axis = find_scan_axis(goniometer.axes, goniometer.starts, goniometer.ends)

    # Compute scan_range
    idx = goniometer.axes.index(osc_axis)
    if data_type[0] == "images":
        if data_type[1] is None:
            scan_range = calculate_scan_range(
                goniometer.starts[idx],
                goniometer.ends[idx],
                axis_increment=goniometer.increments[idx],
            )
            data_type = ("images", len(scan_range))
        else:
            scan_range = calculate_scan_range(
                goniometer.starts[idx], goniometer.ends[idx], n_images=data_type[1]
            )
    elif data_type[0] == "events":
        scan_range = (goniometer.starts[idx], goniometer.ends[idx])

    # Write data files
    data_writer(
        datafiles,
        data_type,
        image_size=detector.image_size,
        scan_range=scan_range,
    )

    # Call the writers
    call_writers(
        nxsfile,
        datafiles,
        coordinate_frame,
        osc_axis,
        scan_range,
        data_type,
        goniometer,
        detector,
        module,
        source,
        beam,
        attenuator,
        vds,
    )


def call_writers(
    nxsfile: h5py.File,
    datafiles: List[Path],
    coordinate_frame: str,
    scan_axis: str,
    scan_range: Union[Tuple, np.ndarray],
    data_type: Tuple[str, int],
    goniometer,
    detector,
    module,
    source,
    beam,
    attenuator,
    vds: str,
):
    """ Call the writers for the NeXus base classes."""
    # NXdata: entry/data
    write_NXdata(
        nxsfile,
        datafiles,
        goniometer.__dict__,
        data_type[0],
        coordinate_frame,
        scan_range,
        scan_axis,
        vds,
    )

    # NXinstrument: entry/instrument
    write_NXinstrument(
        nxsfile,
        beam.__dict__,
        attenuator.__dict__,
        source.beamline_name,
    )

    # NXdetector: entry/instrument/detector
    write_NXdetector(nxsfile, detector.__dict__, coordinate_frame, data_type)

    # NXmodule: entry/instrument/detector/module
    write_NXdetector_module(
        nxsfile,
        module.__dict__,
        coordinate_frame,
        detector.image_size,
        detector.pixel_size,
        beam_center=detector.beam_center,
    )

    # NXsource: entry/source
    write_NXsource(nxsfile, source.__dict__)

    # NXsample: entry/sample
    write_NXsample(
        nxsfile,
        goniometer.__dict__,
        coordinate_frame,
        data_type[0],
        scan_axis,
        scan_range,
    )
