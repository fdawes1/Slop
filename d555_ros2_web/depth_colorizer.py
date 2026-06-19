#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import message_filters
import cv2
import numpy as np
from cv_bridge import CvBridge

CAMERA = 'd555_261422303060'
NS = f'/cameras/{CAMERA}'

DEPTH_MIN_MM = 300    # ignore pixels closer than 0.3 m (noise)
DEPTH_MAX_MM = 8000   # clip at 8 m

class DepthColorizer(Node):
    def __init__(self):
        super().__init__('depth_colorizer')
        self.bridge = CvBridge()

        self.pub_overlay = self.create_publisher(Image, f'{NS}/aligned_depth_to_color/image_colorized', 10)
        self.pub_depth   = self.create_publisher(Image, f'{NS}/depth/image_colorized', 10)

        sub_color = message_filters.Subscriber(self, Image, f'{NS}/color/image_raw')
        sub_align = message_filters.Subscriber(self, Image, f'{NS}/aligned_depth_to_color/image_raw')
        sync = message_filters.ApproximateTimeSynchronizer([sub_color, sub_align], queue_size=5, slop=0.05)
        sync.registerCallback(self._overlay_cb)

        self.create_subscription(Image, f'{NS}/depth/image_rect_raw', self._depth_cb, 10)

    def _colorize_depth(self, depth16):
        valid = (depth16 >= DEPTH_MIN_MM) & (depth16 <= DEPTH_MAX_MM)
        norm = np.zeros_like(depth16, dtype=np.uint8)
        if valid.any():
            vals = depth16[valid]
            # Percentile normalization: ignore bottom/top 2% so objects at any distance look useful
            lo = int(np.percentile(vals, 2))
            hi = int(np.percentile(vals, 98))
            if hi > lo:
                clipped = np.clip(depth16.astype(np.int32), lo, hi)
                norm[valid] = ((clipped[valid] - lo) / (hi - lo) * 255).astype(np.uint8)
        return cv2.applyColorMap(norm, cv2.COLORMAP_TURBO)

    def _overlay_cb(self, color_msg, depth_msg):
        color = self.bridge.imgmsg_to_cv2(color_msg, desired_encoding='bgr8')
        depth = self.bridge.imgmsg_to_cv2(depth_msg, desired_encoding='passthrough')
        colored_depth = self._colorize_depth(depth)

        valid_mask = ((depth >= DEPTH_MIN_MM) & (depth <= DEPTH_MAX_MM)).astype(np.float32)[:, :, np.newaxis]
        alpha = 0.45
        blended = (color.astype(np.float32) * (1.0 - alpha * valid_mask) +
                   colored_depth.astype(np.float32) * (alpha * valid_mask)).astype(np.uint8)

        out = self.bridge.cv2_to_imgmsg(blended, encoding='bgr8')
        out.header = color_msg.header
        self.pub_overlay.publish(out)

    def _depth_cb(self, msg):
        depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        colored = self._colorize_depth(depth)
        out = self.bridge.cv2_to_imgmsg(colored, encoding='bgr8')
        out.header = msg.header
        self.pub_depth.publish(out)

def main():
    rclpy.init()
    rclpy.spin(DepthColorizer())
    rclpy.shutdown()

if __name__ == '__main__':
    main()
