import ble2lsl, utils
import muse2016
from wizardhat import acquire, plot

a = ble2lsl.Replay(muse2016, DATA_PATH) # Put the data path here
receiver = acquire.Receiver()
plot.Lines(receiver.buffers["EEG"])
