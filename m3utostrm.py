import os
import sys
import urllib.request
from http.cookiejar import CookieJar
import time
import re
import logging
from datetime import datetime
import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process XTREAM M3U files into Jellyfin-readable .strm files.')
    parser.add_argument('--moviesDirectory', type=str, required=True)
    parser.add_argument('--tvShowsDirectory', type=str, required=True)
    parser.add_argument('--m3uUrl', type=str, required=True)
    
    return parser.parse_args()

# Define the fixed M3U URL
M3U_FILE_PATH = "m3u_temp"
LOG_FILE_PATH = "m3utostrm.log"
VALID_FILE_FORMATS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v']

# Set up logging
logging.basicConfig(filename=LOG_FILE_PATH, level=logging.ERROR, format='%(asctime)s %(levelname)s: %(message)s')

def download_m3u_file(url):
    # Set up custom headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.3'
    }

    # Create a cookie jar to handle any cookies that might be required
    cookie_jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    opener.addheaders = [('User-Agent', headers['User-Agent'])]

    try:
        request = urllib.request.Request(url)
        response = opener.open(request)
        
        if response.status == 200:
            # Save the file to a temporary location
            with open(M3U_FILE_PATH, "wb") as f:
                f.write(response.read())
            return M3U_FILE_PATH
        else:
            logging.error(f"HTTP Error {response.status}: {response.reason}")
            return None

    except urllib.error.HTTPError as e:
        logging.error(f"HTTP Error: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return None

def is_file_recent(file_path, max_age_hours=24):
    """Check if the file is less than max_age_hours old."""
    if os.path.exists(file_path):
        file_age = time.time() - os.path.getmtime(file_path)
        return file_age < max_age_hours * 3600
    return False

def sanitize_filename(filename):
    """Sanitize the filename to remove invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def process_m3u_file(m3u_url, movies_folder, tv_shows_folder):
    """Process the M3U file to extract and organize media files."""
    movies_count = 0
    tv_shows_count = 0
    new_movies_count = 0
    new_tv_shows_count = 0
    existing_files = set()
    created_files = set()

    try:
        with open(m3u_url, 'r') as f:
            lines = f.readlines()

        # Create directories if they don't exist
        os.makedirs(movies_folder, exist_ok=True)
        os.makedirs(tv_shows_folder, exist_ok=True)

        # Process each line in the M3U file
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith('#EXTINF'):
                # Extract metadata from the #EXTINF line
                extinf = line
                match = re.search(r'tvg-name="([^"]+)"', extinf)
                if match:
                    tvg_name = match.group(1)
                    # Check if it's a TV show or a movie
                    tv_show_match = re.search(r'(.*?)(?: \((\d{4}(?:-\d{4})?)\))? S(\d+) E(\d+)', tvg_name)
                    movie_match = re.search(r'(.*?)(?: \((\d{4})\))?$', tvg_name)
                    if tv_show_match:
                        title = tv_show_match.group(1).strip()
                        year = tv_show_match.group(2) if tv_show_match.group(2) else "Unknown"
                        season = tv_show_match.group(3)
                        episode = tv_show_match.group(4)
                        strm_filename = sanitize_filename(f"{title} {year} S{season}E{episode}.strm")
                        target_folder = tv_shows_folder
                        tv_shows_count += 1
                    elif movie_match:
                        title = movie_match.group(1).strip()
                        year = movie_match.group(2) if movie_match.group(2) else "Unknown"
                        strm_filename = sanitize_filename(f"{title} {year}.strm")
                        target_folder = movies_folder
                        movies_count += 1
                    else:
                        logging.error(f"Unsupported tvg-name format: {tvg_name} at line {i}")
                        continue
                else:
                    logging.error(f"No tvg-name found in line: {extinf} at line {i}")
                    continue

                # Check if the next line is a URL
                if i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
                    if '://' in url_line and any(url_line.endswith(ext) for ext in VALID_FILE_FORMATS):
                        # Create a .strm file with the URL
                        strm_file_path = os.path.join(target_folder, strm_filename)
                        existing_files.add(strm_file_path)
                        if not os.path.exists(strm_file_path):
                            try:
                                with open(strm_file_path, 'w') as strm_file:
                                    strm_file.write(url_line)
                                created_files.add(strm_file_path)
                                if target_folder == movies_folder:
                                    new_movies_count += 1
                                else:
                                    new_tv_shows_count += 1
                            except Exception as e:
                                logging.error(f"Error creating .strm file: {strm_file_path} with URL: {url_line} at line {i + 1} - {e}")

        # Check for and delete .strm files that don't appear in the M3U file
        for folder in [movies_folder, tv_shows_folder]:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.endswith(".strm"):
                        file_path = os.path.join(root, file)
                        if file_path not in existing_files:
                            os.remove(file_path)
                            logging.error(f"Deleted .strm file: {file_path}")

    except Exception as e:
        logging.error(f"Error processing M3U file: {e}")

    logging.error(f"Total movies created: {movies_count}")
    logging.error(f"Total TV shows created: {tv_shows_count}")
    logging.error(f"New movies added: {new_movies_count}")
    logging.error(f"New TV shows added: {new_tv_shows_count}")
    logging.error(f"Total run time: {datetime.now() - start_time}")

def main():

    args = parse_arguments()
    movies_folder = args.moviesDirectory
    tv_shows_folder = args.tvShowsDirectory
    M3U_URL = args.m3uUrl
    """Main function to download and process the M3U file."""
    # Log the start time
    global start_time
    start_time = datetime.now()
    logging.error(f"Script started at: {start_time}")

    # Set up directories
    movies_folder = movies_folder
    tv_shows_folder = tv_shows_folder

    # Check if the M3U file is recent
    if is_file_recent(M3U_FILE_PATH):
        m3u_path = M3U_FILE_PATH
    else:
        # Download the M3U file
        m3u_path = download_m3u_file(M3U_URL)
        if not m3u_path:
            return

    # Process the M3U file
    process_m3u_file(m3u_path, movies_folder, tv_shows_folder)

if __name__ == "__main__":
    main()