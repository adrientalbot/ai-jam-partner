# ai-jam-partner

An experimental MIDI-based call-and-response system for the human / robot / AI music project.

## What this repo is

This repository contains a notebook-first MVP for:

- reading MIDI files
- extracting simple musical features
- generating a reactive MIDI response
- exporting a new MIDI file for playback or DAW review

The first version is intentionally MIDI-only and rule-based. It is designed to validate the musical interaction before adding real-time audio, robotics, or model training.

## Project Files

- `[MVP.md](/Users/adrientalbot/Desktop/ai-jam-partner/MVP.md)` short description of the MVP
- `[notebooks/01_mvp_playground.ipynb](/Users/adrientalbot/Desktop/ai-jam-partner/notebooks/01_mvp_playground.ipynb)` notebook demo
- `[data/input_midi/](/Users/adrientalbot/Desktop/ai-jam-partner/data/input_midi)` sample MIDI inputs
- `[data/output_midi/](/Users/adrientalbot/Desktop/ai-jam-partner/data/output_midi)` generated MIDI outputs

## Setup

This project is managed with `uv`.

Install dependencies:

```bash
uv sync
```

If you want to enter the environment manually:

```bash
source .venv/bin/activate
```

## Run the Notebook

Start Jupyter:

```bash
uv run jupyter lab
```

Open:

- `[notebooks/01_mvp_playground.ipynb](/Users/adrientalbot/Desktop/ai-jam-partner/notebooks/01_mvp_playground.ipynb)`

The notebook defaults to:

- input MIDI: `[data/input_midi/mvp_minimalist_input.mid](/Users/adrientalbot/Desktop/ai-jam-partner/data/input_midi/mvp_minimalist_input.mid)`
- output MIDI: `[data/output_midi/mvp_minimalist_response.mid](/Users/adrientalbot/Desktop/ai-jam-partner/data/output_midi/mvp_minimalist_response.mid)`

## Using MIDI Files

To test the system with your own MIDI file:

1. Copy the `.mid` file into `data/input_midi/`
2. Update the `INPUT_MIDI` path in the notebook
3. Run the notebook from top to bottom
4. Inspect the generated file in `data/output_midi/`

Helpful notes:

- the first track is treated as the input source by default
- the notebook expects at least one instrument track
- the output MIDI can be imported into a DAW or MIDI player
- if your source file has a piano timbre, the response currently keeps the same instrument program for consistency

## What the MVP Does

- extracts basic features like density and register
- chooses a response mode such as `repeat`, `fragment`, `sequence`, or `contrast`
- generates a longer response phrase after a short latency
- writes a new MIDI file to disk

## Suggested Next Step

Once the notebook prototype feels good, the next step is to split the same logic into:

- a Python backend on `Render`
- a browser frontend on `Vercel`
