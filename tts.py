"""Text-to-speech utilities.

speak(text, lang='ro', use_macos_say=False, voice=None)
- If use_macos_say=True and running on macOS, uses the `say` command (voice optional).
- Otherwise falls back to gTTS-generated MP3 playback (afplay / playsound / system open).
"""
import platform
import subprocess
import tempfile
import os
import threading
import time

from gtts import gTTS

# Global state to track current playback process and temporary file so we can stop playback
_current_proc_lock = threading.Lock()
_current_proc = None
_current_tempfile = None


def _say_text(text: str, voice: str | None = None) -> None:
    """Call macOS `say` to speak text."""
    global _current_proc
    try:
        cmd = ['say']
        if voice:
            cmd += ['-v', voice]
        cmd += [text]
        with _current_proc_lock:
            _current_proc = subprocess.Popen(cmd)
        # wait until finished or terminated
        _current_proc.wait()
    except Exception:
        # don't raise from background thread
        pass
    finally:
        with _current_proc_lock:
            _current_proc = None


def _play_and_cleanup(path: str) -> None:
    global _current_proc, _current_tempfile
    try:
        if platform.system() == 'Darwin':
            with _current_proc_lock:
                _current_proc = subprocess.Popen(['afplay', path])
            _current_proc.wait()
        else:
            try:
                from playsound import playsound
                # playsound is blocking and doesn't expose a process handle; call it directly
                playsound(path)
            except Exception:
                if platform.system() == 'Windows':
                    # type: ignore[attr-defined]
                    os.startfile(path)
                else:
                    with _current_proc_lock:
                        _current_proc = subprocess.Popen(['xdg-open', path])
                    _current_proc.wait()
        # give a small delay to ensure playback has started before removing
        time.sleep(0.5)
    finally:
        try:
            os.remove(path)
        except Exception:
            pass
        with _current_proc_lock:
            _current_proc = None
            _current_tempfile = None


def speak(text: str, lang: str = 'ro', use_macos_say: bool = False, voice: str | None = None) -> None:
    """Generate speech and play it asynchronously.

    If use_macos_say=True and running on macOS, uses the native `say` command
    (optionally with a specified voice). Otherwise generates an MP3 with gTTS
    and plays it in background.

    Returns immediately; playback occurs in background threads.
    """
    global _current_tempfile
    # Prefer macOS native TTS when requested and available
    if use_macos_say and platform.system() == 'Darwin':
        threading.Thread(target=_say_text, args=(text, voice), daemon=True).start()
        return

    # gTTS fallback (requires internet)
    try:
        tf = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        tf.close()
        tts = gTTS(text=text, lang=lang)
        tts.save(tf.name)
        with _current_proc_lock:
            _current_tempfile = tf.name
        threading.Thread(target=_play_and_cleanup, args=(tf.name,), daemon=True).start()
    except Exception as e:
        # print for debugging but do not raise
        print('TTS error:', e)


def stop() -> None:
    """Stop any currently playing speech and clean up temporary files."""
    global _current_proc, _current_tempfile
    with _current_proc_lock:
        proc = _current_proc
        tf = _current_tempfile
        # clear globals so background threads won't try to remove again
        _current_proc = None
        _current_tempfile = None

    if proc:
        try:
            proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if tf:
        try:
            os.remove(tf)
        except Exception:
            pass


def is_speaking() -> bool:
    """Return True if TTS is currently playing."""
    with _current_proc_lock:
        return _current_proc is not None
