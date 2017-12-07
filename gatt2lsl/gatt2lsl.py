# -*- coding: utf-8 -*-
"""Setup streaming of GATT data through LSL.


"""

import time

import bitstring
import numpy as np
import pygatt
import pylsl as lsl


MUSE_PARAMS = dict(
    manufacturer='Muse',
    units='microvolts',
    ch_names=('TP9', 'AF7', 'AF8', 'TP10', 'Right AUX'),
    ch_uuids=(
        '273e0003-4c4d-454d-96be-f03bac821358',
        '273e0004-4c4d-454d-96be-f03bac821358',
        '273e0005-4c4d-454d-96be-f03bac821358',
        '273e0006-4c4d-454d-96be-f03bac821358',
        '273e0007-4c4d-454d-96be-f03bac821358',
    ),
    packet_dtypes=dict(index='uint:16', ch_value='uint:12'),
)
"""General Muse headset parameters."""


MUSE_STREAM_PARAMS = dict(
    name='Muse',
    type='EEG',
    channel_count=5,
    nominal_srate=256,
    channel_format='float32',
)
"""Muse headset parameters for constructing `pylsl.StreamInfo`."""


class LSLOutletStreamer():

    def __init__(self, device_params=None, stream_params=None, interface=None,
                 address=None, backend='bgapi', autostart=True, chunk_size=12,
                 time_func=time.time):
        if device_params is None:
            device_params = MUSE_PARAMS
        if stream_params is None:
            stream_params = MUSE_STREAM_PARAMS
        if address is None:
            address = self.__get_device_address(stream_params["name"])

        self.device_params = device_params
        self.chunk_size = chunk_size
        self.interface = interface
        self.address = address
        self.time_func = time_func

        # initialize gatt adapter
        if backend == 'gatt':
            self.interface = self.interface or 'hci0'
            self.adapter = pygatt.GATTToolBackend(self.interface)
        elif backend == 'bgapi':
            self.adapter = pygatt.BGAPIBackend(serial_port=self.interface)
        else:
            raise(ValueError("Invalid backend specified; use bgapi or gatt."))
        self.backend = backend

        # construct LSL StreamInfo and StreamOutlet
        self.__init_stream_info(stream_params)
        self.outlet = lsl.StreamOutlet(self.info, chunk_size=chunk_size,
                                       max_buffered=360)
        self.__set_packet_format()

        if autostart:
            self.connect()
            self.start()

    def connect(self):
        self.adapter.start()
        try:
            self.device = self.adapter.connect(self.address)
        except pygatt.exceptions.NotConnectedError:
            e_msg = "Unable to connect to device at address {}" \
                    .format(self.address)
            raise(IOError(e_msg))

        for uuid in self.device_params["ch_uuids"]:
            self.device.subscribe(uuid, callback=self.__transmit_sample)

    def start(self):
        self.sample_index = 0
        self.start_time = self.time_func()
        self.__init_sample()
        self.last_tm = 0
        self.device.char_write_handle(0x000e, [0x02, 0x64, 0x0a], False)

    def stop(self):
        self.device.char_write_handle(0x000e, [0x02, 0x68, 0x0a], False)

    def disconnect(self):
        self.device.disconnect()
        self.adapter.stop()

    def __get_device_address(self, name):
        list_devices = self.adapter.scan(timeout=10.5)
        for device in list_devices:
            if device['name'] == name:
                return device['address']
        raise(ValueError("No devices found with name `{}`".format(name)))

    def __init_stream_info(self, stream_params):
        self.info = lsl.StreamInfo(**stream_params, source_id="MuseNone")
        self.info.desc().append_child_value("manufacturer",
                                            self.device_params["manufacturer"])
        self.channels = self.info.desc().append_child("channels")
        for ch_name in self.device_params["ch_names"]:
            self.channels.append_child("channel") \
                .append_child_value("label", ch_name) \
                .append_child_value("unit", self.device_params["units"]) \
                .append_child_value("type", stream_params["type"])

    def __set_packet_format(self):
        dtypes = self.device_params["packet_dtypes"]
        n_chan = self.info.channel_count()
        self.packet_format = dtypes["index"] + \
                             (',' + dtypes["ch_value"]) * n_chan

    def __transmit_packet(self, handle, data):
        """TODO: Move bit locations to Muse parameters."""
        timestamp = self.time_func()
        index = int((handle - 32) / 3)
        tm, d = self.__unpack_channel(data)

        if self.last_tm == 0:
            self.last_tm = tm - 1

        self.data[index] = d
        self.timestamps[index] = timestamp

        # if last channel in chunk
        if handle == 35:
            if tm != self.last_tm + 1:
                print("Missing sample {} : {}".format(tm, self.last_tm))
            self.last_tm = tm

            # sample indices
            sample_indices = np.arange(self.chunk_size) + self.sample_index
            self.sample_index += self.chunk_size

            timestamps = sample_indices / self.info.nominal_srate() \
                         + self.start_time

            self.__push_chunk(self.data, timestamps)
            self.__init_sample()

    def __unpack_channel(self, packet):
        packet_bits = bitstring.Bits(bytes=packet)
        unpacked = packet_bits.unpack(self.packet_format)
        packet_index = unpacked[0]
        packet_values = np.array(unpacked[1:])
        packet_values = 0.48828125 * (packet_values - 2048)

        return packet_index, packet_values

    def __init_sample(self):
        self.timestamps = np.zeros(self.info.channel_count())
        self.data = np.zeros((self.info.channel_count(), self.chunk_size))

    def __push_chunk(self, channels, timestamps):
        for sample in range(self.chunk_size):
            self.outlet.push_sample(channels[:, sample], timestamps[sample])