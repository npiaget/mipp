#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Adam.Dybbroe

# Author(s):

#   Adam.Dybbroe <a000680@c14526.ad.smhi.se>
#

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""A reader for the native format MSG data
"""

import mipp.cfg
from glob import glob
import os.path
from datetime import datetime, timedelta
import numpy as np
from mipp.header_records import (
    Msg15NativeHeaderRecord, GSDTRecords)

import mipp.xrit.MSG


class ChannelData(object):

    def __init__(self, data, mda, name):

        self.header = mda
        self.channel_name = name
        self.calibrator = mipp.xrit.MSG._Calibrator(
            self.header, self.channel_name)
        self.data, self.unit = data, 'counts'

    def calibrate(self, calswitch):
        """calibrate the data"""
        print("Calibrate... ")
        self.data, self.unit = self.calibrator(self.data, calibrate=calswitch)

    def show(self):
        """Show an image of the data"""
        import matplotlib.pyplot as plt
        plt.imshow(self.data)
        plt.show()


class NativeImage(object):

    """Handling the MSG Native data format"""

    def __init__(self, satname, time_slot=None, filename=None, calibflag=1):
        """Intialise the object, setting the time slot and finding the filename
        (if not given) and reading the header data
        """
        self.calibflag = calibflag
        self.units = {}
        self.satname = satname
        self.channel_name_mapping = None
        self.channel_numbers = []
        self._config_reader = mipp.cfg.read_config(satname)
        self.channel_name_mapping = self._config_reader.channels
        self.channel_names = self.channel_name_mapping.keys()
        # Make the list of channel numbers:
        self.channel_numbers = []
        for name in self.channel_names:
            self.channel_numbers.append(
                self.channel_name_mapping[name].channel_number)

        self.header = None
        self.pk_head = None
        self._umarf = None
        self._pk_head_dtype = None
        self._cols_visir = None
        self._cols_hrv = None
        self.data_len = None

        self.area_extent = None

        if time_slot:
            self.time_slot = time_slot
            self.filename = self.get_filename()
        elif filename:
            self.filename = filename
            self.time_slot = None
        else:
            raise IOError("Either filename or time slot needed as input!")

        self.get_header()
        if not self.time_slot:
            self.time_slot = self.header['15_DATA_HEADER']['SatelliteStatus'][
                'UTCCorrelation']['PeriodStartTime']

        self.memmap = self.load()  # Pointer to the data

        for name in self.channel_names:
            self.add_property(name.lower())

    def _get_unitnames(self):
        """Get the present unit names for each channel"""
        pass

    def get_header(self):
        """Read the header info"""

        hdrrec = Msg15NativeHeaderRecord().get()
        hd_dt = np.dtype(hdrrec)
        hd_dt = hd_dt.newbyteorder('>')
        self.header = np.fromfile(self.filename, dtype=hd_dt, count=1)

        pkhrec = [
            ('GP_PK_HEADER', GSDTRecords().gp_pk_header),
            ('GP_PK_SH1', GSDTRecords().gp_pk_sh1)
        ]
        pkht = np.dtype(pkhrec)
        self._pk_head_dtype = pkht.newbyteorder('>')

        sec15hd = self.header['15_SECONDARY_PRODUCT_HEADER']
        numlines_visir = int(sec15hd['NumberLinesVISIR']['Value'][0])
        west = int(sec15hd['WestColumnSelectedRectangle']['Value'][0])
        east = int(sec15hd['EastColumnSelectedRectangle']['Value'][0])
        north = int(sec15hd["NorthLineSelectedRectangle"]['Value'][0])
        south = int(sec15hd["SouthLineSelectedRectangle"]['Value'][0])
        numcols_hrv = int(sec15hd["NumberColumnsHRV"]['Value'][0])

        self._cols_visir = np.ceil(numlines_visir * 5.0 / 4)  # 4640
        if (west - east) < 3711:
            self._cols_hrv = np.ceil(numcols_hrv * 5.0 / 4)  # 6960
        else:
            self._cols_hrv = np.ceil(5568 * 5.0 / 4)  # 6960
        #'WestColumnSelectedRectangle' - 'EastColumnSelectedRectangle'
        #'NorthLineSelectedRectangle' - 'SouthLineSelectedRectangle'

        coldir_step = self.header['15_DATA_HEADER']['ImageDescription'][
            "ReferenceGridVIS_IR"]["ColumnDirGridStep"]
        lindir_step = self.header['15_DATA_HEADER']['ImageDescription'][
            "ReferenceGridVIS_IR"]["LineDirGridStep"]
        area_extent = ((1856 - west - 0.5) * coldir_step,
                       (1856 - north + 0.5) * lindir_step,
                       (1856 - east + 0.5) * coldir_step,
                       (1856 - south + 1.5) * lindir_step)

        self.area_extent = area_extent

        self.data_len = numlines_visir

    def load(self):
        """Open the file and generate a memory map of the data using numpy memmap"""

        with open(self.filename) as fp_:

            # fp_.seek(450400)

            linetype = np.dtype([("visir", [("gp_pk", self._pk_head_dtype),
                                            ("version", ">u1"),
                                            ("satid", ">u2"),
                                            ("time", ">u2", (5, )),
                                            ("lineno", ">u4"),
                                            ("chan_id", ">u1"),
                                            ("acq_time", ">u2", (3, )),
                                            ("line_validity", ">u1"),
                                            ("line_rquality", ">u1"),
                                            ("line_gquality", ">u1"),
                                            ("line_data", ">u1", (self._cols_visir, ))],
                                  (11, )),
                                 ("hrv",  [("gp_pk", self._pk_head_dtype),
                                           ("version", ">u1"),
                                           ("satid", ">u2"),
                                           ("time", ">u2", (5, )),
                                           ("lineno", ">u4"),
                                           ("chan_id", ">u1"),
                                           ("acq_time", ">u2", (3, )),
                                           ("line_validity", ">u1"),
                                           ("line_rquality", ">u1"),
                                           ("line_gquality", ">u1"),
                                           ("line_data", ">u1", (self._cols_hrv, ))],
                                  (3, ))])

            # read everything in memory
            #res = np.fromfile(fp_, dtype=linetype, count=data_len)

            # lazy reading
            return np.memmap(
                fp_, dtype=linetype, shape=(self.data_len, ), offset=450400, mode="r")

    def read_channel(self, channel_index):
        """Read the actual channel into memory"""

        if channel_index < 11:
            return self._dec10to16(
                self.memmap["visir"]["line_data"][:, channel_index, :])[::-1, ::-1]
        else:
            data0 = self._dec10to16(
                self.memmap["hrv"]["line_data"][:, 0, :])[::-1, ::-1]
            data1 = self._dec10to16(
                self.memmap["hrv"]["line_data"][:, 1, :])[::-1, ::-1]
            data2 = self._dec10to16(
                self.memmap["hrv"]["line_data"][:, 2, :])[::-1, ::-1]
            # Make empty array:
            shape = data0.shape[0] * 3, data0.shape[1]
            data = np.zeros(shape)
            idx = range(0, shape[0], 3)
            data[idx, :] = data0
            idx = range(1, shape[0], 3)
            data[idx, :] = data1
            idx = range(2, shape[0], 3)
            data[idx, :] = data2
            return data

    def _dec10to16(self, data):
        """Unpacking the 10 bit data to 16 bit"""

        arr10 = data.astype(np.uint16).flat
        new_shape = list(data.shape[:-1]) + [(data.shape[-1] * 8) / 10]
        arr16 = np.zeros(new_shape, dtype=np.uint16)
        arr16.flat[::4] = np.left_shift(arr10[::5], 2) + \
            np.right_shift((arr10[1::5]), 6)
        arr16.flat[1::4] = np.left_shift((arr10[1::5] & 63), 4) + \
            np.right_shift((arr10[2::5]), 4)
        arr16.flat[2::4] = np.left_shift(arr10[2::5] & 15, 6) + \
            np.right_shift((arr10[3::5]), 2)
        arr16.flat[3::4] = np.left_shift(arr10[3::5] & 3, 8) + \
            arr10[4::5]
        return arr16

    def __str__(self):

        retv = [name.lower() for name in self.channel_names]
        return ' '.join(retv)

    def add_property(self, prop):
        fget = lambda self: self._get_property(prop)
        setattr(self.__class__, prop, property(fget))

    def _get_property(self, prop):
        attr = '_{0}'.format(prop)
        # When accessing the attribute the data is fetched, and calibrated as
        # specified using the self.calibflag:
        chidx = self.channel_name_mapping[prop.upper()].channel_number - 1
        chname = self.channel_name_mapping[prop.upper()].name
        tmpch = ChannelData(self.read_channel(chidx), self.header, chname)
        if self.calibflag > 0:
            chname = self.channel_name_mapping[prop.upper()].name
            tmpch.calibrate(self.calibflag)

        return tmpch

    def get_filename(self):
        """Get the file name (incl path) given the satellite and the time slot"""

        opt = self._config_reader('level1')

        # Find the file name valid for the time slot:
        path = opt['dir']

        new_tstamp = datetime(self.time_slot.year,
                              self.time_slot.month,
                              self.time_slot.day,
                              self.time_slot.hour)
        ftmpl = new_tstamp.strftime(opt['filename'])
        flist = glob(os.path.join(path, ftmpl))

        files_and_times = [(fname, os.path.basename(fname).split(
            '.')[0].split('-')[-1]) for fname in flist]
        files_and_dtobjs = [(fname, datetime.strptime(tstring, '%Y%m%d%H%M%S'))
                            for (fname, tstring) in files_and_times]
        # Find the closest time to the quarter
        dtobj = None
        for dtobj in files_and_dtobjs:
            if (self.time_slot - (dtobj[1] - timedelta(minutes=15))) < timedelta(minutes=15):
                break
        if dtobj:
            return os.path.join(path, dtobj[0])
