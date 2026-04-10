# Gemini Text-to-Speech for Home Assistant

Custom TTS component using Google's Gemini 2.5 Flash TTS model. Natural Hebrew speech with style control.

## Features

- **30 voices** — including `callirrhoe` (natural Hebrew)
- **2 models** — Flash (fast) and Pro (quality)
- **Style prompts** — "warm and friendly", "professional", "whisper"
- **Config flow** — full UI setup with dropdowns
- **Cache toggle** — enable/disable audio caching

## Installation via HACS

1. Add custom repository: `https://github.com/yairpi165/ha-gemini-tts`
2. Install "Gemini Text-to-Speech"
3. Restart HA
4. Settings → Integrations → Add → Gemini Text-to-Speech
5. Enter Gemini API key, select voice and language

## Setup as Voice Assistant TTS

Settings → Voice Assistants → Edit → Set TTS to **Gemini TTS**

## Voices

Aoede, Achernar, Achird, Algenib, Algieba, Alnilam, Autonoe, **Callirrhoe** (Hebrew), Charon, Despina, Enceladus, Erinome, Fenrir, Gacrux, Iapetus, Kore, Laomedeia, Leda, Orus, Puck, Pulcherrima, Rasalgethi, Sadachbia, Sadaltager, Schedar, Sulafat, Umbriel, Vindemiatrix, Zephyr, Zubenelgenubi

## Style Prompt Examples

- `warm and friendly` — conversational tone
- `professional and clear` — formal
- `cheerful and enthusiastic` — upbeat
- `calm and soothing` — relaxed
- Leave empty for default voice style
