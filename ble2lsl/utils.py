"""Utilities for use within ble2lsl."""

from warnings import warn


def subdicts_to_attrdicts(dict_):
    for key in dict_:
        try:
            dict_[key].keys()
            dict_[key] = AttrDict(dict_[key])
            dicts_to_attrdicts(dict_[key])
        except AttributeError:
            pass


class AttrDict(dict):
    """Dictionary whose keys can be referenced like attributes."""
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    def __init__(self, *args, **kwargs):
        subdicts_to_attrdicts(kwargs)
        super().__init__(*args, **kwargs)


def invert_map(dict_):
    """Invert the keys and values in a dict."""
    inverted = {v: k for k, v in dict_.items()}
    return inverted


def bad_data_size(data, size, data_type="packet"):
    """Return `True` if length of `data` is not `size`."""
    if len(data) != size:
        warn('Wrong size for {}, {} instead of {} bytes'
             .format(data_type, len(data), size))
        return True
    return False


def dict_partial_from_keys(keys):
    """Return a function that constructs a dictionary with predetermined keys.
    """
    def dict_partial(values):
        return dict(zip(keys, values))
    return dict_partial


class file_read:
    #the parent class for CSV_read and JSON_read
    __slots__ = ("_path", "_filename", "_stream_type")

    def __init__(self, path, filename, stream_type):
        self._path = self._path_check(path)
        self._filename = self._filename_check(filename)
        self._stream_type = self._stream_type_check(stream_type)

    @property
    def path(self):
        return self._path

    @property
    def filename(self):
        return self._filename

    @property
    def stream_type(self):
        return self._stream_type

    @staticmethod
    def _path_check(p):
        #to check if path is valid
        tmp_p = Path(p)
        if tmp_p.exists():
            if tmp_p.is_dir() and tmp_p.is_absolute(): #use absolute path
                return str(tmp_p)
            elif tmp_p.is_dir() and not tmp_p.is_absolute():
                return str(tmp_p.resolve(strict=True))
            else:
                raise ValueError("Path needs to be a folder")
        else:
            raise ValueError("Path does not exist")

    def _filename_check(self, f):
        #name check, see if the name matches the required format
        pattern = re.compile(r"\d{6}-\d{6}_.+\d\.(csv|json)$", re.I)
        if not isinstance(f, str):
            raise TypeError("Invalid filename")
        fname = pattern.match(f)
        if fname == None:
            raise ValueError("Filename does not match required pattern")
        fname = fname.group()
        if fname != f:
            raise ValueError("Filename does not match required pattern")
        if not fname.lower().endswith((".csv", ".json")):
            raise ValueError("Only CSV and JSON files can be valid input")
        if not (Path(self._path) / fname).is_file():
            raise ValueError("File does not exist")
        if isinstance(self, CSV_read) and not fname.lower().endswith(".csv"):
            raise TypeError("Not a CSV file")
        if isinstance(self, JSON_read) and not fname.lower().endswith(".json"):
            raise TypeError("Not a JSON file")
        return fname

    def _stream_type_check(self, s):
        keys = ["telemetry", "gyroscope", "EEG", "accelerometer"]
        if s not in keys:
            raise ValueError("Stream does not match required types")
        part = self._filename.split("_")
        if not part[-2].endswith(s):
            raise ValueError("Stream does not match filename")
        return s


class CSV_read(file_read):
    __slots__ = ("_dtype", "_data", "_row_pos")

    def __init__(self, path, filename, stream_type):
        super().__init__(path, filename, stream_type)
        self._dtype = self._dtype_set(self._stream_type)
        self._data = self._read_file_csv() #the data from CSV
        self._row_pos = 0 #the position of current row number

    @property
    def dtype(self):
        return self._dtype

    @property
    def data(self):
        return self._data

    @property
    def row_pos(self):
        return self._row_pos

    @staticmethod
    def _dtype_set(d):
        return "<f8" #dtype: float

    @staticmethod
    def _data_check(d):
        if isinstance(d, np.ndarray):
            if d.ndim > 2 or d.ndim <= 0:
                raise ValueError("Invalid data")
            elif d.ndim == 2:
                if d.size == 0:
                    raise ValueError("Data is empty")
                else:
                    return np.array([i.reshape((2,-1)) for i in np.tile(d, (2,))]) #duplicate data to fit in _push_func
            else: #when there is 1 row of data
                if d.size == 0:
                    raise ValueError("Data is empty")
                else:
                    return np.array([i.reshape((2,-1)) for i in np.tile(np.expand_dims(d, axis=0), (2,))]) #duplicate data to fit in _push_func
        else:
            raise ValueError("Invalid data")

    def _read_file_csv(self):
        tmp_d = np.loadtxt((Path(self._path) / self._filename), dtype=self._dtype, delimiter=",") #load data with check
        return self._data_check(tmp_d)

    def _raw_data(self):
        return np.loadtxt((Path(self._path) / self._filename), dtype=self._dtype, delimiter=",") #load data without check

    def reset(self):
        self._row_pos = 0

    def start(self): #return generator to perform the stream of data
        while True:
            if self._row_pos >=0 and self._row_pos < len(self._data):
                yield self._data[self._row_pos]
                self._row_pos += 1
            else:
                self._row_pos = 0
                return


class JSON_read(file_read): #only read JSON file, but doesn't use it
    __slots__ = ("_data")

    def __init__(self, path, filename, stream_type):
        super().__init__(path, filename, stream_type)
        self._data = self._read_file_json()

    @property
    def data(self):
        return self._data

    def _read_file_json(self):
        p = Path(self._path) / self._filename
        f = p.read_text(encoding="utf8")
        return self._data_check(json.loads(f))

    @staticmethod
    def _data_check(d):
        if d != {} and d!= None:
            return d
        else:
            raise ValueError("Data is empty")


class stream_collect:
    __slots__ = ("_path", "_files", "_name_pattern")

    def __init__(self, path):
        self._path = self._path_check(path)
        self._files = self._scan_files(self._path)
        self._name_pattern = re.compile(self._choose_files(self._files))

    @property
    def path(self):
        return self._path

    @property
    def files(self):
        return self._files

    @property
    def name_pattern(self):
        return self._name_pattern

    @staticmethod
    def _path_check(p):
        tmp_p = Path(p)
        if tmp_p.exists():
            if tmp_p.is_dir() and tmp_p.is_absolute():
                return str(tmp_p)
            elif tmp_p.is_dir() and not tmp_p.is_absolute():
                return str(tmp_p.resolve(strict=True))
            else:
                raise ValueError("Path needs to be a folder")
        else:
            raise ValueError("Path does not exist")

    def _scan_files(self, p): #find all files that can be fit into the format
        pattern = re.compile(r".+\d{6}-\d{6}_.+\d\.(csv|json)$", re.I)
        tmp_f = Path(p).glob("**/*")
        tmp_files = [str(i) for i in tmp_f if i.is_file()]
        return [i for i in tmp_files if pattern.match(i)]

    @staticmethod
    def _choose_files(files): #allow user to choose which group of files to use
        filenames = [Path(i).name for i in files]
        tmp_n = [i.split(".")[0].split("_") for i in filenames] #filename handling
        for i in tmp_n:
            i[-2] = "-".join(i[-2].split("-")[:-1])
        display_stream = list(set(["id: {}\ttime: {}\tname: {}".format(i[-1], i[0], "_".join(i[1:-1])) for i in tmp_n]))
        print("The stream(s) found in the folder:")
        for i in range(len(display_stream)):
            print(str(i+1)+". "+display_stream[i])
        index = input("\nChoose the stream to replay by entering the number index: ")
        while not index.isdigit() or int(index) <= 0 or int(index) > len(display_stream): #handle wrong input
            print("Invalid input, please try again")
            index = input("\nChoose the stream to replay by entering the number index: ")
        name_pattern = display_stream[int(index)-1].replace("\t",": ").split(": ")[::-2]
        name_pattern[1], name_pattern[0] = name_pattern[0], name_pattern[1]
        return "_".join(name_pattern[:-1]) + ".+_" + name_pattern[-1]

    def read_stream(self): #read group of files using CSV_read and JSON_read
        stream_files = list(filter(lambda x:self.name_pattern.search(x), self.files))
        csv_files = [Path(i) for i in stream_files if i.lower().endswith(".csv")]
        json_files = [Path(i) for i in stream_files if i.lower().endswith(".json")]
        if not len(csv_files) == 4:
            raise ValueError("No enough CSV files")
        if not len(json_files) == 4:
            raise ValueError("No enough JSON files")
        csv_data, json_data = {}, {}
        for i in ["telemetry", "gyroscope", "EEG", "accelerometer"]:
            for j in csv_files:
                if i in j.name:
                    csv_data[i] = CSV_read(j.parent, j.name, i)
            for k in json_files:
                if i in k.name:
                    json_data[i] = JSON_read(k.parent, k.name, i)
        return {"CSV": csv_data, "JSON": json_data}
