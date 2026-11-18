import json
import urllib.request

with open('/opt/gta-clips/.env') as f:
    env = dict(line.strip().split('=', 1) for line in f if '=' in line and not line.strip().startswith('#'))
key = env.get('GROQ_API_KEY', '').strip()

transcript_text = (
    "Here. Excuse me? I was thinking about shooting. You know what? I'm just gonna get a... "
    "Goddamn, I joined. I was just weak. Thank you. Now, am I actually in the spot? "
    "Let me go, drive over there real quick. Now let me really show y'all boys how I get there "
    "when I got a goddamn fish, y'all. First things first, you wanna take out your ultimate fishing rod, "
    "then you wanna go out on a day where it's beautiful, and you'll be able to do this. "
    "Look at that. Give me that. Let's see if this is still"
)

prompt = f"""You are an elite, creative viral video editor and curator specialized in Grand Theft Auto VI (GTA 6).
Analyze the following transcript from a 60-second livestream segment.

YOUR MISSION:
Find the most entertaining, hilarious, intense, scandalous, or memorable moment in this transcript that will perform well on TikTok, YouTube Shorts, and Instagram Reels.

DEEP GTA 6 KNOWLEDGE & VIBES:
Do NOT limit your search to just 5-star police chases. GTA 6 in the state of Leonida (Vice City) is full of crazy, diverse moments:
- Lucia and Jason dynamics: romantic tension, banter, relationship drama, ex-partners, arguments, trust and crime partnership.
- Vice City nightlife: Lucia dancing at clubs, partying, wild NPCs, twerking on car roofs, beach antics, luxury lifestyle.
- Stunts and chaos: stealing fighter jets from the military base, crazy car ramps, speedboat chases in the Keys, airboats in the swamp with alligators, robbing stores, weapon experiments.
- Funny Florida/Leonida humor: bizarre NPC interactions, hilarious dialogue, weird radio broadcasts, ridiculous social media moments.
- Streamer reactions: funny jokes, roasts, laughing, screaming, unexpected fails, clutch saves, genuine shock or hype.
- Random fun banter: any conversation or moment that is funny, weird, or interesting to watch!

RULES:
1. If there is a fun, interesting, funny, or action-packed moment in the transcript, extract the best 15 to 60-second clip window.
2. Only return an empty list {{"highlights": []}} if the transcript is completely empty, unintelligible noise, or pure silence.
3. Provide a score between 70 and 100 based on entertainment value, humor, or excitement.
4. Provide a punchy, click-worthy 'headline' in uppercase (3-6 words, e.g. "LUCIA DANCING AT THE CLUB 💃", "STEALING A MILITARY JET ✈️", "JASON'S WORST DECISION EVER 😂", "BRO ACCIDENTALLY JUMPED THE BRIDGE 💀").
5. Write a natural, conversational 'caption' for social media (simple, everyday words - no big english or robotic prose).
6. Provide up to 5 lowercase hashtags, always including "#gta" and "#gta6" (e.g. ["#gta", "#gta6", "#gaming", "#gtavice", "#viral"]).
7. Quote the exact spoken words from the transcript as evidence.
8. Output MUST strictly adhere to the JSON schema below.

JSON Schema:
{{
  "highlights": [
    {{
      "hook_summary": "Catchy clip title (5-10 words)",
      "headline": "LUCIA CAUGHT DANCING AT THE CLUB 💃",
      "caption": "Jason was not ready for this in Vice City!",
      "hashtags": ["#gta", "#gta6", "#gaming", "#gtavice", "#viral"],
      "facecam_position": "top_right",
      "start_second": 5.0,
      "end_second": 35.0,
      "duration_seconds": 30.0,
      "score": 88.0,
      "excitement_score": 90.0,
      "clarity_score": 85.0,
      "why_highlight": "Funny and entertaining dialogue/moment",
      "evidence_quote": "Exact transcript text",
      "safety_flags": []
    }}
  ]
}}

Transcript:
\"\"\"{transcript_text}\"\"\"

Respond with valid JSON only. Do not add markdown backticks outside JSON."""

payload = json.dumps({
    "model": "openai/gpt-oss-120b",
    "messages": [
        {"role": "system", "content": "You are a professional video clipping AI. You always respond in valid JSON."},
        {"role": "user", "content": prompt}
    ],
    "response_format": {"type": "json_object"},
    "temperature": 0.3
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.groq.com/openai/v1/chat/completions",
    data=payload,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    content = data["choices"][0]["message"]["content"]
    print("OUTPUT:")
    print(content)
