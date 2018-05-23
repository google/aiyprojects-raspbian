#!/bin/bash

# This script compiles messages.proto to Python and JavaScript. It depends
# on npm, browserify and google-protobuf.
# Install node, which ships with npm, then from this folder run:
# npm install -g browserify
# npm install google-protobuf@3.5.0
# This script can then be executed to compile the protobufs.

protoc --python_out=. messages.proto
protoc --js_out=import_style=commonjs,binary:. messages.proto
browserify messages_pb.js -o ../assets/proto.js
rm messages_pb.js
