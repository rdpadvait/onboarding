import os
import ffmpeg
import yt_dlp
import pandas as pd
import numpy as np

def process_csv(input_file='input.csv'):
    """
    Processes a CSV file to download and cut video clips.
    """
    downloaded_videos = {}  # Cache for {video_link: path}

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
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
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

        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).strip()
        if not safe_topic:
            print(f"Warning: Could not generate a valid clip name from topic '{topic}'. Using a default name.")
            safe_topic = f"clip_{index}"
        output_clip_path = os.path.join(output_dir, f"{safe_topic}.mp4")

        print(f"Creating clip: {output_clip_path} from {start_time} to {end_time}")
        try:
            (
                ffmpeg
                .input(downloaded_video_path, ss=start_time, to=end_time)
                .output(output_clip_path, c='copy')
                .run(overwrite_output=True, quiet=True)
            )
            print(f"Successfully created clip: {output_clip_path}")
        except ffmpeg.Error as e:
            print(f"Stream copy failed. Retrying with re-encoding... Error: {e.stderr.decode()}")
            try:
                (
                    ffmpeg
                    .input(downloaded_video_path, ss=start_time, to=end_time)
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
