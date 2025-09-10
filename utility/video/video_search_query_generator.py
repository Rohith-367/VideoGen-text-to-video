from openai import OpenAI
import os
import json
import re
from datetime import datetime
from utility.utils import log_response,LOG_TYPE_GPT

if len(os.environ.get("GROQ_API_KEY")) > 30:
    from groq import Groq
    # model = "llama3-70b-8192"
    model  = "llama-3.3-70b-versatile"
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
        )
else:
    model = "gpt-4"  # Fixed model name
    OPENAI_API_KEY = os.environ.get('OPENAI_KEY')
    client = OpenAI(api_key=OPENAI_API_KEY)

log_directory = ".logs/gpt_logs"

prompt = """# Instructions

Given a video script and timed captions, generate search keywords for background videos. Follow these rules:

1. Each time segment should have TWO specific, visually descriptive keywords for variety
2. Keywords must be:
   - In English and visually concrete (e.g., "running cheetah", not "speed")
   - Highly specific and detailed (e.g., "aerial view mountain lake" instead of just "mountain")
   - Related to the actual content/context of the script
   - Diverse to avoid repetition
3. Each segment should be 3-5 seconds long for smoother transitions
4. Time segments must be consecutive and cover the entire video
5. Format must be a valid JSON array: [[[start_time, end_time], ["keyword1", "keyword2"]], ...]

Example good output:
[
  [[0, 4], ["aerial view ocean waves", "coastal cliff sunset"]],
  [[4, 8], ["snow capped mountain peak", "alpine forest landscape"]],
  [[8, 12], ["busy city intersection timelapse", "modern skyscraper district"]]
]

Guidelines for keywords:
- GOOD: "drone shot rainforest canopy", "slow motion waterfall cascade", "urban street night traffic"
- BAD: "nature", "city", "technology" (too generic)
- BAD: "beautiful scene" (not visually specific)
- BAD: "happiness" (abstract concept)
- BAD: Multiple unrelated keywords

Your response must be ONLY the JSON array, nothing else.
"""

def clean_json_string(json_str):
    """Clean and validate JSON string"""
    # Remove any non-JSON content
    try:
        # Find the first '[' and last ']'
        start = json_str.find('[')
        end = json_str.rfind(']') + 1
        if start == -1 or end == 0:
            raise ValueError("No valid JSON array found")
        
        json_str = json_str[start:end]
        
        # Clean up common formatting issues
        json_str = json_str.replace("'", '"')  # Replace single quotes with double quotes
        json_str = re.sub(r'\s+', ' ', json_str)  # Normalize whitespace
        
        # Remove any trailing commas before closing brackets
        json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)
        
        # Try to parse the JSON to validate it
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # If there's still an error, try to clean up any trailing content
            if "Extra data" in str(e):
                # Find the position of the error
                pos = e.pos
                # Truncate the string at the error position
                json_str = json_str[:pos]
                # Try parsing again
                data = json.loads(json_str)
        
        # Validate format
        if not isinstance(data, list):
            raise ValueError("Root must be an array")
            
        for item in data:
            if not isinstance(item, list) or len(item) != 2:
                raise ValueError("Each item must be [time_range, keywords]")
            if not isinstance(item[0], list) or len(item[0]) != 2:
                raise ValueError("Time range must be [start, end]")
            if not isinstance(item[1], list) or not all(isinstance(k, str) for k in item[1]):
                raise ValueError("Keywords must be a list of strings")
            # Ensure times are numbers
            item[0][0] = float(item[0][0])
            item[0][1] = float(item[0][1])
        
        return json.dumps(data)  # Return a properly formatted JSON string
    except Exception as e:
        print(f"JSON cleaning error: {str(e)}")
        print(f"Original string: {json_str}")
        raise

def getVideoSearchQueriesTimed(script, captions_timed):
    if not captions_timed:
        print("No captions provided")
        return None
        
    try:
        end = captions_timed[-1][0][1]
        response = call_OpenAI(script, captions_timed)
        
        # Clean and parse JSON
        cleaned_json = clean_json_string(response)
        result = json.loads(cleaned_json)
        
        # Process the result to flatten the keywords and ensure no duplicates
        processed_result = []
        used_keywords = set()
        
        for time_segment, keywords in result:
            filtered_keywords = []
            for keyword in keywords:
                if keyword.lower() not in used_keywords:
                    filtered_keywords.append(keyword)
                    used_keywords.add(keyword.lower())
            
            if filtered_keywords:
                # Use the first non-duplicate keyword
                processed_result.append([time_segment, filtered_keywords[0]])
        
        # Validate time coverage
        if processed_result and processed_result[-1][0][1] != end:
            print(f"Warning: Generated segments don't cover full duration. Expected end: {end}, Got: {processed_result[-1][0][1]}")
        
        return processed_result
    except Exception as e:
        print(f"Error in video search query generation: {str(e)}")
        return None

def call_OpenAI(script, captions_timed):
    user_content = f"""Script: {script}
Timed Captions: {json.dumps(captions_timed)}"""
    
    print("Sending request with content:", user_content)
    
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.7,  # Lower temperature for more consistent formatting
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content}
            ]
        )
        
        text = response.choices[0].message.content.strip()
        print("Received response:", text)
        
        log_response(LOG_TYPE_GPT, script, text)
        return text
    except Exception as e:
        print(f"API call error: {str(e)}")
        raise

def merge_empty_intervals(segments):
    if not segments:
        return []
        
    merged = []
    i = 0
    while i < len(segments):
        interval, url = segments[i]
        if url is None:
            # Find consecutive None intervals
            j = i + 1
            while j < len(segments) and segments[j][1] is None:
                j += 1
            
            # Merge consecutive None intervals with the previous valid URL
            if i > 0:
                prev_interval, prev_url = merged[-1]
                if prev_url is not None and prev_interval[1] == interval[0]:
                    merged[-1] = [[prev_interval[0], segments[j-1][0][1]], prev_url]
                else:
                    merged.append([interval, prev_url])
            else:
                merged.append([interval, None])
            
            i = j
        else:
            merged.append([interval, url])
            i += 1
    
    return merged