import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from recorder import record_wav
from openai_client import transcribe_audio, ask_assistant
import threading
import os
from tts import speak, stop, is_speaking


ROOT_PROMPT = (
    "You are an AI cooking assistant. The user will list ingredients and ask for recipes. "
    "I want you to act as a cooking assistant that provides recipes based on the ingredients provided by the user. "
    "List some possible dishes that can be made with those ingredients and allow the user to choose one "
    "Give step-by-step cooking instructions to make a delicious dish using only those ingredients. "
    "Try to create a recipe based only on the ingredients provided by the user. "
    "Do not give all cooking instructions at once; Provide the instructions step by step so that the user can follow along easily. "
    "After each step, wait for the user to confirm they are ready for the next step before proceeding. "
    "Always respond in Romanian."
    "When the recipe is complete, always wish the user 'Poftă bună!'"
)


class App:
    def __init__(self, root):
        self.root = root
        root.title('AI Cooking Assistant')
        
        # Conversation history
        self.conversation_history = []
        
        # Track whether a recipe (step-by-step) has commenced
        self.recipe_started = False
        # Track recording/transcribing state to avoid overlap
        self.is_recording = False
        self.is_transcribing = False

        self.text = ScrolledText(root, wrap=tk.WORD, width=80, height=25)
        self.text.pack(padx=10, pady=10)

        controls = tk.Frame(root)
        controls.pack(pady=6)

        self.status = tk.Label(root, text='Idle')
        self.status.pack()

        self.record_btn = tk.Button(controls, text='Record (5s)', command=self.record_once)
        self.record_btn.pack(side=tk.LEFT, padx=4)

        self.ask_btn = tk.Button(controls, text='Transcribe & Ask', command=self.transcribe_and_ask)
        self.ask_btn.pack(side=tk.LEFT, padx=4)
        
        self.reset_btn = tk.Button(controls, text='Reset Session', command=self.reset_session)
        self.reset_btn.pack(side=tk.LEFT, padx=4)
        
        # Button to stop current TTS playback
        self.stop_tts_btn = tk.Button(controls, text='Shut up!', command=self.stop_tts)
        self.stop_tts_btn.pack(side=tk.LEFT, padx=4)

        # Next step button (disabled until a recipe starts)
        self.next_step_btn = tk.Button(controls, text='Next step', command=self.next_step, state=tk.DISABLED)
        self.next_step_btn.pack(side=tk.LEFT, padx=4)

    def append(self, who, text):
        self.text.insert(tk.END, f"{who}: {text}\n\n")
        self.text.see(tk.END)

    def record_once(self):
        def _rec():
            # Prevent starting a new recording if a transcription is in progress
            if self.is_transcribing:
                self.append('SYSTEM', 'Cannot record while transcribing')
                return
            self.is_recording = True
            try:
                # update UI
                self.status.config(text='Recording...')
                # disable transcribe button while recording
                try:
                    self.ask_btn.config(state=tk.DISABLED)
                except Exception:
                    pass
                filename = record_wav(duration=4)
                self.status.config(text=f'Recorded {filename}')
                self.append('SYSTEM', f'Recorded audio saved as {filename}')
            finally:
                self.is_recording = False
                try:
                    self.ask_btn.config(state=tk.NORMAL)
                except Exception:
                    pass

        threading.Thread(target=_rec, daemon=True).start()

    def transcribe_and_ask(self):
        def _work():
            try:
                # Prevent transcription if a recording is currently in progress
                if self.is_recording:
                    self.append('SYSTEM', 'Recording in progress — wait until it finishes before transcribing')
                    self.status.config(text='Busy recording')
                    return
                # Ensure a recording exists before attempting transcription
                if not os.path.exists('audio.wav'):
                    self.append('SYSTEM', 'No recording found — please press Record first.')
                    self.status.config(text='No audio to transcribe')
                    return
                # mark transcribing state and disable record button
                self.is_transcribing = True
                try:
                    self.record_btn.config(state=tk.DISABLED)
                except Exception:
                    pass
                self.status.config(text='Transcribing...')
                transcript = transcribe_audio('audio.wav')
                self.append('You (transcript)', transcript)
                self.status.config(text='Asking assistant...')
                
                # Add user message to history
                self.conversation_history.append(f"User: {transcript}")
                
                # Build context from conversation history
                context = "\n".join(self.conversation_history)
                prompt = f"Conversation so far:\n{context}\n\nRespond to the user's latest message."
                print(f"Prompt sent to assistant:\n{prompt}\n")
                reply = ask_assistant(prompt, model='gpt-4o-mini', system_prompt=ROOT_PROMPT)
                
                # Add assistant reply to history
                self.conversation_history.append(f"Assistant: {reply}")
                
                self.append('Assistant', reply)
                # update recipe state (enable Next step button if appropriate)
                try:
                    self._update_recipe_state(reply)
                except Exception:
                    pass
                # play assistant reply using TTS module
                try:
                    speak(reply, lang='ro', use_macos_say=True, voice='Ioana')
                except Exception:
                    pass
                self.status.config(text='Done')
            finally:
                # clear transcribing flag and re-enable record button
                self.is_transcribing = False
                try:
                    self.record_btn.config(state=tk.NORMAL)
                except Exception:
                    pass

        threading.Thread(target=_work, daemon=True).start()
    
    def reset_session(self):
        """Reset the conversation history and clear the text display."""
        self.conversation_history = []
        self.text.delete(1.0, tk.END)
        self.append('SYSTEM', 'Session reset. Conversation history cleared.')
        self.status.config(text='Session reset')
    
    def stop_tts(self):
        """Stop any currently playing TTS audio."""
        try:
            stop()
            self.append('SYSTEM', 'TTS playback stopped')
            self.status.config(text='TTS stopped')
        except Exception as e:
            self.append('ERROR', f'Failed to stop TTS: {e}')
            self.status.config(text='Error stopping TTS')

    def _update_recipe_state(self, assistant_reply: str) -> None:
        """Enable or disable the Next step button based on the assistant reply."""
        lower = assistant_reply.lower()
        started_tokens = ['pasul', 'pas ', '1.', '1)']
        finished_tokens = ['poftă bună', 'pofta']

        if not self.recipe_started and any(tok in lower for tok in started_tokens):
            self.recipe_started = True
            try:
                self.next_step_btn.config(state=tk.NORMAL)
            except Exception:
                pass
            self.append('SYSTEM', 'Recipe started — use "Next step" to continue')
        elif self.recipe_started and any(tok in lower for tok in finished_tokens):
            self.recipe_started = False
            try:
                self.next_step_btn.config(state=tk.DISABLED)
            except Exception:
                pass
            self.append('SYSTEM', 'Recipe appears finished — Next step disabled')

    def next_step(self):
        """Ask the assistant for the next step in the recipe using the conversation history."""
        def _work_next():
            try:
                self.status.config(text='Requesting next step...')
                # add a short user intent to request next step
                self.conversation_history.append('User: Next step')
                context = "\n".join(self.conversation_history)
                prompt = f"Conversation so far:\n{context}\n\nPlease provide the next step of the recipe."
                reply = ask_assistant(prompt, model='gpt-4o-mini', system_prompt=ROOT_PROMPT)
                self.conversation_history.append(f'Assistant: {reply}')
                self.append('Assistant', reply)
                try:
                    speak(reply, lang='ro', use_macos_say=True, voice='Ioana')
                except Exception:
                    pass
                # update recipe state based on reply
                try:
                    self._update_recipe_state(reply)
                except Exception:
                    pass
                self.status.config(text='Done')
            except Exception as e:
                self.append('ERROR', str(e))
                self.status.config(text='Error')

        threading.Thread(target=_work_next, daemon=True).start()


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()