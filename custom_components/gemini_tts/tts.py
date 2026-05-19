"""Gemini TTS platform for Home Assistant."""

import io
import logging
import wave
from typing import Any

from google import genai
from google.genai import types

from homeassistant.components.tts import TextToSpeechEntity, Voice, TtsAudioType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_API_KEY,
    CONF_CACHE,
    CONF_LANGUAGE,
    CONF_MODEL,
    CONF_STYLE_PROMPT,
    CONF_VOICE,
    DEFAULT_CACHE,
    DEFAULT_LANGUAGE,
    DEFAULT_MODEL,
    DEFAULT_STYLE_PROMPT,
    DEFAULT_VOICE,
    DOMAIN,
    SUPPORTED_LANGUAGES,
    VOICES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gemini TTS from config entry."""
    async_add_entities([GeminiTTSEntity(hass, entry)])


class GeminiTTSEntity(TextToSpeechEntity):
    """Gemini TTS entity."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self._entry = entry
        self._attr_name = "Gemini TTS"
        self._attr_unique_id = entry.entry_id

        data = entry.data
        options = entry.options
        self._api_key = data[CONF_API_KEY]
        self._model = options.get(CONF_MODEL, data.get(CONF_MODEL, DEFAULT_MODEL))
        self._voice = options.get(CONF_VOICE, data.get(CONF_VOICE, DEFAULT_VOICE))
        self._language = options.get(CONF_LANGUAGE, data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE))
        self._style_prompt = options.get(CONF_STYLE_PROMPT, data.get(CONF_STYLE_PROMPT, DEFAULT_STYLE_PROMPT))
        self._cache_enabled = options.get(CONF_CACHE, data.get(CONF_CACHE, DEFAULT_CACHE))

        # Lazy init — avoid blocking SSL handshake on event loop
        self._client = None

    @property
    def default_options(self) -> dict[str, Any]:
        """Return default options."""
        return {
            CONF_VOICE: self._voice,
            CONF_STYLE_PROMPT: self._style_prompt,
        }

    @property
    def supported_languages(self) -> list[str]:
        """Return list of supported languages."""
        return SUPPORTED_LANGUAGES

    @property
    def default_language(self) -> str:
        """Return default language."""
        return self._language

    @property
    def supported_options(self) -> list[str]:
        """Return supported options."""
        return [CONF_VOICE, CONF_STYLE_PROMPT]

    def get_supported_voices(self, language: str) -> list[Voice] | None:
        """Return list of supported voices for a language."""
        return [Voice(voice_id=v, name=v) for v in VOICES]

    async def async_get_tts_audio(
        self, message: str, language: str, options: dict[str, Any]
    ) -> TtsAudioType:
        """Generate TTS audio using Gemini."""
        voice = options.get(CONF_VOICE, self._voice)
        style = options.get(CONF_STYLE_PROMPT, self._style_prompt)

        # Build content — must clearly instruct TTS to speak, not generate text
        if style:
            content = f"Say the following in a {style} voice: {message}"
        else:
            content = f"Say the following: {message}"

        _LOGGER.debug(
            "Generating TTS: model=%s, voice=%s, lang=%s, text=%s",
            self._model, voice, language, message[:50],
        )

        try:
            response = await self.hass.async_add_executor_job(
                self._generate_audio, content, voice
            )

            if (
                not response.candidates
                or not response.candidates[0].content
                or not response.candidates[0].content.parts
            ):
                self._log_empty_response(response, message, voice, language)
                return (None, None)

            audio_pcm = response.candidates[0].content.parts[0].inline_data.data
            wav_bytes = _pcm_to_wav(audio_pcm)

            _LOGGER.debug("Generated %d bytes of WAV audio", len(wav_bytes))
            return ("wav", wav_bytes)

        except Exception as e:
            _LOGGER.error("Gemini TTS failed: %s", e)
            return (None, None)

    def _log_empty_response(self, response, message: str, voice: str, language: str) -> None:
        """JANE-163 diagnostic — dump every available field on empty-response."""
        pf = getattr(response, "prompt_feedback", None)
        block_reason = getattr(pf, "block_reason", None) if pf else None
        prompt_safety = getattr(pf, "safety_ratings", None) if pf else None

        cands = getattr(response, "candidates", None) or []
        cand_summaries = []
        for i, c in enumerate(cands):
            cand_summaries.append({
                "i": i,
                "finish_reason": getattr(c, "finish_reason", None),
                "finish_message": getattr(c, "finish_message", None),
                "safety_ratings": getattr(c, "safety_ratings", None),
                "content_present": getattr(c, "content", None) is not None,
                "parts_count": len(getattr(getattr(c, "content", None), "parts", None) or []),
            })

        usage = getattr(response, "usage_metadata", None)
        model_version = getattr(response, "model_version", None)

        _LOGGER.error(
            "Empty response from Gemini TTS | model=%s voice=%s lang=%s text=%r len=%d | "
            "block_reason=%s prompt_safety=%s candidates_count=%d candidates=%s usage=%s model_version=%s",
            self._model, voice, language, message, len(message),
            block_reason, prompt_safety, len(cands), cand_summaries, usage, model_version,
        )

    def _generate_audio(self, content: str, voice: str):
        """Call Gemini TTS API (sync, runs in executor)."""
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client.models.generate_content(
            model=self._model,
            contents=content,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            ),
        )


def _pcm_to_wav(pcm_data: bytes) -> bytes:
    """Convert raw PCM (24kHz, 16-bit, mono) to WAV."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_data)
    return buf.getvalue()
