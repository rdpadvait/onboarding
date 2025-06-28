# onboarding
Download and Generate stitched clips from Session links

## Setup Instructions

### 1. Install ffmpeg
This project requires the `ffmpeg` command-line tool.

If you are on macOS and have [Homebrew](https://brew.sh/) installed, you can install it by running:
```sh
brew install ffmpeg
```
For other operating systems, please see the official [ffmpeg download page](https://ffmpeg.org/download.html).

### 2. Create and activate Python virtual environment
It is recommended to use a virtual environment to manage project dependencies.

```sh
python3 -m venv onboarding
source onboarding/bin/activate
```
After running the `source` command, your shell prompt should indicate that you are in the `(onboarding)` environment.

### 3. Install Python dependencies
With the virtual environment activated, install the required Python packages:
```sh
pip install ffmpeg-python
```
