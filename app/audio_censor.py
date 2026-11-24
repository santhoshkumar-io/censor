from typing import Any

import whisperx
from rich import print_json

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

ac = AudioCensor()
result = ac.transcribe_audio("./sample.wav")
print_json(data=result)