var g_socket = null;
var g_container = null;
var g_player = null;
var g_canvas = null;
var g_frame_count = 0;

var ClientBound = null;
var ServerBound = null;

protobuf.load("messages.proto", function(err, root) {
  if (err)
    throw err;

  ClientBound = root.lookupType("ClientBound");
  ServerBound = root.lookupType("ServerBound")

  g_container = document.getElementById("container");
  g_socket = new WebSocket("ws://" + window.location.host);
  g_socket.binaryType = "arraybuffer";
  g_socket.onopen = ws_opened;
  g_socket.onclose = ws_closed;
  g_socket.onmessage = ws_message;
})

function ws_opened(event) {
  console.log("Socket connected");
  stream_control(true);
};

function ws_closed(event) {
  console.log("Socket closed");
};

function ws_message(event) {
  var clientBound = ClientBound.decode(new Uint8Array(event.data))
  switch (clientBound.message) {
    case 'start':
      handle_start(clientBound.start);
      break;
    case 'video':
      handle_video(clientBound.video);
      break;
    case 'overlay':
      handle_overlay(clientBound.overlay);
      break;
    case 'stop':
      handle_stop(clientBound.stop);
      break;
  }
};

function stream_control(enabled) {
  serverBound = ServerBound.create({streamControl: {enabled:enabled}});
  g_socket.send(ServerBound.encode(serverBound).finish());
};

function handle_start(start) {
  console.log('Starting...')

  if (g_player != null) {
    return
  }

  g_player = new Player({
    useWorker: true,
    workerFile: "broadway/Decoder.js",
    reuseMemory: true,
    webgl: "auto",
    size: {
      width: start.width,
      height: start.height,
    }
  });

  g_player.onPictureDecoded = function(data) {
    if (!g_frame_count) {
      console.log("First frame decoded");
    }
    g_frame_count++;
  };

  var crop_div = document.createElement("div");
  crop_div.style.overflow = "hidden";
  crop_div.style.position = "absolute";
  crop_div.style.width = start.width + "px";
  crop_div.style.height = start.height + "px";
  crop_div.appendChild(g_player.canvas);
  g_container.appendChild(crop_div);

  g_canvas = document.createElement("canvas");
  g_canvas.style.position = "absolute";
  g_canvas.width = start.width;
  g_canvas.height = start.height;
  g_container.appendChild(g_canvas);

  var license_link = document.createElement("a");
  license_link.appendChild(document.createTextNode("Open source licenses"));
  license_link.title = "LICENSE";
  license_link.href = "broadway/LICENSE";
  license_link.target= "_blank";
  license_link.style.position = "relative";
  license_link.style.top = start.height + "px";
  g_container.appendChild(license_link);

  var startButton = document.getElementById("start");
  startButton.onclick = function() {
    console.log('Start clicked!')
    stream_control(true);
  }

  var stopButton = document.getElementById("stop");
  stopButton.onclick = function() {
    console.log('Stop clicked!')
    stream_control(false);
  }

  console.log("Started: " + start.width + "x" + start.height);
}

function handle_stop(stop) {
  console.log("Stopped.");
}

function handle_video(video) {
  g_player.decode(video.data);
}

function handle_overlay(overlay) {
  if (!g_canvas || !g_frame_count) {
    return;
  }

  var ctx = g_canvas.getContext("2d");
  var img = new Image();
  img.onload = function() {
    ctx.clearRect(0, 0, g_canvas.width, g_canvas.height);
    ctx.drawImage(img, 0, 0, g_canvas.width, g_canvas.height);
  }
  img.src = "data:image/svg+xml;charset=utf-8," + overlay.svg;
}
