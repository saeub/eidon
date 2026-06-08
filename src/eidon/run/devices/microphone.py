import math
import wave
from pathlib import Path

import pyaudio


class Microphone:
    def __init__(self):
        self.pyaudio = pyaudio.PyAudio()

        # TODO: Make configurable
        self.num_channels = 2
        self.format = pyaudio.paInt16
        self.sample_width = self.pyaudio.get_sample_size(self.format)
        self.framerate = 44100

        self.file = None
        self.stream = None
        self.latest_data = None

    def start_recording(self, path: Path | str | None = None):
        """
        Start streaming audio and save it to the provided path.

        If no path is provided, record to an in-memory buffer (to monitor volume).
        """
        assert self.stream is None, "Recording is already in progress."

        if path is None:
            # Record to 0.1 seconds in-memory buffer if no path is provided
            self.file = AudioBuffer(
                0.1, self.framerate, self.num_channels, self.sample_width
            )
        else:
            self.file = wave.open(str(path), "w")
            self.file.setnchannels(self.num_channels)
            self.file.setsampwidth(self.sample_width)
            self.file.setframerate(self.framerate)

        self.stream = self.pyaudio.open(
            format=self.format,
            channels=self.num_channels,
            rate=self.framerate,
            input=True,
            stream_callback=self._callback,
        )

    def stop_recording(self):
        """Stop the ongoing audio recording and close the file."""
        if self.stream is not None:
            self.stream.close()
            self.stream = None

        if self.file is not None:
            self.file.close()
            self.file = None

    def _callback(self, in_data, frame_count, time_info, status):
        if self.file is not None:
            self.file.writeframes(in_data)
        self.latest_data = in_data
        return None, pyaudio.paContinue


class AudioBuffer:
    """
    A simple in-memory audio buffer to monitor volume levels in real time.

    Uses an interface similar to wave.Wave_write for compatibility.
    """

    def __init__(
        self, length: float, framerate: int, num_channels: int, sample_width: int
    ):
        self.size = int(length * framerate) * num_channels * sample_width
        self.num_channels = num_channels
        self.sample_width = sample_width
        self.buffer = bytearray()

    def writeframes(self, data: bytes):
        self.buffer.extend(data)
        if len(self.buffer) > self.size:
            self.buffer = self.buffer[len(self.buffer) - self.size :]

    def close(self):
        pass

    def get_volume(self) -> float:
        """Calculate the RMS volume of the data currently in the buffer."""
        num_samples = len(self.buffer) // (self.sample_width * self.num_channels)
        if num_samples == 0:
            return 0.0
        total_squares = 0.0
        for i in range(num_samples):
            start = (i * self.num_channels) * self.sample_width
            sample_bytes = self.buffer[start : start + self.sample_width]
            sample = int.from_bytes(sample_bytes, byteorder="little", signed=True)
            total_squares += sample**2
        mean_square = total_squares / (num_samples * self.num_channels)
        rms = math.sqrt(mean_square)
        return rms
