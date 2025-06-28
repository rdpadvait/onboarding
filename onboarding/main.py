import csv
import os
import ffmpeg
import yt_dlp

def process_csv(input_file='input.csv'):
    """
    Processes a CSV file to download and cut video clips.
    """
    last_title = ""
    last_video_link = ""
    downloaded_videos = {}  # Cache for {video_link: path}

    if not os.path.exists(input_file):
        print(f"Error: Input file not found at {input_file}")
        return

    with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            title = row.get('title', '').strip()
            video_link = row.get('video link', '').strip()
            topic = row.get('topic', '').strip()
            start_time = row.get('start', '').strip()
            end_time = row.get('end', '').strip()

            if not title:
                title = last_title
            else:
                last_title = title

            if not video_link:
                video_link = last_video_link
            else:
                last_video_link = video_link

            if not all([title, video_link, topic, start_time, end_time]):
                print(f"Skipping row due to missing data: {row}")
                continue

            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
            output_dir = safe_title
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

            safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '_')).rstrip()
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
