import warnings
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import whisperx
from better_profanity import profanity
from pydub import AudioSegment
from pydub.generators import Sine
from rich import print_json

warnings.filterwarnings("ignore", category=UserWarning, module="pydub")

class Word(TypedDict):
    word: str
    start: float
    end: float
    score: float
    flagged: NotRequired[bool]


class AudioCensor:
    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        # float16 is not supported on CPU; int8 is the fastest option there.
        compute_type: str = "int8",
        language: str = "en",
        batch_size: int = 8,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.batch_size = batch_size

        # Load both models once, at construction, and reuse them for every call.
        self.whisper_model = whisperx.load_model(
            self.model_name,
            self.device,
            compute_type=self.compute_type,
            language=self.language,
        )
        self.align_model, self.align_metadata = whisperx.load_align_model(
            language_code=self.language, device=self.device
        )


    def transcribe_audio(self, audio_path: str) -> dict[str, Any]:
        """Transcribe an English audio file with WhisperX on CPU and align it.

        Returns the aligned result: ``{"segments": [...], "word_segments": [...]}``,
        where each word carries ``start``/``end`` timestamps (in seconds) and a
        ``score``. Words the aligner cannot place (e.g. bare numbers) may lack
        timestamps.
        """
        audio = whisperx.load_audio(audio_path)

        result = self.whisper_model.transcribe(
            audio, batch_size=self.batch_size, language=self.language
        )

        return whisperx.align(
            result["segments"],
            self.align_model,
            self.align_metadata,
            audio,
            self.device,
            return_char_alignments=False,
        )

    def profanity_check(self, words: list[Word]) -> list[Word]:
        """Set ``flagged`` on each word (in place) and return the same list."""
        for word in words:
            word["flagged"] = profanity.contains_profanity(word["word"])
        return words
    def mute_audio(
        self,
        input_path: str,
        output_path: str,
        words: list[Word],
        beep: bool = False,
    )->None:
        """Replace every flagged word with silence (or a beep) and save to ``output_path``.

        With ``beep=True`` each flagged word is replaced by a 1 kHz tone instead
        of silence. The output keeps the input's length; the format is taken
        from the output file extension (e.g. ``.wav``, ``.mp3``).
        """
        audio = AudioSegment.from_file(input_path)

        for word in words:
            # Words the aligner could not place have no timestamps; skip them.
            if not word.get("flagged") or "start" not in word or "end" not in word:
                continue
            start_ms = int(word["start"] * 1000)
            end_ms = int(word["end"] * 1000)
            duration = end_ms - start_ms
            if beep:
                replacement = (
                    Sine(1000, sample_rate=audio.frame_rate)
                    .to_audio_segment(duration=duration, volume=-10.0)
                    .set_channels(audio.channels)
                    .set_sample_width(audio.sample_width)
                )
            else:
                replacement = AudioSegment.silent(
                    duration=duration, frame_rate=audio.frame_rate
                )
            audio = audio[:start_ms] + replacement + audio[end_ms:]

        output_format = Path(output_path).suffix.lstrip(".") or "wav"
        audio.export(output_path, format=output_format)

ac = AudioCensor()

words = ac.transcribe_audio("./sample.wav")
ac.mute_audio(
    input_path="./sample.wav",
    output_path="./sample_censored.wav",
    words=ac.profanity_check(words["word_segments"]),
    beep=True,
)
print_json(data=ac.profanity_check(words["word_segments"]), indent=4)