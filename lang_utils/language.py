import time
import pyttsx4
import speech_recognition as sr
from playsound import playsound

engine = pyttsx4.Engine()


def audio2text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)  # read the entire audio file
    # recognize speech using Sphinx
    try:
        res = recognizer.recognize_sphinx(audio)
        return res
    except sr.UnknownValueError:
        print("Sphinx could not understand audio")
    except sr.RequestError as e:
        print("Sphinx error; {0}".format(e))
    return None


def text2audio(text):
    try:
        filename = "{}.wav".format(time.time())
        engine.save_to_file(text, filename)
        engine.runAndWait()
        return filename
    except Exception as e:
        print("text2audio failed for: {}, error:{}".format(text, e))
    return None


def play_audio(filename):
    try:
        playsound(filename)
    except Exception as e:
        print("play {} failed, error:{}".format(filename, e))


if __name__ == '__main__':
    # lyric = "冷咖啡离开乐杯垫，我忍住的情绪在很后面"
    # lyric = "hello from the other side, i wish i could never die"
    lyric = "it has been a long day without you my friend, i will tell you all about it when i see you again"
    filepath = text2audio(lyric)
    play_audio(filepath)
    print(audio2text(filepath))
