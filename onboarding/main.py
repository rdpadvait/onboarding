import os
import ffmpeg
import yt_dlp
import pandas as pd
import numpy as np
import cv2
import shutil

def crop_to_square_with_face_detection(input_path, output_path):
    """
    Crops a video to a square (1:1) aspect ratio, dynamically keeping a detected face in the center of each frame.
    If the video is already square or portrait, it is copied without changes.
    """
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream is None:
            print("No video stream found.")
            raise ValueError("No video stream in file")
        
        width = int(video_stream['width'])
        height = int(video_stream['height'])
        fps = eval(video_stream.get('r_frame_rate', '30/1'))

    except ffmpeg.Error as e:
        print(f"Error probing video: {e.stderr.decode()}")
        raise

    # Desired square aspect ratio
    new_width = height

    if new_width >= width:
        print("Video is already square or portrait, skipping crop.")
        shutil.copy(input_path, output_path)
        return

    # Load face detector
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        raise IOError("Unable to load the face cascade classifier xml file")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video file {input_path}")

    # Temporary path for video without audio
    temp_video_path = output_path + ".tmp.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (new_width, height))

    # Cropping parameters
    current_crop_x = (width - new_width) // 2
    # Define a safe zone within the cropped frame (e.g., middle 50%)
    safe_zone_padding = new_width * 0.25
    safe_zone_start = safe_zone_padding
    safe_zone_end = new_width - safe_zone_padding
    # Number of consecutive frames face must be out of bounds to trigger a re-crop
    recrop_persistence_frames = int(fps * 3)
    out_of_bounds_counter = 0
    ideal_crop_x = current_crop_x

    print("Starting dynamic crop with face detection...")

    frame_number = 0
    detection_interval = max(1, int(fps / 10))  # Detect at most 10 times per second

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Only run face detection periodically
        if frame_number % detection_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)

            if len(faces) > 0:
                x, y, w, h = faces[0]  # Use the first detected face
                face_center_x = x + w // 2

                # Calculate face position within the current crop
                face_center_in_crop = face_center_x - current_crop_x

                # Check if face is outside the safe zone
                if not (safe_zone_start < face_center_in_crop < safe_zone_end):
                    # Calculate the ideal crop position to re-center the face
                    new_ideal_crop_x = face_center_x - new_width // 2
                    # Clamp crop_x to be within video bounds
                    new_ideal_crop_x = max(0, min(new_ideal_crop_x, width - new_width))

                    # Trigger change only if shift is significant
                    if abs(new_ideal_crop_x - current_crop_x) > (0.4 * width):
                        ideal_crop_x = new_ideal_crop_x
                        out_of_bounds_counter += detection_interval
                    else:
                        # Not a big enough shift, reset counter
                        out_of_bounds_counter = 0
                else:
                    # Face is inside the safe zone, reset counter
                    out_of_bounds_counter = 0
            else:
                # No face detected, assume it's in a good position
                out_of_bounds_counter = 0

        # If the face has been consistently out of bounds, update the crop position
        if out_of_bounds_counter >= recrop_persistence_frames:
            current_crop_x = ideal_crop_x
            out_of_bounds_counter = 0  # Reset after adjusting

        # Use integer for slicing
        crop_x = current_crop_x
        
        cropped_frame = frame[:, crop_x : crop_x + new_width]
        out.write(cropped_frame)

        frame_number += 1

    cap.release()
    out.release()
    print("Dynamic crop finished. Merging audio...")

    try:
        input_video = ffmpeg.input(temp_video_path)
        input_audio = ffmpeg.input(input_path).audio
        (
            ffmpeg
            .output(input_video, input_audio, output_path, acodec='copy')
            .run(overwrite_output=True, quiet=True)
        )
        print("Audio merged successfully.")
    except ffmpeg.Error as e:
        print(f"Error merging audio: {e.stderr.decode()}")
        # If audio merge fails, copy the silent video as a fallback
        shutil.copy(temp_video_path, output_path)
    finally:
        # Clean up temporary file
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)

def process_csv(input_file='input.csv'):
    """
    Processes a CSV file to download and cut video clips.
    """
    downloaded_videos = {}  # Cache for {video_link: path}
    cropped_videos = {}  # Cache for {video_link: cropped_path}

    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        return

    try:
        df = pd.read_csv(input_file, encoding='utf-8', header=0)
        df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]
        if 'link' in df.columns:
            df = df.rename(columns={'link': 'video_link'})

    except Exception as e:
        print(f"Error reading or processing CSV file: {e}")
        return

    # Forward fill title and video link
    for col in ['title', 'video_link']:
        if col in df.columns:
            df[col] = df[col].replace(r'^\s*$', np.nan, regex=True)
            df[col] = df[col].ffill()

    # Drop rows that are still missing essential data after filling
    essential_cols = ['title', 'video_link', 'topic', 'start', 'end']
    df.dropna(subset=[col for col in essential_cols if col in df.columns], inplace=True)

    for index, row in df.iterrows():
        title = str(row.get('title', '')).strip()
        video_link = str(row.get('video_link', '')).strip()
        topic = str(row.get('topic', '')).strip()
        start_time = str(row.get('start', '')).strip()
        end_time = str(row.get('end', '')).strip()

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).strip()
        if not safe_title:
            print(f"Warning: Could not generate a valid directory name from title '{title}'. Using 'default_video_title'.")
            safe_title = "default_video_title"
        output_dir = os.path.join('output', safe_title)
        os.makedirs(output_dir, exist_ok=True)

        downloaded_video_path = downloaded_videos.get(video_link)

        if not downloaded_video_path or not os.path.exists(downloaded_video_path):
            ydl_opts = {
                'outtmpl': os.path.join(output_dir, 'full_video.%(ext)s'),
                'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]/best[height<=480]',
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    print(f"Downloading video from: {video_link}")
                    info = ydl.extract_info(video_link, download=True)
                    downloaded_video_path = ydl.prepare_filename(info)
                    downloaded_videos[video_link] = downloaded_video_path
                    print(f"Downloaded to: {downloaded_video_path}")
                except yt_dlp.utils.DownloadError as e:
                    print(f"Error downloading {video_link}: {e}")
                    continue
        else:
            print(f"Using cached video: {downloaded_video_path}")

        if not downloaded_video_path or not os.path.exists(downloaded_video_path):
            print(f"Failed to get video for {video_link}")
            continue

        video_to_clip_path = cropped_videos.get(video_link)
        if not video_to_clip_path or not os.path.exists(video_to_clip_path):
            squarish_video_path = os.path.join(output_dir, 'full_video_squarish.mp4')
            print(f"Creating squarish version of {video_link}")
            try:
                crop_to_square_with_face_detection(downloaded_video_path, squarish_video_path)
                print(f"Successfully created squarish video: {squarish_video_path}")
                video_to_clip_path = squarish_video_path
                cropped_videos[video_link] = video_to_clip_path
            except Exception as e:
                print(f"Failed to crop video to square: {e}. Using original video for clipping.")
                video_to_clip_path = downloaded_video_path
        else:
            print(f"Using cached squarish video: {video_to_clip_path}")

        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).strip()
        if not safe_topic:
            print(f"Warning: Could not generate a valid clip name from topic '{topic}'. Using a default name.")
            safe_topic = f"clip_{index}"
        output_clip_path = os.path.join(output_dir, f"{safe_topic}.mp4")

        print(f"Creating clip: {output_clip_path} from {start_time} to {end_time}")
        try:
            (
                ffmpeg
                .input(video_to_clip_path, ss=start_time, to=end_time)
                .output(output_clip_path, c='copy')
                .run(overwrite_output=True, quiet=True)
            )
            print(f"Successfully created clip: {output_clip_path}")
        except ffmpeg.Error as e:
            print(f"Stream copy failed. Retrying with re-encoding... Error: {e.stderr.decode()}")
            try:
                (
                    ffmpeg
                    .input(video_to_clip_path, ss=start_time, to=end_time)
                    .output(output_clip_path)
                    .run(overwrite_output=True, quiet=True)
                )
                print(f"Successfully created clip with re-encoding: {output_clip_path}")
            except ffmpeg.Error as e2:
                print(f"Failed to cut video for topic '{topic}': {e2.stderr.decode()}")

def main():
    process_csv('input.csv')

if __name__ == '__main__':
    main()
