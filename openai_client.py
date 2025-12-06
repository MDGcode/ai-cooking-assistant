import os
import requests
from dotenv import load_dotenv

load_dotenv()
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
TRANSCRIBE_URL = 'https://api.openai.com/v1/audio/transcriptions'
CHAT_URL = 'https://api.openai.com/v1/chat/completions'


HEADERS = {
    'Authorization': f'Bearer {OPENAI_KEY}',
}


def transcribe_audio(filepath, model='whisper-1', language='ro'):
    """Send audio file to OpenAI transcription endpoint and return text.
    Model names may change; check OpenAI docs if this fails.
    """
    with open(filepath, 'rb') as f:
        files = {'file': (filepath, f)}
        data = {'model': model, 'language': language}
        resp = requests.post(TRANSCRIBE_URL, headers=HEADERS, files=files, data=data)
    resp.raise_for_status()
    j = resp.json()
    # typical response includes 'text'
    return j.get('text', '')



def ask_assistant(prompt, model='gpt-4o-mini', system_prompt=None, temperature=0.6):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})


    payload = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': 800,
    }
    resp = requests.post(CHAT_URL, headers={**HEADERS, 'Content-Type': 'application/json'}, json=payload)
    resp.raise_for_status()
    j = resp.json()
    # Chat completions structure usually in choices[0].message.content
    return j['choices'][0]['message']['content']