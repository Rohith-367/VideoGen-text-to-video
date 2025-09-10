import time
import os
import tempfile
import zipfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, ImageClip,
                            TextClip, VideoFileClip)
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
import requests
import re

def get_imagemagick_version():
    try:
        output = subprocess.check_output(['magick', '-version']).decode()
        match = re.search(r'Version: ImageMagick (\d+)\.(\d+)\.(\d+)', output)
        if match:
            return tuple(map(int, match.groups()))
        return None
    except:
        return None

def create_text_clip(text, fontsize=100, color="white", stroke_width=3, stroke_color="black", method="label"):
    """Create a text clip using direct ImageMagick commands for version 7.x"""
    try:
        # Create a temporary file for the text image
        temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_img.close()
        
        # Construct ImageMagick command for version 7.x
        cmd = [
            'magick',
            '-background', 'transparent',
            '-fill', color,
            '-font', 'Arial',
            '-pointsize', str(fontsize),
            '-stroke', stroke_color,
            '-strokewidth', str(stroke_width),
            '-gravity', 'center',
            'label:' + text,
            temp_img.name
        ]
        
        # Execute the command
        subprocess.run(cmd, check=True)
        
        # Create ImageClip from the generated image
        clip = ImageClip(temp_img.name)
        
        # Clean up the temporary file
        try:
            os.unlink(temp_img.name)
        except:
            pass  # Ignore cleanup errors
            
        return clip
    except Exception as e:
        print(f"Error creating text clip: {str(e)}")
        raise

def download_file(url, filename):
    with open(filename, 'wb') as f:
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        f.write(response.content)

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    # Special handling for ImageMagick on Windows
    if platform.system() == "Windows" and program_name == "magick":
        # First try the PATH
        program_path = search_program(program_name)
        if program_path:
            return program_path
            
        # Then try default installation path
        default_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
        if os.path.exists(default_path):
            return default_path
    
    return search_program(program_name)

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server, output_path=None):
    # Use provided output path or default
    OUTPUT_FILE_NAME = output_path if output_path else "rendered_video.mp4"
    
    # Ensure output directory exists
    output_dir = os.path.dirname(OUTPUT_FILE_NAME)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Set ImageMagick path based on platform and version
    if platform.system() == "Windows":
        magick_path = search_program("magick")
        if not magick_path:
            magick_path = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"
    else:
        magick_path = get_program_path("magick") or '/usr/bin/convert'
    
    print(f"ImageMagick path: {magick_path}")
    if os.path.exists(magick_path):
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        print(f"Warning: ImageMagick not found at {magick_path}")
    
    temp_files = []  # Keep track of temporary files for cleanup
    visual_clips = []
    
    try:
        for (t1, t2), video_url in background_video_data:
            # Download the video file
            video_filename = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            temp_files.append(video_filename)  # Add to cleanup list
            download_file(video_url, video_filename)
            
            # Create VideoFileClip from the downloaded file
            video_clip = VideoFileClip(video_filename)
            video_clip = video_clip.set_start(t1)
            video_clip = video_clip.set_end(t2)
            visual_clips.append(video_clip)
        
        audio_clips = []
        audio_file_clip = AudioFileClip(audio_file_path)
        audio_clips.append(audio_file_clip)

        # Use our custom text clip creation for ImageMagick 7.x
        for (t1, t2), text in timed_captions:
            try:
                text_clip = create_text_clip(
                    text=text,
                    fontsize=100,
                    color="white",
                    stroke_width=3,
                    stroke_color="black"
                )
                text_clip = text_clip.set_start(t1)
                text_clip = text_clip.set_end(t2)
                text_clip = text_clip.set_position(("center", 800))
                visual_clips.append(text_clip)
            except Exception as e:
                print(f"Warning: Failed to create text clip: {str(e)}")
                continue

        video = CompositeVideoClip(visual_clips)
        
        if audio_clips:
            audio = CompositeAudioClip(audio_clips)
            video.duration = audio.duration
            video.audio = audio

        print(f"Writing video to: {OUTPUT_FILE_NAME}")
        video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')
        
    finally:
        # Clean up downloaded files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as e:
                print(f"Warning: Failed to remove temporary file {temp_file}: {e}")

    return OUTPUT_FILE_NAME
