import base64
import hashlib
import os
import logging
import select
import socket
import struct
import sys
import threading
import time

from aiy.vision.streaming.presence import PresenceServer
import aiy.vision.streaming.proto.messages_pb2 as pb2

from http.server import BaseHTTPRequestHandler
from io import BytesIO
from itertools import cycle
from picamera import PiVideoFrameType


AVAHI_SERVICE = '_aiy_vision_video._tcp'
ENCODING_BIT_RATE = 1000000
TX_QUEUE_SIZE = 15
WS_PORT = 4664
TCP_PORT = 4665
ANNEXB_PORT = 4666


def _close_socket(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


class StreamingServer(object):

    def __init__(self, camera):
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        self._camera = camera
        self._stream_count = 0
        self._tcp_socket = None
        self._web_socket = None
        self._annexb_socket = None
        self._thread = None
        self._closed = False
        self._waiting_for_key = False
        self._start_time = time.monotonic()
        self._seq = 0
        self._clients = []

    def run(self):
        with self._lock:
            if self._thread:
                self._logger.error('Server already running')
                return
            self._closed = False
            self._thread = threading.Thread(target=self._server_thread)
            self._thread.start()

    def close(self):
        to_join = None
        clients = None
        with self._lock:
            if self._closed:
                return
            self._closed = True

            clients = self._clients
            self._clients = []
            if self._tcp_socket:
                _close_socket(self._tcp_socket)
                self._tcp_socket = None
            if self._web_socket:
                _close_socket(self._web_socket)
                self._web_socket = None
            if self._annexb_socket:
                _close_socket(self._annexb_socket)
                self._annexb_socket = None
            if self._thread:
                to_join = self._thread
                self._thread = None
        if clients:
            self._logger.info('Closing %d clients', len(clients))
            for client in clients:
                client.close()
        if to_join:
            to_join.join()
        self._logger.info('Server closed')

    def _server_thread(self):
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tcp_socket.bind(('', TCP_PORT))
        tcp_socket.listen()
        tcp_port = tcp_socket.getsockname()[1]

        web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        web_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        web_socket.bind(('', WS_PORT))
        web_socket.listen()
        web_port = web_socket.getsockname()[1]

        annexb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        annexb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        annexb_socket.bind(('', ANNEXB_PORT))
        annexb_socket.listen()
        annexb_port = annexb_socket.getsockname()[1]

        with self._lock:
            self._tcp_socket = tcp_socket
            self._web_socket = web_socket
            self._annexb_socket = annexb_socket

        self._logger.info('Listening on ports tcp: %d web: %d annexb: %d',
                          tcp_port, web_port, annexb_port)

        presence = PresenceServer(AVAHI_SERVICE, tcp_port)
        presence.run()

        while True:
            with self._lock:
                if self._closed:
                    break
            socks = [tcp_socket, web_socket, annexb_socket]
            try:
                rlist, _, _ = select.select(socks, socks, socks)
                for ready in rlist:
                    client_sock, client_addr = ready.accept()
                    if ready == tcp_socket:
                        kind = 'tcp'
                        client = _ProtoClient(self, client_sock, client_addr)
                    elif ready == web_socket:
                        kind = 'web'
                        client = _WsProtoClient(self, client_sock, client_addr)
                    elif ready == annexb_socket:
                        kind = 'annexb'
                        client = _AnnexbClient(self, client_sock, client_addr)
                    else:
                        # Shouldn't happen.
                        client_sock.close()
                        continue

                    self._logger.info('New %s connection from %s:%d', kind,
                                      client_addr[0], client_addr[1])

                    with self._lock:
                        self._clients.append(client)
                    client.start()
            except:
                self._logger.info('Server sockets closed')

        self._logger.info('Server shutting down')
        presence.close()
        _close_socket(tcp_socket)
        _close_socket(web_socket)
        _close_socket(annexb_socket)
        with self._lock:
            self._tcp_socket = None
            self._web_socket = None
            self._annexb_socket = None

    def _stream_control(self, enable):
        start_recording = False
        stop_recording = False
        with self._lock:
            if enable:
                self._stream_count += 1
                start_recording = self._stream_count == 1
            else:
                self._stream_count -= 1
                stop_recording = self._stream_count == 0
        if start_recording:
            self._logger.info('Start recording')
            self._camera.start_recording(
                _EncoderSink(self),
                format='h264',
                profile='baseline',
                inline_headers=True,
                bitrate=ENCODING_BIT_RATE,
                intra_period=0)
        if stop_recording:
            self._logger.info('Stop recording')
            self._camera.stop_recording()

    def _client_closed(self, client):
        with self._lock:
            if client in self._clients:
                self._clients.remove(client)

    def _on_video_data(self, data):
        frame_type = self._camera.frame.frame_type
        is_key = frame_type == PiVideoFrameType.key_frame
        is_delta = frame_type == PiVideoFrameType.frame
        is_codec_data = frame_type == PiVideoFrameType.sps_header
        if is_key:
            self._waiting_for_key = False
        needs_key = False
        if is_codec_data:
            with self._lock:
                for client in self._clients:
                    needs_key |= client.send_codec_data(self._camera.resolution, data)
        elif is_key or is_delta:
            needs_key = False
            pts = int((time.monotonic() - self._start_time) * 1e6)
            with self._lock:
                for client in self._clients:
                    needs_key |= client.send_frame_data(is_key, self._seq, pts, data)
                self._seq += 1
        else:
            self._logger.info('Unknown frame %d bytes', len(data))
        if needs_key:
            self._request_key_frame()

    def send_inference_data(self, data):
        needs_key = False
        with self._lock:
            for client in self._clients:
                needs_key |= client.send_inference_data(data)
        if needs_key:
            self._request_key_frame()

    def _request_key_frame(self):
        if not self._waiting_for_key:
            self._logger.info('Requesting key frame')
            self._camera.request_key_frame()
            self._waiting_for_key = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class _EncoderSink(object):

    def __init__(self, server):
        self._server = server

    def write(self, data):
        self._server._on_video_data(data)

    def flush(self):
        pass


class _Client(object):
    def __init__(self, server, socket, addr):
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._logger = logging.getLogger(__name__)
        self._streaming = False
        self._closed = False
        self._server = server
        self._socket = socket
        self._ip = addr[0]
        self._port = addr[1]
        self._tx_q = []
        self._needs_codec_data = True
        self._needs_key = True
        self._rx_thread = threading.Thread(target=self._rx_thread)
        self._tx_thread = threading.Thread(target=self._tx_thread)

    def start(self):
        self._rx_thread.start()
        self._tx_thread.start()

    def __del__(self):
        self.close()

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._cond.notifyAll()
            streaming = self._streaming
            self._streaming = False
        _close_socket(self._socket)

        self._log_info('Connection closed')
        if streaming:
            self._server._stream_control(False)
        self._server._client_closed(self)

    def send_codec_data(self, resolution, data):
        with self._lock:
            if not self._streaming:
                return False
            self._needs_codec_data = False
            return self._queue_codec_data_locked(resolution, data)

    def send_frame_data(self, is_key, seq, pts, data):
        with self._lock:
            if not self._streaming:
                return False

            if self._needs_codec_data:
                return True

            if self._needs_key and not is_key:
                return True
            self._needs_key = False

            return self._queue_frame_data_locked(is_key, seq, pts, data)

    def send_inference_data(self, data):
        with self._lock:
            if not self._streaming:
                return False
            return self._queue_inference_data_locked(data)

    def _log(self, func, fmt, *args):
        args = (self._ip, self._port) + args
        func('%s:%d: ' + fmt, *args)

    def _log_info(self, fmt, *args):
        self._log(self._logger.info, fmt, *args)

    def _log_warning(self, fmt, *args):
        self._log(self._logger.warning, fmt, *args)

    def _log_error(self, fmt, *args):
        self._log(self._logger.error, fmt, *args)

    def _queue_message_locked(self, message):
        dropped = False
        self._tx_q.append(message)
        while len(self._tx_q) > TX_QUEUE_SIZE:
            dropped = True
            self._tx_q.pop(0)
            self._needs_codec_data = True
            self._needs_key = True
            self._log_warning('running behind, dropping messages')
        self._cond.notifyAll()
        return dropped

    def _tx_thread(self):
        while True:
            with self._lock:
                if self._closed:
                    break
                if self._tx_q:
                    message = self._tx_q.pop(0)
                else:
                    self._cond.wait()
                    continue
            try:
                self._send_message(message)
            except Exception as e:
                self._log_error('Failed to send data: %s', e)
                self.close()

    def _rx_thread(self):
        while True:
            with self._lock:
                if self._closed:
                    break

            message = self._receive_message()
            if message:
                self._handle_message(message)
            else:
                self.close()


class _ProtoClient(_Client):
    def __init__(self, server, socket, addr):
        _Client.__init__(self, server, socket, addr)

    def _queue_codec_data_locked(self, resolution, data):
        message = pb2.ClientBound()
        message.stream_data.codec_data.width = resolution[0]
        message.stream_data.codec_data.height = resolution[1]
        message.stream_data.codec_data.data = data
        return self._queue_message_locked(message)

    def _queue_frame_data_locked(self, is_key, seq, pts, data):
        message = pb2.ClientBound()
        if is_key:
            message.stream_data.frame_data.type = pb2.FrameData.KEY
        else:
            message.stream_data.frame_data.type = pb2.FrameData.DELTA
        message.stream_data.frame_data.seq = seq
        message.stream_data.frame_data.pts = pts
        message.stream_data.frame_data.data = data
        return self._queue_message_locked(message)

    def _queue_inference_data_locked(self, data):
        return self._queue_message_locked(data.GetMessage())

    def _handle_message(self, message):
        which = message.WhichOneof('message')
        try:
            if which == 'stream_control':
                self._handle_stream_control(message.stream_control)
            else:
                self._log_warning('unhandled message %s', which)
        except Exception as e:
            self._log_error('Error handling message %s: %s', which, e)
            self.close()

    def _handle_stream_control(self, stream_control):
        self._log_info('stream_control %s', stream_control.enabled)
        enabled = stream_control.enabled
        with self._lock:
            if enabled == self._streaming:
                self._log_info('ignoring NOP stream_control')
                return
            else:
                self._streaming = enabled
        self._server._stream_control(enabled)

    def _send_message(self, message):
        buf = message.SerializeToString()
        self._socket.sendall(struct.pack('!I', len(buf)))
        self._socket.sendall(buf)

    def _receive_bytes(self, num_bytes):
        received = bytearray(b'')
        while num_bytes > len(received):
            buf = self._socket.recv(num_bytes - len(received))
            if not buf:
                break
            received.extend(buf)
        return bytes(received)

    def _receive_message(self):
        try:
            buf = self._receive_bytes(4)
            num_bytes = struct.unpack('!I', buf)[0]
            buf = self._receive_bytes(num_bytes)
            message = pb2.AiyBound()
            message.ParseFromString(buf)
            return message
        except:
            return None


class _WsProtoClient(_ProtoClient):
    class WsPacket(object):
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

    def __init__(self, server, socket, addr):
        self._handshaked = False
        _ProtoClient.__init__(self, server, socket, addr)

    def _receive_message(self):
        try:
            while True:
                if self._handshaked:
                    break
                self._process_web_request()

            packets = []
            while True:
                packet = self._receive_packet()
                if packet.opcode == 0:
                    # Continuation
                    if not packets:
                        self._log_error('Invalid continuation received')
                        return None
                    packets.append(packet)
                elif packet.opcode == 1:
                    # Text, not supported.
                    self._log_error('Received text packet')
                    return None
                elif packet.opcode == 2:
                    # Binary.
                    packets.append(packet)
                    if packet.fin:
                        joined = bytearray()
                        for p in packets:
                            joined.extend(p.payload)
                        message = pb2.AiyBound()
                        message.ParseFromString(joined)
                        return message
                elif packet.opcode == 8:
                    # Close.
                    self._log_info('WebSocket close requested')
                    return None
                elif packet.opcode == 9:
                    # Ping, send pong.
                    self._log_info('Received ping')
                    response = self.WsPacket()
                    response.opcode = 10
                    response.append(packet.payload)
                    with self._lock:
                        self._queue_message_locked(response)
                elif packet.opcode == 10:
                    # Pong. Igore as we don't send pings.
                    self._log_info('Dropping pong')
                else:
                    self._log_info('Dropping opcode %d', packet.opcode)
        except:
            return None

    def _receive_packet(self):
        packet = self.WsPacket()
        buf = super()._receive_bytes(2)
        packet.fin = buf[0] & 0x80 > 0
        packet.opcode = buf[0] & 0x0F
        packet.masked = buf[1] & 0x80 > 0
        packet.length = buf[1] & 0x7F
        if packet.length == 126:
            packet.length = struct.unpack('!H', super()._receive_bytes(2))[0]
        elif packet.length == 127:
            packet.length = struct.unpack('!Q', super()._receive_bytes(8))[0]
        if packet.masked:
            packet.mask = super()._receive_bytes(4)
        packet.append(super()._receive_bytes(packet.length))
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

    class HTTPRequest(BaseHTTPRequestHandler):
        def __init__(self, request_buf):
            self.rfile = BytesIO(request_buf)
            self.raw_requestline = self.rfile.readline()
            self.parse_request()

    def _process_web_request(self):
        response_template = (
            'HTTP/1.1 200 OK\r\n'
            'Content-Length: %(content_length)s\r\n'
            'Connection: Keep-Alive\r\n\r\n'
        )
        try:
            header_buf = bytearray()
            while b'\r\n\r\n' not in header_buf:
                buf = self._socket.recv(2048)
                if not buf:
                    raise Exception('Socket closed while receiving header')
                header_buf.extend(buf)
                if len(header_buf) >= 10 * 1024:
                    raise Exception('HTTP header too large')
            request = self.HTTPRequest(header_buf)

            connection = request.headers['Connection']
            upgrade = request.headers['Upgrade']
            if 'Upgrade' in connection and upgrade == 'websocket':
                self._handshake(request)
            elif request.command == 'GET':
                content = self._get_asset(request.path)
                response_hdr = response_template % {'content_length': len(content)}
                response = bytearray(response_hdr.encode('ascii'))
                response.extend(content)
                with self._lock:
                    self._queue_message_locked(response)
            else:
                raise Exception('Unsupported request')
        except Exception as e:
            self.close()
            raise e

    def _handshake(self, request):
        magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
        response_template = (
            'HTTP/1.1 101 Switching Protocols\r\n'
            'Upgrade: WebSocket\r\n'
            'Connection: Upgrade\r\n'
            'Sec-WebSocket-Accept: %(sec_key)s\r\n\r\n'
        )

        try:
            sec_key = request.headers['Sec-WebSocket-Key']
            sec_key = sec_key.encode('ascii') + magic.encode('ascii')
            sec_key = base64.b64encode(hashlib.sha1(sec_key).digest()).decode('ascii')
            response = response_template % {'sec_key': sec_key}
            with self._lock:
                self._queue_message_locked(response.encode('ascii'))
            self._handshaked = True
            self._log_info('Upgraded to WebSocket')
        except Exception as e:
            self._log_error('WebSocket handshake error: %s', e)
            self.close()

    def _get_asset(self, path):
        if not path or '..' in path:
            return 'Nice try'.encode('ascii')
        if path == '/':
            path = 'index.html'
        elif path[0] == '/':
            path = path[1:]
        path = os.path.join(os.path.dirname(__file__), 'assets', path)
        try:
            with open(path, 'rb') as asset:
                return asset.read()
        except:
            return b''


class _AnnexbClient(_Client):
    def __init__(self, server, socket, addr):
        _Client.__init__(self, server, socket, addr)
        with self._lock:
            self._streaming = True
        self._server._stream_control(True)

    def start(self):
        super().start()
        with self._lock:
            self._streaming = True
        self._server._stream_control(True)

    def _queue_codec_data_locked(self, resolution, data):
        return self._queue_message_locked(data)

    def _queue_frame_data_locked(self, is_key, seq, pts, data):
        return self._queue_message_locked(data)

    def _queue_inference_data_locked(self, data):
        # Silently drop inference data.
        return False

    def _handle_message(self, message):
        pass

    def _send_message(self, message):
        self._socket.sendall(message)

    def _receive_message(self):
        try:
            buf = self._socket.recv(1024)
            if not buf:
                return None
            else:
                return buf
        except:
            return None


class InferenceData(object):
    def __init__(self):
        self._message = pb2.ClientBound()
        self._message.stream_data.inference_data.SetInParent()

    def _get_color(value):
        if isinstance(value, int):
            return value
        if isinstance(value, tuple):
            if len(value) == 3:
                color = 0xFF000000
                color |= (value[0] & 0xff) << 16
                color |= (value[1] & 0xff) << 8
                color |= (value[2] & 0xff) << 0
                return color
            if len(value) == 4:
                color = 0
                color |= (value[0] & 0xff) << 24
                color |= (value[1] & 0xff) << 16
                color |= (value[2] & 0xff) << 8
                color |= (value[3] & 0xff) << 0
                return color
        return 0xFFFFFFFF

    def add_rectangle(self, x, y, w, h, color, weight):
        element = self._message.stream_data.inference_data.elements.add()
        element.rectangle.x = x
        element.rectangle.y = y
        element.rectangle.w = w
        element.rectangle.h = h
        element.rectangle.color = InferenceData._get_color(color)
        element.rectangle.weight = weight

    def add_label(self, text, x, y, color, size):
        element = self._message.stream_data.inference_data.elements.add()
        element.label.text = text
        element.label.x = x
        element.label.y = y
        element.label.color = InferenceData._get_color(color)
        element.label.size = size

    def GetMessage(self):
        return self._message
