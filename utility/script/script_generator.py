
import os
import json
from openai import OpenAI

# Determine client and model
if len(os.environ.get("GROQ_API_KEY") or "") > 30:
    from groq import Groq
    # model = "llama3-70b-8192"
    model  = "llama-3.3-70b-versatile"
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
else:
    model = "gpt-4o"
    client = OpenAI(api_key=os.environ["OPENAI_KEY"])

def generate_script(topic):
    prompt = (
        """You are a seasoned content writer for a YouTube Shorts channel, specializing in facts videos.
        Each script should be under 50 seconds (under 140 words), and extremely engaging.

        For example, if asked for:
        Weird facts
        You’d write something like:
        {"script": "Weird facts you don't know: ..."}

        Now generate the best short script for the user's topic.
        Only respond with a pure JSON object like:
        {"script": "..." }
        """
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": topic}
        ]
    )

    content = response.choices[0].message.content.strip()

    # 🔧 Clean up: remove code fences and invalid characters
    if content.startswith("```json") or content.startswith("```"):
        content = content.split("```")[-1].strip()

    try:
        return json.loads(content)["script"]
    except json.JSONDecodeError as e:
        print("Raw response (will sanitize):", content)
        # Try to manually extract a valid JSON object
        try:
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            clean_json = content[json_start:json_end]
            return json.loads(clean_json)["script"]
        except Exception as e:
            raise RuntimeError(f"Failed to parse script JSON:\n{content}") from e
