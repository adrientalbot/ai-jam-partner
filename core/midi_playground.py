from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pretty_midi

DEFAULT_SEED = 7
DEFAULT_TEMPO = 120
DEFAULT_TIME_SIG = (4, 4)
DEFAULT_LATENCY_BARS = 1


def find_repo_root(start: Path | None = None) -> Path:
    candidates = []
    current = (start or Path.cwd()).resolve()
    candidates.extend([current, current.parent, current.parent.parent])
    for candidate in candidates:
        if (candidate / "pyproject.toml").exists() and (candidate / "data").exists():
            return candidate
    raise FileNotFoundError("Could not find repo root from the current working directory")


def seconds_per_bar(tempo: int = DEFAULT_TEMPO, time_sig: tuple[int, int] = DEFAULT_TIME_SIG) -> float:
    return 60.0 / tempo * time_sig[0]


def density_bucket(notes_per_bar: float) -> str:
    if notes_per_bar < 4:
        return "low"
    if notes_per_bar < 7:
        return "medium"
    return "high"


def register_bucket(avg_pitch: float) -> str:
    if avg_pitch < 54:
        return "low"
    if avg_pitch < 66:
        return "mid"
    return "high"


def quantize(value: float, step: float) -> float:
    return round(value / step) * step


def load_midi(path: Path) -> tuple[pretty_midi.PrettyMIDI, pretty_midi.Instrument, list[pretty_midi.Note]]:
    midi = pretty_midi.PrettyMIDI(str(path))
    if not midi.instruments:
        raise ValueError("Input MIDI contains no instruments")

    instrument = midi.instruments[0]
    notes = sorted(instrument.notes, key=lambda note: note.start)
    if not notes:
        raise ValueError("Input MIDI contains no notes in the first instrument")

    return midi, instrument, notes


def extract_features(
    notes: Iterable[pretty_midi.Note],
    tempo: int = DEFAULT_TEMPO,
    time_sig: tuple[int, int] = DEFAULT_TIME_SIG,
) -> dict[str, float | int | str | list[int]]:
    note_list = list(notes)
    pitches = [note.pitch for note in note_list]
    avg_pitch = float(np.mean(pitches))
    pitch_span = max(pitches) - min(pitches) if pitches else 0
    duration = note_list[-1].end - note_list[0].start if note_list else 0.0
    bars = max(1, int(round(duration / seconds_per_bar(tempo, time_sig))))
    notes_per_bar = len(note_list) / bars if bars else len(note_list)
    tail = sorted(note_list, key=lambda note: note.start)[-8:]
    motif = [note.pitch for note in tail[-4:]] if tail else []
    ioi = [tail[i + 1].start - tail[i].start for i in range(len(tail) - 1)] if len(tail) > 1 else []
    rhythmic_variance = float(np.std(ioi)) if ioi else 0.0

    return {
        "note_count": len(note_list),
        "avg_pitch": avg_pitch,
        "pitch_span": pitch_span,
        "density": density_bucket(notes_per_bar),
        "notes_per_bar": notes_per_bar,
        "register": register_bucket(avg_pitch),
        "bars": bars,
        "motif": motif,
        "rhythmic_variance": rhythmic_variance,
    }


def decide_action(features: dict[str, float | int | str | list[int]]) -> dict[str, int | str]:
    density = str(features["density"])
    register = str(features["register"])
    pitch_span = int(features["pitch_span"])
    rhythmic_variance = float(features["rhythmic_variance"])

    if density == "high" and register == "mid" and pitch_span >= 20:
        mode = "contrast"
        response_density = "low"
        octave_shift = 12
    elif density == "high" and register == "low":
        mode = "sequence"
        response_density = "medium"
        octave_shift = 24
    elif density == "medium" and register == "high":
        mode = "fragment"
        response_density = "medium"
        octave_shift = 12
    elif rhythmic_variance > 0.05:
        mode = "repeat"
        response_density = "medium"
        octave_shift = 0
    else:
        mode = "sequence"
        response_density = "low"
        octave_shift = 12

    return {
        "mode": mode,
        "response_density": response_density,
        "bars": int(features["bars"]),
        "latency_bars": DEFAULT_LATENCY_BARS,
        "target_notes": 32,
        "octave_shift": octave_shift,
    }


def detect_key(notes: Iterable[pretty_midi.Note]) -> int:
    note_list = list(notes)
    if not note_list:
        return 60
    pcs = [note.pitch % 12 for note in note_list]
    root = Counter(pcs).most_common(1)[0][0]
    return 60 + root


def get_major_scale(root: int) -> list[int]:
    return [(root + interval) % 12 for interval in [0, 2, 4, 5, 7, 9, 11]]


def constrain_to_scale(pitches: Iterable[int], scale_pc: Iterable[int]) -> list[int]:
    scale = list(scale_pc)
    out = []
    for pitch in pitches:
        pc = pitch % 12
        if pc not in scale:
            closest = min(scale, key=lambda candidate: abs(candidate - pc))
            pitch = pitch - pc + closest
        out.append(pitch)
    return out


def choose_response_program(source_instrument: pretty_midi.Instrument, action: dict[str, int | str], features: dict[str, float | int | str | list[int]]) -> int:
    return source_instrument.program


def build_response(
    notes: Iterable[pretty_midi.Note],
    action: dict[str, int | str],
    source_instrument: pretty_midi.Instrument,
    features: dict[str, float | int | str | list[int]],
    tempo: int = DEFAULT_TEMPO,
    time_sig: tuple[int, int] = DEFAULT_TIME_SIG,
    start_time: float = 0.0,
) -> pretty_midi.PrettyMIDI:
    note_list = list(notes)
    response = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    response_program = choose_response_program(source_instrument, action, features)
    instrument = pretty_midi.Instrument(program=response_program)

    recent_notes = sorted(note_list, key=lambda note: note.start)[-8:]
    motif = [note.pitch for note in recent_notes[-4:]] if recent_notes else []
    motif = motif if motif else [60, 62, 64, 67]

    key_root = detect_key(note_list)
    scale_pc = get_major_scale(key_root)

    bar_len = seconds_per_bar(tempo, time_sig)
    step = (60.0 / tempo) / 2
    current_time = quantize(start_time + int(action["latency_bars"]) * bar_len, step)

    response_density = str(action["response_density"])
    if response_density == "low":
        note_length = step * 1.5
    elif response_density == "medium":
        note_length = step * 1.0
    else:
        note_length = step * 0.75

    mode = str(action["mode"])
    base = motif[:]
    if mode == "repeat":
        pitches = base + base[:4]
    elif mode == "fragment":
        fragment = base[-2:]
        pitches = fragment * 8
    elif mode == "sequence":
        pitches = base + [p + 2 for p in base] + [p + 4 for p in base]
    else:
        pitches = [p for p in base] + [p + 5 for p in base] + [p - 2 for p in base]

    pitches = [p + int(action["octave_shift"]) for p in pitches]

    if note_list:
        avg_pitch = int(np.mean([note.pitch for note in note_list]))
        target_center = avg_pitch + (12 if mode != "repeat" else 0)
        current_center = int(np.mean(pitches))
        center_shift = target_center - current_center
        pitches = [p + center_shift for p in pitches]

    pitches = constrain_to_scale(pitches, scale_pc)
    pitches = [int(np.clip(pitch, 48, 84)) for pitch in pitches]

    if response_density == "low":
        pitches = pitches[: max(8, len(pitches) // 2)]

    target_notes = int(action.get("target_notes", 32))
    while len(pitches) < target_notes:
        pitches.extend([pitch + 2 for pitch in pitches[:4]])
    pitches = pitches[:target_notes]

    velocities = [70 + int(8 * np.sin(index / 2)) for index in range(len(pitches))]

    for index, pitch in enumerate(pitches):
        note = pretty_midi.Note(
            velocity=int(np.clip(velocities[index], 50, 100)),
            pitch=int(pitch),
            start=current_time,
            end=current_time + note_length,
        )
        instrument.notes.append(note)
        current_time += step

    response.instruments.append(instrument)
    return response


@dataclass(frozen=True)
class PlaybackResult:
    input_path: Path
    output_path: Path
    features: dict[str, float | int | str | list[int]]
    action: dict[str, int | str]
    source_instrument_name: str
    response_instrument_name: str
    response_note_count: int
    response_pitch_min: int
    response_pitch_max: int
    duration_seconds: float


def generate_response(
    input_path: Path,
    output_path: Path,
    tempo: int = DEFAULT_TEMPO,
    time_sig: tuple[int, int] = DEFAULT_TIME_SIG,
) -> PlaybackResult:
    np.random.seed(DEFAULT_SEED)
    midi, instrument, notes = load_midi(input_path)
    features = extract_features(notes, tempo=tempo, time_sig=time_sig)
    action = decide_action(features)
    response_midi = build_response(
        notes,
        action,
        source_instrument=instrument,
        features=features,
        tempo=tempo,
        time_sig=time_sig,
        start_time=midi.get_end_time(),
    )

    combined = pretty_midi.PrettyMIDI(initial_tempo=tempo)
    combined.instruments = midi.instruments + response_midi.instruments
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.write(str(output_path))

    response_instrument = response_midi.instruments[0]
    response_notes = response_instrument.notes

    return PlaybackResult(
        input_path=input_path,
        output_path=output_path,
        features=features,
        action=action,
        source_instrument_name=pretty_midi.program_to_instrument_name(instrument.program),
        response_instrument_name=pretty_midi.program_to_instrument_name(response_instrument.program),
        response_note_count=len(response_notes),
        response_pitch_min=min(note.pitch for note in response_notes),
        response_pitch_max=max(note.pitch for note in response_notes),
        duration_seconds=midi.get_end_time(),
    )
