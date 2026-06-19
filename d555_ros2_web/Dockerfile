FROM ros:jazzy

# Install deps (NOT ros-jazzy-realsense2-camera — we build from source against DDS-enabled libs)
RUN apt-get update && apt-get install -y \
    ros-jazzy-web-video-server \
    ros-jazzy-realsense2-camera-msgs \
    python3-colcon-common-extensions \
    python3-rosdep \
    libusb-1.0-0 \
    libudev1 \
    libcap2 \
    iproute2 \
    git \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Install librealsense2 2.58 with DDS/network support (pre-staged from host Ubuntu 24.04 build)
COPY librealsense_staged/lib/    /usr/local/lib/
COPY librealsense_staged/include/ /usr/local/include/
COPY librealsense_staged/bin/    /usr/local/bin/
COPY librealsense_staged/lib/foonathan_memory/ /usr/local/lib/foonathan_memory/
RUN ldconfig

# Build realsense2_camera ROS2 package from source against the DDS-enabled librealsense2
RUN mkdir -p /ros2_ws/src && \
    git clone --depth 1 --branch 4.57.7 \
        https://github.com/IntelRealSense/realsense-ros.git \
        /ros2_ws/src/realsense-ros

RUN rosdep init 2>/dev/null || true && \
    rosdep update && \
    apt-get update && \
    bash -c "source /opt/ros/jazzy/setup.bash && \
        rosdep install --from-paths /ros2_ws/src --ignore-src -r -y \
            --skip-keys 'librealsense2'" && \
    rm -rf /var/lib/apt/lists/*

RUN bash -c "\
    source /opt/ros/jazzy/setup.bash && \
    cd /ros2_ws && \
    colcon build \
        --packages-select realsense2_camera \
        --cmake-args \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_PREFIX_PATH=/usr/local && \
    rm -rf build log"

RUN echo 'source /opt/ros/jazzy/setup.bash' >> /root/.bashrc

CMD ["bash"]
