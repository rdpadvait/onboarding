# onboarding
Download and Generate stitched clips from Session links

## Setup Instructions

### 1. Install Poetry
This project uses [Poetry](https://python-poetry.org/) for dependency management. If you don't have it, follow the [official installation guide](https://python-poetry.org/docs/#installation).

### 2. Install ffmpeg
This project requires the `ffmpeg` command-line tool. The version used for development was `7.1.1_3`.

If you are on macOS and have [Homebrew](https://brew.sh/) installed, you can install it by running:
```sh
brew install ffmpeg
```
For other operating systems, please see the official [ffmpeg download page](https://ffmpeg.org/download.html).

### 3. Install Dependencies
This command will create a virtual environment and install all Python dependencies from `pyproject.toml`.
```sh
poetry install
```

### 4. Activate Virtual Environment
To work within the project's virtual environment, run:
```sh
poetry shell
```
This will spawn a new shell within the virtual environment.

### 5. Running the script
To process the `input.csv` and generate video clips, run:
```sh
poetry run process-videos
```
Make sure you have an `input.csv` file in the root of the project with columns: `title`, `video link`, `topic`, `start`, `end`. The output videos will be saved in directories named after the video titles.
