# Streaming protocol specification

Server streams data to clients. There is only one server and there can be zero
or more connected clients.

## Messages from Server to Client (ClientBound)

Each server streaming session must start with `ClientBound{start}` and
stop with `ClientBound{stop}` messages. Interleaved  `ClientBound{video}`
and `ClientBound{overlay}` are allowed in between:

```
-> ClientBound{start={width=<width>, height=<height>}}

-> ClientBound{video} or ClientBound{overlay}

-> ClientBound{stop}
```

Each video message contains one or more H264 encoded NAL units. Partial NAL
units are not allowed. The first NAL unit must be SPS (Sequence Parameter Set),
the second one is IDR. Concatenation of all video messages should produce a
valid H264 bitstream. All subsequent SPS NAL units must contain the same
information as the first one.

Overlay messages are allowed at any time. You can think that there are two
logical streams during the session: video stream and stream of overlays.
Each overlay message contains SVG image which is drawn on top of the video.

## Messages from Client to Server (ServerBound)

Client can control the server by sending `ServerBound{stream_control}` messages.
There are only two allowed: `ServerBound{stream_control={enabled=true}}` to
start streaming and `ServerBound{stream_control={enabled=false}}` to stop
streaming. Server could ignore these messages if it is already in the requested
state.

```
<- ServerBound{stream_control={enabled=true}}


<- ServerBound{stream_control={enabled=false}}

```

## Example

From the Server's point of view ordered by absolute time:

```
<- ServerBound{stream_control={enabled=true}}
-> ClientBound{start={width=720, height=480}}
-> ClientBound{overlay={svg=<DATA>}
-> ClientBound{video={<SPS>}}  # First NAL unit in video stream
-> ClientBound{overlay={svg=<DATA>}
-> ClientBound{video={<IDR>}}  # Second NAL unit in video stream
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{overlay={svg=<DATA>}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{overlay={svg=<DATA>}
-> ClientBound{video={<SPS>}}  # The same as the first SPS NAL unit.
-> ClientBound{video={<IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{overlay={svg=<DATA>}
<- ServerBound{stream_control={enabled=false}}
-> ClientBound{video={<IDR>}}
-> ClientBound{video={<NON-IDR>}}
-> ClientBound{stop}
```

## References

[Protocol Buffers](https://developers.google.com/protocol-buffers/)
[H264 Specification](https://www.itu.int/rec/T-REC-H.264-201704-I)
[SVG Specification](https://www.w3.org/TR/SVG11/)
