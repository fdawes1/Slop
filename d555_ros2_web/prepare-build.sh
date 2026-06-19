#!/bin/bash
# Stage host's prebuilt librealsense2 2.58 (with DDS/network support) into the Docker build context.
# Run this once before `docker compose build`.
set -e

STAGE_DIR="librealsense_staged"

echo "Staging librealsense2 2.58 (with DDS) from /usr/local ..."
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR/lib/cmake" "$STAGE_DIR/include" "$STAGE_DIR/bin" "$STAGE_DIR/lib/foonathan_memory"

# Shared libraries
cp /usr/local/lib/librealsense2.so.2.58.2    "$STAGE_DIR/lib/"
cp /usr/local/lib/librealsense2-gl.so.2.58.2 "$STAGE_DIR/lib/"

# Static libs needed at build time (all realsense-related)
cp /usr/local/lib/librealdds.a              "$STAGE_DIR/lib/"
cp /usr/local/lib/librealsense-file.a       "$STAGE_DIR/lib/"
cp /usr/local/lib/librsutils.a              "$STAGE_DIR/lib/"
cp /usr/local/lib/librs_lz4.a              "$STAGE_DIR/lib/"
cp /usr/local/lib/libsqlite3_lib.a          "$STAGE_DIR/lib/"
cp /usr/local/lib/libfastrtps.a             "$STAGE_DIR/lib/"
cp /usr/local/lib/libfastcdr.a              "$STAGE_DIR/lib/"
cp /usr/local/lib/libfoonathan_memory-0.7.3.a "$STAGE_DIR/lib/"

# Symlinks
(cd "$STAGE_DIR/lib" && \
  ln -sf librealsense2.so.2.58.2    librealsense2.so.2.58 && \
  ln -sf librealsense2.so.2.58      librealsense2.so && \
  ln -sf librealsense2-gl.so.2.58.2 librealsense2-gl.so.2.58 && \
  ln -sf librealsense2-gl.so.2.58   librealsense2-gl.so)

# CMake configs
cp -r /usr/local/lib/cmake/realsense2   "$STAGE_DIR/lib/cmake/"
cp -r /usr/local/lib/cmake/fastcdr      "$STAGE_DIR/lib/cmake/"
cp -r /usr/local/lib/foonathan_memory/cmake  "$STAGE_DIR/lib/foonathan_memory/"

# Headers
cp -r /usr/local/include/librealsense2  "$STAGE_DIR/include/"
cp -r /usr/local/include/fastdds        "$STAGE_DIR/include/"
cp -r /usr/local/include/fastrtps       "$STAGE_DIR/include/"
cp -r /usr/local/include/fastcdr        "$STAGE_DIR/include/"

# Diagnostic tool
cp /usr/local/bin/rs-enumerate-devices  "$STAGE_DIR/bin/" 2>/dev/null || true

echo "Done. Now run: docker compose build --no-cache"
