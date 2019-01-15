import base64
import contextlib
import hashlib
import io
import os
import logging
import queue
import select
import socket
import struct
import subprocess
import sys
import threading
import time

from enum import Enum
from http.server import BaseHTTPRequestHandler
from itertools import cycle

from .proto import messages_pb2 as pb2

logger = logging.getLogger(__name__)

class NAL:
    CODED_SLICE_NON_IDR = 1  # Coded slice of a non-IDR picture
    CODED_SLICE_IDR     = 5  # Coded slice of an IDR picture
    SEI                 = 6  # Supplemental enhancement information (SEI)
    SPS                 = 7  # Sequence parameter set
    PPS                 = 8  # Picture parameter set

ALLOWED_NALS = {NAL.CODED_SLICE_NON_IDR,
                NAL.CODED_SLICE_IDR,
                NAL.SPS,
                NAL.PPS,
                NAL.SEI}

def StartMessage(resolution):
    width, height = resolution
    return pb2.ClientBound(timestamp_us=int(time.monotonic() * 1000000),
                           start=pb2.Start(width=width, height=height))

def StopMessage():
    return pb2.ClientBound(timestamp_us=int(time.monotonic() * 1000000),
                           stop=pb2.Stop())

def VideoMessage(data):
    return pb2.ClientBound(timestamp_us=int(time.monotonic() * 1000000),
                           video=pb2.Video(data=data))

def OverlayMessage(svg):
    return pb2.ClientBound(timestamp_us=int(time.monotonic() * 1000000),
                           overlay=pb2.Overlay(svg=svg))

def _parse_server_message(data):
    message = pb2.ServerBound()
    message.ParseFromString(data)
    return message

def _shutdown(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass

def _read_asset(path):
    if path == '/':
        path = 'index.html'
    elif path[0] == '/':
        path = path[1:]

    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets'))
    asset_path = os.path.abspath(os.path.join(base_path, path))

    if os.path.commonpath((base_path, asset_path)) != base_path:
        return None, None

    if path.endswith('.html'):
        content_type = 'text/html; charset=utf-8'
    elif path.endswith('.js'):
        content_type = 'application/javascript; charset=utf-8'
    elif path.endswith('.wasm'):
        content_type = 'application/wasm'
    else:
        content_type = 'application/octet-stream'

    try:
        with open(asset_path, 'rb') as f:
            return f.read(), content_type
    except Exception:
        return None, None


class HTTPRequest(BaseHTTPRequestHandler):

    def __init__(self, request_buf):
        self.rfile = io.BytesIO(request_buf)
        self.raw_requestline = self.rfile.readline()
        self.parse_request()


def _read_http_request(sock):
    request = bytearray()
    while b'\r\n\r\n' not in request:
        buf = sock.recv(2048)
        if not buf:
            break
        request.extend(buf)
    return request


def _http_ok(content, content_type):
    header = (
        'HTTP/1.1 200 OK\r\n'
        'Content-Length: %d\r\n'
        'Content-Type: %s\r\n'
        'Connection: Keep-Alive\r\n\r\n'
    ) % (len(content), content_type)
    return header.encode('ascii') + content


def _http_switching_protocols(token):
    accept_token = token.encode('ascii') + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
    accept_token = hashlib.sha1(accept_token).digest()
    header = (
        'HTTP/1.1 101 Switching Protocols\r\n'
        'Upgrade: WebSocket\r\n'
        'Connection: Upgrade\r\n'
        'Sec-WebSocket-Accept: %s\r\n\r\n'
    ) % base64.b64encode(accept_token).decode('ascii')
    return header.encode('ascii')


def _http_not_found():
    return 'HTTP/1.1 404 Not Found\r\n\r\n'.encode('ascii')


@contextlib.contextmanager
def Socket(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', port))
    sock.listen()
    try:
        yield sock
    finally:
        _shutdown(sock)
        sock.close()


class DroppingQueue:

    def __init__(self, maxsize):
        if maxsize <= 0:
            raise ValueError('Maxsize must be positive.')
        self.maxsize = maxsize
        self._items = []
        self._cond = threading.Condition(threading.Lock())

    def put(self, item, replace_last=False):
        with self._cond:
            was_empty = len(self._items) == 0
            if len(self._items) < self.maxsize:
                self._items.append(item)
                if was_empty:
                    self._cond.notify()
                return False  # Not dropped.

            if replace_last:
                self._items[len(self._items) - 1] = item
                return False  # Not dropped.

            return True  # Dropped.

    def get(self):
        with self._cond:
            while not self._items:
                self._cond.wait()
            return self._items.pop(0)


class AtomicSet:

    def __init__(self):
        self._lock = threading.Lock()
        self._set = set()

    def add(self, value):
        with self._lock:
            self._set.add(value)
            return value

    def remove(self, value):
        with self._lock:
            try:
                self._set.remove(value)
                return True
            except KeyError:
                return False

    def __len__(self):
        with self._lock:
            return len(self._set)

    def __iter__(self):
        with self._lock:
            return iter(self._set.copy())

class PresenceServer:

    SERVICE_TYPE = '_aiy_vision_video._tcp'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __init__(self, name, port):
        logger.info('Start publishing %s on port %d.', name, port)
        cmd = ['avahi-publish-service', name, self.SERVICE_TYPE, str(port), 'AIY Streaming']
        self._process = subprocess.Popen(cmd, shell=False)

    def close(self):
        self._process.terminate()
        self._process.wait()
        logger.info('Stop publishing.')


class StreamingServer:

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __init__(self, camera, bitrate=1000000, mdns_name=None,
                 tcp_port=4665, web_port=4664, annexb_port=4666):
        self._bitrate = bitrate
        self._camera = camera
        self._clients = AtomicSet()
        self._enabled_clients = AtomicSet()
        self._done = threading.Event()
        self._commands = queue.Queue()
        self._thread = threading.Thread(target=self._run,
                                        args=(mdns_name, tcp_port, web_port, annexb_port))
        self._thread.start()

    def close(self):
        self._done.set()
        self._thread.join()

    def send_overlay(self, svg):
        for client in self._enabled_clients:
            client.send_overlay(svg)

    def _start_recording(self):
        logger.info('Camera start recording')
        self._camera.start_recording(self, format='h264', profile='baseline',
            inline_headers=True, bitrate=self._bitrate, intra_period=0)

    def _stop_recording(self):
        logger.info('Camera stop recording')
        self._camera.stop_recording()

    def _process_command(self, client, command):
        was_streaming = bool(self._enabled_clients)

        if command is ClientCommand.ENABLE:
            self._enabled_clients.add(client)
        elif command is ClientCommand.DISABLE:
            self._enabled_clients.remove(client)
        elif command == ClientCommand.STOP:
            self._enabled_clients.remove(client)
            if self._clients.remove(client):
                client.stop()
            logger.info('Number of active clients: %d', len(self._clients))

        is_streaming = bool(self._enabled_clients)

        if not was_streaming and is_streaming:
            self._start_recording()
        if was_streaming and not is_streaming:
            self._stop_recording()

    def _run(self, mdns_name, tcp_port, web_port, annexb_port):
        try:
            with contextlib.ExitStack() as stack:
                logger.info('Listening on ports tcp: %d, web: %d, annexb: %d',
                            tcp_port, web_port, annexb_port)
                tcp_socket = stack.enter_context(Socket(tcp_port))
                web_socket = stack.enter_context(Socket(web_port))
                annexb_socket = stack.enter_context(Socket(annexb_port))
                if mdns_name:
                    stack.enter_context(PresenceServer(mdns_name, tcp_port))

                socks = (tcp_socket, web_socket, annexb_socket)
                while not self._done.is_set():
                    # Process available client commands.
                    try:
                        while True:
                            client, command = self._commands.get_nowait()
                            self._process_command(client, command)
                    except queue.Empty:
                        pass  # Done processing commands.

                    # Process recently connected clients.
                    rlist, _, _ = select.select(socks, [], [], 0.2)  # 200ms
                    for ready in rlist:
                        sock, addr = ready.accept()
                        name = '%s:%d' % addr
                        if ready is tcp_socket:
                            client = ProtoClient(name, sock, self._commands, self._camera.resolution)
                        elif ready is web_socket:
                            client = WsProtoClient(name, sock, self._commands, self._camera.resolution)
                        elif ready is annexb_socket:
                            client = AnnexbClient(name, sock, self._commands)
                        logger.info('New %s connection from %s', client.TYPE, name)

                        self._clients.add(client).start()
                        logger.info('Number of active clients: %d', len(self._clients))
        finally:
            logger.info('Server is shutting down')
            if self._enabled_clients:
                self._stop_recording()

            for client in self._clients:
                client.stop()
            logger.info('Done')

    def write(self, data):
        """Called by camera thread for each compressed frame."""
        assert data[0:4] == b'\x00\x00\x00\x01'
        frame_type = data[4] & 0b00011111
        if frame_type in ALLOWED_NALS:
            states = {client.send_video(frame_type, data) for client in self._enabled_clients}
            if ClientState.ENABLED_NEEDS_SPS in states:
                logger.info('Requesting key frame')
                self._camera.request_key_frame()

class ClientLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return '[%s] %s' % (self.extra['name'], msg), kwargs

class ClientState(Enum):
    DISABLED = 1
    ENABLED_NEEDS_SPS = 2
    ENABLED = 3

class ClientCommand(Enum):
    STOP = 1
    ENABLE = 2
    DISABLE = 3

class Client:
    def __init__(self, name, sock, command_queue):
        self._lock = threading.Lock()  # Protects _state.
        self._state = ClientState.DISABLED
        self._logger = ClientLogger(logger, {'name': name})
        self._socket = sock
        self._commands = command_queue
        self._tx_q = DroppingQueue(15)
        self._rx_thread = threading.Thread(target=self._rx_run)
        self._tx_thread = threading.Thread(target=self._tx_run)

    def start(self):
        self._rx_thread.start()
        self._tx_thread.start()

    def stop(self):
        self._logger.info('Stopping...')
        _shutdown(self._socket)
        self._socket.close()
        self._tx_q.put(None)
        self._tx_thread.join()
        self._rx_thread.join()
        self._logger.info('Stopped.')

    def send_video(self, frame_type, data):
        """Only called by camera thread."""
        with self._lock:
            if self._state == ClientState.DISABLED:
                pass
            elif self._state == ClientState.ENABLED_NEEDS_SPS:
                if frame_type == NAL.SPS:
                    dropped = self._queue_video(data)
                    if not dropped:
                        self._state = ClientState.ENABLED
            elif self._state == ClientState.ENABLED:
                dropped = self._queue_video(data)
                if dropped:
                    self._state = ClientState.ENABLED_NEEDS_SPS
            return self._state

    def send_overlay(self, svg):
        """Can be called by any user thread."""
        with self._lock:
            if self._state != ClientState.DISABLED:
                self._queue_overlay(svg)

    def _send_command(self, command):
        self._commands.put((self, command))

    def _queue_message(self, message, replace_last=False):
        dropped = self._tx_q.put(message, replace_last)
        if dropped:
            self._logger.warning('Running behind, dropping messages')
        return dropped

    def _tx_run(self):
        try:
            while True:
                message = self._tx_q.get()
                if message is None:
                    break
                self._send_message(message)
            self._logger.info('Tx thread finished')
        except Exception as e:
            self._logger.warning('Tx thread failed: %s', e)

        # Tx thread stops the client in any situation.
        self._send_command(ClientCommand.STOP)

    def _rx_run(self):
        try:
            while True:
                message = self._receive_message()
                if message is None:
                    break
                self._handle_message(message)
            self._logger.info('Rx thread finished')
        except Exception as e:
            self._logger.warning('Rx thread failed: %s', e)
            # Rx thread stops the client only if error happened.
            self._send_command(ClientCommand.STOP)

    def _receive_bytes(self, num_bytes):
        received = bytearray()
        while len(received) < num_bytes:
            buf = self._socket.recv(num_bytes - len(received))
            if not buf:
                return buf
            received.extend(buf)
        return received

    def _queue_video(self, data):
        raise NotImplementedError

    def _queue_overlay(self, svg):
        raise NotImplementedError

    def _send_message(self, message):
        raise NotImplementedError

    def _receive_message(self):
        raise NotImplementedError

    def _handle_message(self, message):
        pass

class ProtoClient(Client):
    TYPE = 'tcp'

    def __init__(self, name, sock, command_queue, resolution):
        super().__init__(name, sock, command_queue)
        self._resolution = resolution

    def _queue_video(self, data):
        return self._queue_message(VideoMessage(data))

    def _queue_overlay(self, svg):
        return self._queue_message(OverlayMessage(svg))

    def _handle_message(self, message):
        which = message.WhichOneof('message')
        if which == 'stream_control':
            self._handle_stream_control(message.stream_control)

    def _handle_stream_control(self, stream_control):
        enabled = stream_control.enabled
        self._logger.info('stream_control %s', enabled)

        with self._lock:
            if self._state == ClientState.DISABLED and not enabled:
                self._logger.info('Ignoring stream_control disable')
            elif self._state in (ClientState.ENABLED_NEEDS_SPS, ClientState.ENABLED) and enabled:
                self._logger.info('Ignoring stream_control enable')
            else:
                if enabled:
                    self._logger.info('Enabling client')
                    self._state = ClientState.ENABLED_NEEDS_SPS
                    self._queue_message(StartMessage(self._resolution))
                    self._send_command(ClientCommand.ENABLE)
                else:
                    self._logger.info('Disabling client')
                    self._state = ClientState.DISABLED
                    self._queue_message(StopMessage(), replace_last=True)
                    self._send_command(ClientCommand.DISABLE)

    def _send_message(self, message):
        buf = message.SerializeToString()
        self._socket.sendall(struct.pack('!I', len(buf)))
        self._socket.sendall(buf)

    def _receive_message(self):
        buf = self._receive_bytes(4)
        if not buf:
            return None
        num_bytes = struct.unpack('!I', buf)[0]
        buf = self._receive_bytes(num_bytes)
        if not buf:
            return None
        return _parse_server_message(buf)


class WsProtoClient(ProtoClient):
    TYPE = 'web'

    class WsPacket:
        def __init__(self):
            self.fin = True
            self.opcode = 2
            self.masked = False
            self.mask = None
            self.length = 0
            self.payload = bytearray()

        def append(self, data):
            if self.masked:
                data = bytes([c ^ k for c, k in zip(data, cycle(self.mask))])
            self.payload.extend(data)

        def serialize(self):
            self.length = len(self.payload)
            buf = bytearray()
            b0 = 0
            b1 = 0
            if self.fin:
                b0 |= 0x80
            b0 |= self.opcode
            buf.append(b0)
            if self.length <= 125:
                b1 |= self.length
                buf.append(b1)
            elif self.length >= 126 and self.length <= 65535:
                b1 |= 126
                buf.append(b1)
                buf.extend(struct.pack('!H', self.length))
            else:
                b1 |= 127
                buf.append(b1)
                buf.extend(struct.pack('!Q', self.length))
            if self.payload:
                buf.extend(self.payload)
            return bytes(buf)

    def __init__(self, name, sock, command_queue, resolution):
        super().__init__(name, sock, command_queue, resolution)
        self._upgraded = False

    def _receive_message(self):
        try:
            if not self._upgraded:
                if self._process_web_request():
                    return None
                self._upgraded = True

            packets = []
            while True:
                packet = self._receive_packet()
                if packet.opcode == 0:
                    # Continuation
                    if not packets:
                        self._logger.error('Invalid continuation received')
                        return None
                    packets.append(packet)
                elif packet.opcode == 1:
                    # Text, not supported.
                    self._logger.error('Received text packet')
                    return None
                elif packet.opcode == 2:
                    # Binary.
                    packets.append(packet)
                    if packet.fin:
                        joined = bytearray()
                        for p in packets:
                            joined.extend(p.payload)
                        return _parse_server_message(joined)
                elif packet.opcode == 8:
                    # Close.
                    self._logger.info('WebSocket close requested')
                    return None
                elif packet.opcode == 9:
                    # Ping, send pong.
                    self._logger.info('Received ping')
                    response = self.WsPacket()
                    response.opcode = 10
                    response.append(packet.payload)
                    self._queue_message(response)
                elif packet.opcode == 10:
                    # Pong. Igore as we don't send pings.
                    self._logger.info('Dropping pong')
                else:
                    self._logger.info('Dropping opcode %d', packet.opcode)
        except Exception:
            self._logger.exception('Error while processing websocket request')
            return None

    def _receive_packet(self):
        packet = self.WsPacket()
        buf = self._receive_bytes(2)
        packet.fin = buf[0] & 0x80 > 0
        packet.opcode = buf[0] & 0x0F
        packet.masked = buf[1] & 0x80 > 0
        packet.length = buf[1] & 0x7F
        if packet.length == 126:
            packet.length = struct.unpack('!H', self._receive_bytes(2))[0]
        elif packet.length == 127:
            packet.length = struct.unpack('!Q', self._receive_bytes(8))[0]
        if packet.masked:
            packet.mask = self._receive_bytes(4)
        packet.append(self._receive_bytes(packet.length))
        return packet

    def _send_message(self, message):
        if isinstance(message, (bytes, bytearray)):
            buf = message
        else:
            if isinstance(message, self.WsPacket):
                packet = message
            else:
                packet = self.WsPacket()
                packet.append(message.SerializeToString())
            buf = packet.serialize()
        self._socket.sendall(buf)

    def _process_web_request(self):
        request = _read_http_request(self._socket)
        request = HTTPRequest(request)
        connection = request.headers['Connection']
        upgrade = request.headers['Upgrade']
        if 'Upgrade' in connection and upgrade == 'websocket':
            sec_websocket_key = request.headers['Sec-WebSocket-Key']
            self._queue_message(_http_switching_protocols(sec_websocket_key))
            self._logger.info('Upgraded to WebSocket')
            return False

        if request.command == 'GET':
            content, content_type = _read_asset(request.path)
            if content is None:
                self._queue_message(_http_not_found())
            else:
                self._queue_message(_http_ok(content, content_type))
            self._queue_message(None)
            return True

        raise Exception('Unsupported request')


class AnnexbClient(Client):
    TYPE = 'annexb'

    def __init__(self, name, sock, command_queue):
        super().__init__(name, sock, command_queue)
        self._state = ClientState.ENABLED_NEEDS_SPS
        self._send_command(ClientCommand.ENABLE)

    def _queue_video(self, data):
        return self._queue_message(data)

    def _queue_overlay(self, svg):
        pass  # Ignore overlays.

    def _send_message(self, message):
        self._socket.sendall(message)

    def _receive_message(self):
        buf = self._socket.recv(1024)
        if not buf:
            return None
        raise RuntimeError('Invalid state.')
