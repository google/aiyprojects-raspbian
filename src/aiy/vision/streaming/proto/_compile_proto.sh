#!/bin/bash

# This script compiles proto/messages.proto to Python and JavaScript. It de

protoc --python_out=. messages.proto

protoc --js_out=import_style=commonjs,binary:. messages.proto
browserify messages_pb.js -o ../assets/proto.js
