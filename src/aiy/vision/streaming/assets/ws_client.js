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
  var width = g_canvas.width;
  var height = g_canvas.height;
  ctx.clearRect(0, 0, width, height);

  for (var i = 0; i < data.elements.length; ++i) {
    element = data.elements[i];
    switch (element.element) {
      case 'label':
        draw_label(ctx, width, height, element.label);
        break;
      case 'rectangle':
        draw_rectangle(ctx, width, height, element.rectangle);
        break;
    }
  }
}

function color_to_style(color) {
  var a = (color & 0xff000000) >>> 24;
  var r = (color & 0x00ff0000) >>> 16;
  var g = (color & 0x0000ff00) >>> 8;
  var b = (color & 0x000000ff) >>> 0;
  return "rgba(" + [r, g, b, a].join(",") + ")";
}

function draw_rectangle(ctx, frame_width, frame_height, rect) {
  var weight = rect.weight
  var x = rect.x * frame_width - weight / 2;
  var y = rect.y * frame_height - weight / 2;
  var w = rect.w * frame_width + weight / 2;
  var h = rect.h * frame_height + weight / 2;
  ctx.strokeStyle = color_to_style(rect.color);
  ctx.lineWidth = weight;
  ctx.strokeRect(x, y, w, h);
}

function draw_label(ctx, frame_width, frame_height, label) {
  var x = label.x * frame_width;
  var y = label.y * frame_height;
  var size = 12 * label.size;
  ctx.fillStyle = color_to_style(label.color);
  ctx.font = size + "px arial";
  ctx.fillText(label.text, x, y + size);
}
