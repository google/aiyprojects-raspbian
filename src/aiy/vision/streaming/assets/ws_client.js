var g_socket = null;
var g_last_frame_seq = -1;
var g_container = null;
var g_player = null;
var g_canvas = null;
var g_frame_count = 0;

function load() {
  g_container = document.getElementById("container");
  g_socket = new WebSocket("ws://" + window.location.host);
  g_socket.binaryType = "arraybuffer";
  g_socket.onopen = ws_opened;
  g_socket.onclose = ws_closed;
  g_socket.onmessage = ws_message;
}

function ws_opened(event) {
  console.log("Socket connected");
  stream_control(true);
};

function ws_closed(event) {
  console.log("Socket closed");
};

function ws_message(event) {
  message = proto.ClientBound.deserializeBinary(event.data);
  switch (message.getMessageCase()) {
    case proto.ClientBound.MessageCase.STREAM_DATA:
      handle_stream_data(message.getStreamData());
      break;
    default:
      break;
  }
};

function stream_control(enabled) {
  message = new proto.AiyBound();
  sc = new proto.StreamControl();
  sc.setEnabled(enabled);
  message.setStreamControl(sc);
  send_message(message);
};

function send_message(message) {
  g_socket.send(message.serializeBinary());
};

function handle_stream_data(data) {
  switch (data.getTypeCase()) {
    case proto.StreamData.TypeCase.CODEC_DATA:
      handle_codec_data(data.getCodecData());
      break;
    case proto.StreamData.TypeCase.FRAME_DATA:
      handle_frame_data(data.getFrameData());
      break;
    case proto.StreamData.TypeCase.INFERENCE_DATA:
      handle_inference_data(data.getInferenceData());
      break;
    default:
      break;
  }
}

function handle_codec_data(data) {
  if (g_player == null) {
    g_player = new Player({
      useWorker: true,
      workerFile: "broadway/Decoder.js",
      reuseMemory: true,
      webgl: "auto",
      size: {
        width: data.getWidth(),
        height: data.getHeight(),
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
    crop_div.style.width = data.getWidth() + "px";
    crop_div.style.height = data.getHeight() + "px";
    crop_div.appendChild(g_player.canvas);
    g_container.appendChild(crop_div);

    g_canvas = document.createElement("canvas");
    g_canvas.style.position = "absolute";
    g_canvas.width = data.getWidth();
    g_canvas.height = data.getHeight();
    g_container.appendChild(g_canvas);

    var license_link = document.createElement("a");
    license_link.appendChild(document.createTextNode("Open source licenses"));
    license_link.title = "LICENSE";
    license_link.href = "broadway/LICENSE";
    license_link.target= "_blank";
    license_link.style.position = "relative";
    license_link.style.top = data.getHeight() + "px";
    g_container.appendChild(license_link);
  }

  var sps_pps = data.getData_asU8();
  console.log("Codec data: " + data.getWidth() + "x" + data.getHeight());
  g_player.decode(sps_pps);
}

function handle_frame_data(data) {
  g_player.decode(data.getData_asU8());

  var new_seq = data.getSeq();
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

  var list = data.getElementsList();
  var len = list.length;
  for (var i = 0; i < len; i++) {
    ctx.save();
    var element = list[i];
    switch (element.getElementCase()) {
      case proto.InferenceElement.ElementCase.RECTANGLE:
        draw_rectangle(ctx, width, height, element.getRectangle());
        break;
      case proto.InferenceElement.ElementCase.LABEL:
        draw_label(ctx, width, height, element.getLabel());
        break;
      default:
        // Ignore.
        break;
    }
    ctx.restore();
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
  var weight = rect.getWeight();
  var x = rect.getX() * frame_width - weight / 2;
  var y = rect.getY() * frame_height - weight / 2;
  var w = rect.getW() * frame_width + weight / 2;
  var h = rect.getH() * frame_height + weight / 2;
  ctx.strokeStyle = color_to_style(rect.getColor());
  ctx.lineWidth = weight;
  ctx.strokeRect(x, y, w, h);
}

function draw_label(ctx, frame_width, frame_height, label) {
  var x = label.getX() * frame_width;
  var y = label.getY() * frame_height;
  var size = 12 * label.getSize();
  ctx.fillStyle = color_to_style(label.getColor());
  ctx.font = size + "px arial";
  ctx.fillText(label.getText(), x, y + size);
}
