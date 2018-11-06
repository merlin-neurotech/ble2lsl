
import ble2lsl as b2l
from ble2lsl.devices import *

import time

import pytest

@pytest.fixture(scope='module', params=b2l.devices.DEVICE_NAMES)
def device(request):
    """Test all compatible devices."""
    device = globals()[request.param]
    return device

@pytest.fixture(scope='module', params=([b2l.BaseStreamer]
                                         + b2l.BaseStreamer.__subclasses__()))
def streamer(request, device):
    """Test `BaseStreamer` and all its subclasses."""
    streamer = request.param(device, autostart=False)

    # TODO: user ch_names

    # not sure why this doesn't work
    # (thinks streamer doesn't exist, UnboundLocalError)
    # def teardown():
    #     try:
    #         streamer.stop()
    #     except NotImplementedError:
    #         pass
    #     del(streamer)
    # request.addfinalizer(teardown)
    return streamer

@pytest.fixture(scope='module')
def subscriptions(device):
    subscriptions = [name for name in device.DEFAULT_SUBSCRIPTIONS
                     if device.PARAMS['streams']['nominal_srate'][name] > 0]
    return set(subscriptions)

def test_empty_chunks(device, subscriptions):
    chunks = b2l.empty_chunks(device.PARAMS['streams'], subscriptions)
    assert set(chunks.keys()) == subscriptions
    for name in subscriptions:
        # empty?
        assert not np.any(chunks[name])
        # right shape?
        assert (chunks[name].shape[0]
                == device.PARAMS['streams']['chunk_size'][name])
        assert (chunks[name].shape[1]
                == device.PARAMS['streams']['channel_count'][name])
        # right dtype?
        assert (chunks[name].dtype
                is device.PARAMS['streams']['numpy_dtype'][name])


def test_get_default_subscriptions(device, subscriptions):
    assert (set(b2l.get_default_subscriptions(device, pos_rate=True))
            == subscriptions)
    try:
        assert (set(b2l.get_default_subscriptions(device, pos_rate=False))
                == device.DEFAULT_SUBSCRIPTIONS)
    except AttributeError:
        assert (set(b2l.get_default_subscriptions(device, pos_rate=False))
                == device.STREAMS)


class TestBaseStreamer:
    def test_init(self, streamer, device, subscriptions):
        # not sure if necessary to test private variables, or just
        # the public behaviour
        assert streamer._device is device
        if streamer.__class__ is b2l.Dummy:
            assert set(streamer.subscriptions) == subscriptions
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
        assert streamer._address == "DUMMY"

    def test_start(self, streamer):
        for name, thread in streamer._threads.items():
            assert not thread.is_alive()
        streamer.start()
        for name, thread in streamer._threads.items():
            assert thread.is_alive()

    def test_stop(self):
        for name, thread in streamer._threads.items():
            assert thread.is_alive()
        streamer.stop()
        time.sleep(1.5)
        #for name, thread in streamer._threads.items():
        #    assert not thread.is_alive()

    def test_make_chunk(self):
        pass

class TestNoisySinusoids:
    pass
