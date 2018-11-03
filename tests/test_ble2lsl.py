
import ble2lsl as b2l
from ble2lsl.devices import *

import pytest


@pytest.fixture(scope='module', params=b2l.devices.DEVICE_NAMES)
def device(request):
    device = globals()[request.param]
    return device

@pytest.fixture(scope='module')
def base_streamer(request, device):
    base_streamer = b2l.BaseStreamer(device)
    def teardown():
        try:
            # in case `BaseStreamer` has been promoted or something
            base_streamer.stop()
        except NotImplementedError:
            pass
        del(base_streamer)
    request.addfinalizer(teardown)
    return base_streamer

class TestBaseStreamer:
    def test_init(self, base_streamer, device):
        streamer = base_streamer
        # not sure if necessary to test private variables, or just
        # the public behaviour
        assert streamer._device is device
        assert streamer._subscriptions == tuple(device.DEFAULT_SUBSCRIPTIONS)
        assert streamer._stream_params is device.PARAMS['streams']
