import os
import re
import json
from pymediainfo import MediaInfo
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_FILE = "media_cache.json"

class MediaFileHandler(FileSystemEventHandler):
    """Event handler to process new media files in real-time."""
    
    def __init__(self, movies_output_dir, shows_output_dir, cache):
        self.movies_output_dir = movies_output_dir
        self.shows_output_dir = shows_output_dir
        self.cache = cache
        self.executor = ThreadPoolExecutor(max_workers=8)  # Adjust number of threads as needed

    def on_created(self, event):
        """Handle event when a new file is created."""
        if not event.is_directory and self.is_media_file(event.src_path):
            media_file = event.src_path
            print(f"New file detected: {media_file}")
            self.process_file(media_file)
    
    def is_media_file(self, file_path):
        """Check if the file is a valid media file based on extension."""
        media_extensions = ('.mp4', '.mkv', '.avi', '.mov')
        return file_path.lower().endswith(media_extensions)

    def process_file(self, media_file):
        """Submit the media file for processing if it's not already in cache."""
        if media_file not in self.cache:
            print(f"Processing new file: {media_file}")
            self.executor.submit(self._process_media_file, media_file)
        else:
            print(f"File already processed: {media_file}. Skipping...")

    def _process_media_file(self, media_file):
        """Process a single media file, extracting audio languages and creating symlinks."""
        # Extract audio languages
        audio_languages = extract_audio_languages(media_file)

        if not audio_languages:
            print(f"No audio language found for {media_file}. Skipping...")
            return

        # Determine if the media file is from 'movies' or 'shows'
        if '/movies/' in media_file:
            base_output_dir = self.movies_output_dir
        elif '/shows/' in media_file:
            base_output_dir = self.shows_output_dir
        else:
            print(f"Unknown category for {media_file}. Skipping...")
            return

        # Cleaned filename for the symlink
        cleaned_filename = os.path.basename(media_file)
        cleaned_filename = re.sub(r'.*(1tamilblasters|1tamilmv|tamilblasters|torrenting).*?-\s*', '', cleaned_filename, flags=re.IGNORECASE).strip()

        for language in audio_languages:
            lang_dir = os.path.join(base_output_dir, language)
            os.makedirs(lang_dir, exist_ok=True)
            dest_path = os.path.join(lang_dir, cleaned_filename)
            create_symlink(media_file, dest_path)

        # Add file to cache after processing
        self.cache[media_file] = True
        save_cache(self.cache)

def load_cache():
    """Load the cache from a JSON file if it exists."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    """Save the cache to a JSON file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

def extract_audio_languages(file_path):
    """Extract audio languages from the media file using MediaInfo."""
    media_info = MediaInfo.parse(file_path)
    languages = set()
    for track in media_info.tracks:
        if track.track_type == "Audio" and track.language:
            languages.add(track.language)
    return list(languages)

def create_symlink(src, dest):
    """Create a symlink from src to dest if it doesn't already exist."""
    try:
        if not os.path.exists(dest):
            os.symlink(src, dest)
            print(f"Created symlink: {dest}")
        else:
            print(f"Symlink already exists: {dest}")
    except Exception as e:
        print(f"Error creating symlink for {src}: {e}")

def start_watching_directories(input_directories, movies_output_dir, shows_output_dir, cache):
    """Set up watchdog to monitor directories for new media files."""
    event_handler = MediaFileHandler(movies_output_dir, shows_output_dir, cache)
    observer = Observer()

    # Watch each directory for file changes
    for directory in input_directories:
        observer.schedule(event_handler, directory, recursive=True)

    # Start observer in the background
    observer.start()
    try:
        print("Watching directories for new media files...")
        while True:
            # Keep running the observer
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    # Define your directories
    input_directories = [
        '/mnt/zurg/movies',  # Movies source folder
        '/mnt/zurg/shows'    # Shows source folder
    ]
    movies_output_directory = '/mnt/xio/movies'  # Movies destination folder
    shows_output_directory = '/mnt/xio/shows'    # Shows destination folder

    # Load cache
    cache = load_cache()

    # Start watching directories
    start_watching_directories(input_directories, movies_output_directory, shows_output_directory, cache)

if __name__ == "__main__":
    main()