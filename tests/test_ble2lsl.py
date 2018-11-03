
import ble2lsl as b2l
from ble2lsl.devices import *

import pytest

@pytest.fixture(scope='module', params=b2l.devices.DEVICE_NAMES)
def device(request):
    device = globals()[request.param]
    return device

@pytest.fixture(scope='module', params=([b2l.BaseStreamer]
                                         + b2l.BaseStreamer.__subclasses__()))
def streamer(request, device):
    streamer = request.param(device, autostart=False)
    # def teardown():
    #     try:
    #         streamer.stop()
    #     except NotImplementedError:
    #         pass
    #     del(streamer)
    # request.addfinalizer(teardown)
    return streamer

class TestBaseStreamer:
    def test_init(self, streamer, device):
        # not sure if necessary to test private variables, or just
        # the public behaviour
        assert streamer._device is device
        if streamer.__class__ is b2l.Dummy:
            defaults = [name for name in device.DEFAULT_SUBSCRIPTIONS
                        if device.PARAMS['streams']['nominal_srate'][name] > 0]
            assert set(streamer.subscriptions) == set(defaults)
        else:
            assert (set(streamer.subscriptions)
                    == set(device.DEFAULT_SUBSCRIPTIONS))
        assert streamer._stream_params is device.PARAMS['streams']


@pytest.fixture(scope='class')
def skip_wrong_class(request, streamer):
    """Skip a class of tests if `streamer` is wrong type of `BaseStreamer`.

    Define the test class attribute `TEST_CLASS` as the (non-test) class the
    tests examine.
    """
    if streamer.__class__ is not request.cls.TEST_CLASS:
        pytest.skip("{} tests skipped for {}".format(request.cls.TEST_CLASS,
                                                     streamer.__class__))

@pytest.mark.usefixtures("skip_wrong_class")
class TestStreamer:

    TEST_CLASS = b2l.Streamer

    def test_init(self, streamer, device):
        # TODO: check threads/outlets
        pass

    def test_connect(self):
        #streamer.connect()
        pass

    def test_start(self, streamer, device):
        pass#streamer.start()
        # TODO: check that correct characteristic sent through BLE

@pytest.mark.usefixtures("skip_wrong_class")
class TestDummy:

    TEST_CLASS = b2l.Dummy

    def test_init(self, streamer, device):
        pass

    def test_start(self):
        pass

    def test_stop(self):
        pass

    def test_make_chunk(self):
        pass
