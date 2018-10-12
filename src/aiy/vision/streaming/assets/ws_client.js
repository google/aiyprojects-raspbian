var g_socket = null;
var g_last_frame_seq = -1;
var g_container = null;
var g_player = null;
var g_canvas = null;
var g_frame_count = 0;

var ClientBound = null;
var AiyBound = null;

protobuf.load("messages.proto", function(err, root) {
  if (err)
    throw err;

  ClientBound = root.lookupType("ClientBound");
  AiyBound = root.lookupType("AiyBound")

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
  if (clientBound.message == 'streamData') {
    var streamData = clientBound.streamData
    switch (streamData.type) {
      case 'inferenceData':
        handle_inference_data(streamData.inferenceData);
        break;
      case 'frameData':
        handle_frame_data(streamData.frameData);
        break;
      case 'codecData':
        handle_codec_data(streamData.codecData);
        break;
    }
  }
};

function stream_control(enabled) {
  aiyBound = AiyBound.create({streamControl: {enabled:enabled}});
  g_socket.send(AiyBound.encode(aiyBound).finish());
};

function handle_codec_data(data) {
  if (g_player == null) {
    g_player = new Player({
      useWorker: true,
      workerFile: "broadway/Decoder.js",
      reuseMemory: true,
      webgl: "auto",
      size: {
        width: data.width,
        height: data.height,
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
    crop_div.style.width = data.width + "px";
    crop_div.style.height = data.height + "px";
    crop_div.appendChild(g_player.canvas);
    g_container.appendChild(crop_div);

    g_canvas = document.createElement("canvas");
    g_canvas.style.position = "absolute";
    g_canvas.width = data.width;
    g_canvas.height = data.height;
    g_container.appendChild(g_canvas);

    var license_link = document.createElement("a");
    license_link.appendChild(document.createTextNode("Open source licenses"));
    license_link.title = "LICENSE";
    license_link.href = "broadway/LICENSE";
    license_link.target= "_blank";
    license_link.style.position = "relative";
    license_link.style.top = data.height + "px";
    g_container.appendChild(license_link);
  }

  var sps_pps = data.data;
  console.log("Codec data: " + data.width + "x" + data.height);
  g_player.decode(sps_pps);
}

function handle_frame_data(data) {
  g_player.decode(data.data);

  var new_seq = data.seq;
  var prev_seq = g_last_frame_seq;
  g_last_frame_seq = new_seq;
  if (prev_seq > 0) {
    var dropped = new_seq - prev_seq - 1;
    if (dropped) {
      console.log("Dropped " + dropped + " frames");
    }
  }
}

function handle_inference_data(data) {
  if (!g_canvas || !g_frame_count) {
    return;
  }

var ctx = g_canvas.getContext("2d");
  var img = new Image();
  img.onload = function() {
    ctx.clearRect(0, 0, g_canvas.width, g_canvas.height);
    ctx.drawImage(img, 0, 0, g_canvas.width, g_canvas.height);
  }
  img.src = "data:image/svg+xml;charset=utf-8," + data.svg;
}
