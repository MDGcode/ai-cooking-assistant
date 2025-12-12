import os
import requests
import speech_recognition as sr
from dotenv import load_dotenv

load_dotenv()
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
TRANSCRIBE_URL = 'https://api.openai.com/v1/audio/transcriptions'
CHAT_URL = 'https://api.openai.com/v1/chat/completions'


HEADERS = {
    'Authorization': f'Bearer {OPENAI_KEY}',
}


def transcribe_audio(filepath, language='ro-RO'):
    """Transcribe a local audio file using the SpeechRecognition library.
    Returns the transcribed text (or an empty string on failure).
    """
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(filepath) as source:
            audio = recognizer.record(source)
        try:
           
            text = recognizer.recognize_google(audio, language=language)
            return text
        except sr.UnknownValueError:
            print('SpeechRecognition: audio unintelligible')
            return ''
        except sr.RequestError as e:
            print(f'SpeechRecognition request failed: {e}')
            return ''
    except FileNotFoundError:
        print(f'Audio file not found: {filepath}')
        return ''
    except Exception as e:
        print(f'Unexpected error during transcription: {e}')
        return ''



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