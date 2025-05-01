import re
from gemini_api import gemini_generate_content

# Build a strict prompt for Gemini to avoid preambles/explanations
def build_gemini_prompt(topic: str) -> str:
    return (
        f"Write a complete, ready-to-post Telegram channel post about: {topic}. "
        "Use only supported Telegram HTML tags. Do NOT include any explanations, tag guides, or preambles. "
        "Do NOT explain which tags you used. Do NOT include any notes, explanations, or instructions. "
        "Only output the post content for the channel."
    )

# Clean up LLM output: remove explanations, tag guides, and preambles
def clean_gemini_output(text: str) -> str:
    # Remove lines that look like explanations, tag guides, or markdown artifacts
    lines = text.splitlines()
    filtered = []
    for line in lines:
        l = line.strip()
        if not l:
            filtered.append("")
            continue
        # Remove lines with explanations, tag guides, or markdown artifacts
        if re.search(r'(Explanation|HTML Tags Used|Important Considerations|Note that|for Telegram|^`{3,}|^\*\*|^\-|^\#|^\[)', l, re.IGNORECASE):
            continue
        if l.lower().startswith("okay") or l.lower().startswith("here's") or l.lower().startswith("here is"):
            continue
        filtered.append(l)
    cleaned = "\n".join(filtered)
    # Remove multiple blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# Main function to get a clean post for a topic
async def get_clean_gemini_post(topic: str) -> str:
    prompt = build_gemini_prompt(topic)
    raw = await gemini_generate_content(prompt)
    return clean_gemini_output(raw)
