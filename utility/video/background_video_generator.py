import os
import requests
from utility.utils import log_response, LOG_TYPE_PEXEL

PEXELS_API_KEY = os.environ.get('PEXELS_KEY')


def search_videos(query_string, orientation_landscape=False):
    url = "https://api.pexels.com/videos/search"
    headers = {
        "Authorization": PEXELS_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    params = {
        "query": query_string,
        "orientation": "landscape" if orientation_landscape else "portrait",
        "per_page": 25,
        "min_duration": 3,
        "max_duration": 20,
        "size": "large"
    }
    response = requests.get(url, headers=headers, params=params)
    json_data = response.json()
    log_response(LOG_TYPE_PEXEL, query_string, json_data)
    return json_data


def getBestVideo(query_string, orientation_landscape=False, used_vids=None):
    if used_vids is None:
        used_vids = []

    vids = search_videos(query_string, orientation_landscape)
    if not vids.get('videos'):
        print(f"No videos found for query: {query_string}")
        return None

    videos = vids['videos']

    # Define target dimensions
    target_w, target_h = (1920, 1080) if orientation_landscape else (1080, 1920)
    target_ratio = target_w / target_h
    ratio_tolerance = 0.05

    # Filter videos by resolution, aspect ratio, duration, and HD
    filtered_videos = []
    for video in videos:
        if video['width'] < target_w or video['height'] < target_h:
            continue
        if abs((video['width'] / video['height']) - target_ratio) > ratio_tolerance:
            continue
        if video['duration'] < 3:
            continue
        hd_files = [f for f in video['video_files'] if f['quality'] == 'hd']
        if not hd_files:
            continue
        # Pick the largest HD file
        best_file = max(hd_files, key=lambda f: f['width'] * f['height'])
        filtered_videos.append((video, best_file))

    if not filtered_videos:
        print(f"No suitable quality videos found for query: {query_string}")
        # Try alternative queries
        alternative_queries = [
            f"cinematic {query_string}",
            f"professional {query_string}",
            f"beautiful {query_string}",
            f"{query_string} scene",
            f"{query_string} footage"
        ]
        for alt_query in alternative_queries:
            url = getBestVideo(alt_query, orientation_landscape, used_vids)
            if url:
                return url
        return None

    # Sort by duration closeness to 15s and resolution
    def quality_score(item):
        video, file = item
        duration_score = 1 - min(1.0, abs(15 - video['duration']) / 15)
        res_score = (file['width'] * file['height']) / (target_w * target_h)
        return duration_score + 0.5 * res_score

    sorted_videos = sorted(filtered_videos, key=quality_score, reverse=True)

    # Pick first unused video
    for video, file in sorted_videos:
        file_key = file['link'].split('.hd')[0]
        if file_key not in used_vids:
            used_vids.append(file_key)
            return file['link']

    print(f"No unused videos found for query: {query_string}")
    return None


def generate_video_url(timed_video_searches,orientation_landscape, video_server="pexel"):
    timed_video_urls = []
    if video_server == "pexel":
        used_links = []
        for (t1, t2), search_terms in timed_video_searches:
            url = None
            if isinstance(search_terms, list):
                for query in search_terms:
                    url = getBestVideo(query, orientation_landscape, used_vids=used_links)
                    if url:
                        used_links.append(url.split('.hd')[0])
                        break
            else:
                url = getBestVideo(search_terms, orientation_landscape, used_vids=used_links)
                if url:
                    used_links.append(url.split('.hd')[0])

            if url:
                timed_video_urls.append([[t1, t2], url])
            else:
                print(f"Warning: Could not find suitable video for time segment {t1}-{t2}")
    else:
        from some_module import get_images_for_video  # Replace with your actual function
        timed_video_urls = get_images_for_video(timed_video_searches)

    return timed_video_urls


# ****************************************************

