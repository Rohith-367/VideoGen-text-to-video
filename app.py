from openai import OpenAI
import os
import edge_tts
import json
import asyncio
import whisper_timestamped as whisper
from utility.script.script_generator import generate_script
from utility.audio.audio_generator import generate_audio
from utility.captions.timed_captions_generator import generate_timed_captions
from utility.video.background_video_generator import generate_video_url
from utility.render.render_engine import get_output_media
from utility.video.video_search_query_generator import getVideoSearchQueriesTimed, merge_empty_intervals
import argparse

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Get API keys from environment variables
OPENAI_KEY = os.getenv("OPENAI_KEY")
PEXELS_KEY = os.getenv("PEXELS_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not all([OPENAI_KEY, PEXELS_KEY, GROQ_API_KEY]):
    raise ValueError("Missing required API keys in environment variables")

os.environ["OPENAI_KEY"] = OPENAI_KEY
os.environ["PEXELS_KEY"] = PEXELS_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY


def generate_video(topic, output_dir, orientation_landscape):
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        SAMPLE_FILE_NAME = os.path.join(output_dir, "audio_tts.wav")
        VIDEO_SERVER = "pexel"
        OUTPUT_VIDEO = os.path.join(output_dir, "output.mp4")

        # Generate engaging script for the topic
        response = generate_script(topic)
        print("Generated script successfully")

        # Generate audio narration
        asyncio.run(generate_audio(response, SAMPLE_FILE_NAME))
        print("Generated audio successfully")

        # Generate timed captions
        timed_captions = generate_timed_captions(SAMPLE_FILE_NAME)
        print("Generated captions successfully")

        # Generate relevant video search terms
        search_terms = getVideoSearchQueriesTimed(response, timed_captions)
        if not search_terms:
            raise ValueError("Failed to generate search terms")

        # Get background video URLs
        background_video_urls = generate_video_url(
            search_terms,
            orientation_landscape=orientation_landscape,
            video_server=VIDEO_SERVER,
        )
        if not background_video_urls:
            raise ValueError("Failed to get background videos")

        # Merge any empty intervals
        background_video_urls = merge_empty_intervals(background_video_urls)

        # Generate final video
        video = get_output_media(
            SAMPLE_FILE_NAME,
            timed_captions,
            background_video_urls,
            VIDEO_SERVER,
            output_path=OUTPUT_VIDEO,
        )
        print(f"Successfully generated video at: {OUTPUT_VIDEO}")

        return True

    except Exception as e:
        print(f"Error generating video: {str(e)}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an engaging video from a topic.")
    parser.add_argument("topic", type=str, help="The topic for the video")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory for the generated files")
    parser.add_argument("--orientation", choices=["landscape", "portrait"], default="portrait",
                        help="Orientation of videos to fetch (default: portrait)")

    args = parser.parse_args()
    orientation_landscape = args.orientation == "landscape"
    print("orientation_landscape : ",orientation_landscape)
    success = generate_video(args.topic, args.output_dir, orientation_landscape)

    if not success:
        exit(1)
