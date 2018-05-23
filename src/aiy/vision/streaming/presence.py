import dbus
import logging
import threading
import time


DEVICE_NAME_FILE = '/home/pi/.config/aiy/device_name'

DBUS_NAME = 'org.freedesktop.Avahi'
DBUS_PATH_SERVER = '/'
DBUS_INTERFACE_SERVER = DBUS_NAME + '.Server'
DBUS_INTERFACE_ENTRY_GROUP = DBUS_NAME + '.EntryGroup'
IF_ANY = -1
PROTO_INET = 0


class PresenceServer(object):
    def __init__(self, service, port):
        self._logger = logging.getLogger('logger')
        self._service = service
        self._port = port
        self._name_thread = None

        bus = dbus.SystemBus()
        server = dbus.Interface(bus.get_object(DBUS_NAME, DBUS_PATH_SERVER),
                                DBUS_INTERFACE_SERVER)
        self._group = dbus.Interface(
            bus.get_object(DBUS_NAME, server.EntryGroupNew()),
            DBUS_INTERFACE_ENTRY_GROUP)

    def __del__(self):
        self.close()

    def close(self):
        if self._name_thread is not None:
            self._name_thread.close()
            self._name_thread = None
            self._group.Reset()

    def run(self):
        self._name_thread = _NameThread(self)
        self._update_device_name(self._name_thread.read_name())
        self._name_thread.start()

    def _update_device_name(self, device_name):
        def string_to_byte_array(s):
            res = []
            for c in s:
                res.append(dbus.Byte(ord(c)))
            return res

        def string_array_to_txt_array(sa):
            res = []
            for s in sa:
                res.append(string_to_byte_array(s))
            return res

        self._group.Reset()

        if not device_name:
            self._logger.info('Device name not set, not advertising')
            return

        self._logger.info('Advertising as %s on port %d', device_name, self._port)
        self._group.AddService(IF_ANY, PROTO_INET, 0, device_name, self._service,
                               '', '', self._port, string_array_to_txt_array(['name=' + device_name]))
        self._group.Commit()


class _NameThread(threading.Thread):
    def __init__(self, owner):
        threading.Thread.__init__(self)
        self._logger = logging.getLogger('logger')
        self._lock = threading.Lock()
        self.daemon = True
        self._closed = False
        self._owner = owner
        self._device_name = self.read_name()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._owner = None

    def run(self):
        while not self._closed:
            try:
                name = self.read_name()
                with self._lock:
                    changed = self._device_name != name
                    self._device_name = name
                if changed and self._owner:
                    self._owner._update_device_name(name)
            except OSError:
                pass
            finally:
                time.sleep(1)

    def read_name(self):
        try:
            with self._lock, open(DEVICE_NAME_FILE, 'r') as name_file:
                return name_file.read().strip()
        except OSError:
            return None
