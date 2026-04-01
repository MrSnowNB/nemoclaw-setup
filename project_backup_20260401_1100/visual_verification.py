#!/usr/bin/env python3
"""
Visual verification script for RICo mouth synchronization

Extracts frames from the processed video to verify mouth shapes change with visemes.
"""

import cv2
import os
import numpy as np

def extract_frames_for_verification(video_path: str, output_dir: str = "outputs/debug"):
    """Extract frames at different viseme timings for visual inspection"""

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Could not open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"🎬 Video: {total_frames} frames at {fps} FPS")

    # Extract frames at key viseme transition points
    # Based on viseme sequence: EH(0-0.75s) -> IH(0.75-1.5s) -> AH(1.5s+)
    frame_indices = [
        0,    # Start - EH viseme (smaller mouth)
        18,   # ~0.75s - transition to IH
        36,   # ~1.5s - transition to AH
        54,   # ~2.25s - still AH
        72,   # ~3.0s - still AH
    ]

    print("📸 Extracting frames for visual verification...")

    for frame_idx in frame_indices:
        if frame_idx >= total_frames:
            print(f"⚠️  Frame {frame_idx} exceeds video length ({total_frames})")
            continue

        # Seek to frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if ret:
            output_path = f"{output_dir}/viseme_verification_frame_{frame_idx:03d}.png"
            cv2.imwrite(output_path, frame)
            print(f"✅ Saved frame {frame_idx} -> {output_path}")

            # Also save a zoomed-in version of the mouth area
            height, width = frame.shape[:2]
            mouth_region = frame[int(height*0.4):int(height*0.8), int(width*0.3):int(width*0.7)]
            if mouth_region.size > 0:
                mouth_zoom_path = f"{output_dir}/mouth_zoom_frame_{frame_idx:03d}.png"
                cv2.imwrite(mouth_zoom_path, cv2.resize(mouth_region, (200, 200)))
                print(f"   👄 Mouth zoom saved -> {mouth_zoom_path}")
        else:
            print(f"❌ Failed to read frame {frame_idx}")

    cap.release()
    print(f"\n📋 Visual verification frames saved to: {output_dir}")
    print("👀 Check the images to see if mouth shapes change between frames")
    print("   - Frame 000: EH viseme (should be smaller mouth)")
    print("   - Frame 018: IH viseme (should be much smaller, darker)")
    print("   - Frame 036+: AH viseme (should be normal size)")

def compare_frames_pixel_diff(video_path: str):
    """Compare pixel differences between frames to quantify mouth changes"""

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return

    frames = []
    frame_indices = [0, 18, 36, 54]  # Key frames to compare

    # Extract frames
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append((idx, frame))

    cap.release()

    if len(frames) < 2:
        print("❌ Not enough frames extracted for comparison")
        return

    print("\n🔍 Pixel difference analysis between key frames:")

    for i in range(len(frames)-1):
        idx1, frame1 = frames[i]
        idx2, frame2 = frames[i+1]

        # Calculate difference
        diff = cv2.absdiff(frame1, frame2)
        pixel_diff = np.sum(diff)

        # Focus on mouth region
        height, width = frame1.shape[:2]
        mouth_region1 = frame1[int(height*0.4):int(height*0.8), int(width*0.3):int(width*0.7)]
        mouth_region2 = frame2[int(height*0.4):int(height*0.8), int(width*0.3):int(width*0.7)]

        if mouth_region1.size > 0 and mouth_region2.size > 0:
            mouth_diff = cv2.absdiff(mouth_region1, mouth_region2)
            mouth_pixel_diff = np.sum(mouth_diff)

            print(f"Frames {idx1}→{idx2}: Total diff={pixel_diff:,}, Mouth diff={mouth_pixel_diff:,}")
        else:
            print(f"Frames {idx1}→{idx2}: Total diff={pixel_diff:,}")

if __name__ == "__main__":
    video_path = "outputs/patent_demo_synced.mp4"

    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        exit(1)

    print("🔍 Starting visual verification of RICo mouth synchronization...")
    print("=" * 60)

    extract_frames_for_verification(video_path)
    compare_frames_pixel_diff(video_path)

    print("\n" + "=" * 60)
    print("✅ Visual verification complete!")
    print("📂 Check outputs/debug/ for extracted frames")
    print("🎯 Look for mouth shape changes between frames with different visemes")
