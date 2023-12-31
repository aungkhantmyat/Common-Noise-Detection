import pyaudio
import math
import struct
import wave
import time
import datetime
import os
import json
import random

TRIGGER_RMS = 10  # start recording above 10
RATE = 16000  # sample rate
TIMEOUT_SECS = 3  # silence time after which recording stops
FRAME_SECS = 0.25  # length of frame(chunks) to be processed at once in secs
CUSHION_SECS = 1  # amount of recording before and after sound

SHORT_NORMALIZE = (1.0 / 32768.0)
FORMAT = pyaudio.paInt16
CHANNELS = 1
SHORT_WIDTH = 2
CHUNK = int(RATE * FRAME_SECS)
CUSHION_FRAMES = int(CUSHION_SECS / FRAME_SECS)
TIMEOUT_FRAMES = int(TIMEOUT_SECS / FRAME_SECS)

f_name_directory = 'D:\Phyton Related Projects\AudioForBest\Recordings' # replace your recording folder directory

class Recorder:
    @staticmethod
    def rms(frame):
        count = len(frame) / SHORT_WIDTH
        format = "%dh" % (count)
        shorts = struct.unpack(format, frame)

        sum_squares = 0.0
        for sample in shorts:
            n = sample * SHORT_NORMALIZE
            sum_squares += n * n
        rms = math.pow(sum_squares / count, 0.5)

        return rms * 1000

    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  output=True,
                                  frames_per_buffer=CHUNK)
        self.time = time.time()
        self.quiet = []
        self.quiet_idx = -1
        self.timeout = 0

    def record(self):
        print('')
        sound = []
        start = time.time()
        begin_time = None
        while True:
            data = self.stream.read(CHUNK)
            rms_val = self.rms(data)
            if self.inSound(data):
                sound.append(data)
                if begin_time == None:
                    begin_time = datetime.datetime.now()
            else:
                if len(sound) > 0:
                    duration=math.floor((datetime.datetime.now()-begin_time).total_seconds())
                    self.write(sound, begin_time, duration)
                    sound.clear()
                    begin_time = None
                else:
                    self.queueQuiet(data)

            curr = time.time()
            secs = int(curr - start)
            tout = 0 if self.timeout == 0 else int(self.timeout - curr)
            label = 'Listening' if self.timeout == 0 else 'Recording'
            print('[+] %s: Level=[%4.2f] Secs=[%d] Timeout=[%d]' % (label, rms_val, secs, tout), end='\r')

    # quiet is a circular buffer of size cushion
    def queueQuiet(self, data):
        self.quiet_idx += 1
        # start over again on overflow
        if self.quiet_idx == CUSHION_FRAMES:
            self.quiet_idx = 0

        # fill up the queue
        if len(self.quiet) < CUSHION_FRAMES:
            self.quiet.append(data)
        # replace the element on the index in a cicular loop like this 0 -> 1 -> 2 -> 3 -> 0 and so on...
        else:
            self.quiet[self.quiet_idx] = data

    def dequeueQuiet(self, sound):
        if len(self.quiet) == 0:
            return sound

        ret = []

        if len(self.quiet) < CUSHION_FRAMES:
            ret.append(self.quiet)
            ret.extend(sound)
        else:
            ret.extend(self.quiet[self.quiet_idx + 1:])
            ret.extend(self.quiet[:self.quiet_idx + 1])
            ret.extend(sound)

        return ret

    def inSound(self, data):
        rms = self.rms(data)
        curr = time.time()

        if rms > TRIGGER_RMS:
            self.timeout = curr + TIMEOUT_SECS
            return True

        if curr < self.timeout:
            return True

        self.timeout = 0
        return False

    def write(self, sound, begin_time, duration):
        # insert the pre-sound quiet frames into sound
        sound = self.dequeueQuiet(sound)

        # sound ends with TIMEOUT_FRAMES of quiet
        # remove all but CUSHION_FRAMES
        keep_frames = len(sound) - TIMEOUT_FRAMES + CUSHION_FRAMES
        recording = b''.join(sound[0:keep_frames])
        filename = str(random.randint(1,50000))+"VoiceViolation"
        pathname = os.path.join(f_name_directory, '{}.wav'.format(filename))
        wf = wave.open(pathname, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(recording)
        wf.close()
        voiceViolation = {
            "Name": "Common Noise is detected.",
            "Time": begin_time.strftime("%m/%d/%Y, %H:%M:%S"),
            "Duration": str(duration) + " seconds",
            "Mark": (2 * (duration - 3)),
            "Link": '{}.wav'.format(filename)
        }
        write_json(voiceViolation)
        print('[+] Saved: {}'.format(pathname))

def write_json(new_data, filename='violation.json'):
    with open(filename, 'r+') as file:
         # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_data with file_data inside emp_details
        file_data.append(new_data)
         # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)

a = Recorder()
a.record()