# D555 ROS 2 Web Viewer

This package runs a RealSense D555 PoE camera via ROS 2 and exposes its image topics in a browser using `web_video_server`.

Camera details used here:

- Serial number: `261422303060`
- Camera IP: `2.2.2.101`
- Assumed host NIC IP: `2.2.2.100`

## Host network setup

Replace `enp3s0` with your actual Ethernet interface.

```bash
sudo ip addr add 2.2.2.100/24 dev enp3s0
sudo ip link set enp3s0 mtu 9000
sudo ip link set enp3s0 up
ping 2.2.2.101
```

Make sure RealSense DDS has been configured on the host:

```bash
rs-dds-config --eth-first
cat ~/.realsense-config.json
```

## First-time setup: stage librealsense2

`librealsense_staged/` is not in git — it's a local build context populated from the host's pre-built librealsense2 2.58 (with DDS/network support). Run this once before the first build, and again if you rebuild librealsense on the host:

```bash
./prepare-build.sh
```

This copies the relevant `.so`, `.a`, headers, and CMake configs from `/usr/local` into `librealsense_staged/`. Requires librealsense2 2.58 with DDS support already built and installed on the host Ubuntu machine.

## Build

```bash
docker compose build
```

## Run

```bash
docker compose up
```

## View

From the workstation:

```text
http://localhost:8090
```

From another machine that can reach the workstation's `2.2.2.100` interface:

```text
http://2.2.2.100:8090
```

Raw stream server:

```text
http://2.2.2.100:8080
```

Colour stream directly:

```text
http://2.2.2.100:8080/stream?topic=/cameras/d555_261422303060/color/image_raw&type=mjpeg
```

## Debug

```bash
docker exec -it d555_web_video_server bash
source /opt/ros/humble/setup.bash
ros2 topic list | grep d555
```

Expected topics include:

```text
/cameras/d555_261422303060/color/image_raw
/cameras/d555_261422303060/depth/image_rect_raw
/cameras/d555_261422303060/aligned_depth_to_color/image_raw
```

If the HTML loads but images are broken, check that the topic names match and that your browser can reach port `8080` on the workstation.
