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


@dataclass(frozen=True)
class VoiceSpec:
    name: str
    family: str
    program: int
    is_drum: bool
    pitch_low: int
    pitch_high: int
    pitch_center: int
    human: bool


@dataclass(frozen=True)
class PerformanceState:
    phase: str
    takeover_bias: float
    response_bars: int
    human_dropout_bar: int
    robot_drive: float
    human_drive: float


VOICE_SPECS: list[VoiceSpec] = [
    VoiceSpec("human_cello", "cello", 42, False, 36, 67, 48, True),
    VoiceSpec("human_trombone", "trombone", 57, False, 43, 74, 55, True),
    VoiceSpec("human_drumset", "drumset", 0, True, 35, 81, 0, True),
    VoiceSpec("human_percussion", "percussion", 0, True, 47, 88, 0, True),
    VoiceSpec("robot_cello", "cello", 42, False, 36, 79, 60, False),
    VoiceSpec("robot_trombone", "trombone", 57, False, 43, 84, 67, False),
    VoiceSpec("robot_drumset", "drumset", 0, True, 35, 81, 0, False),
    VoiceSpec("robot_percussion", "percussion", 0, True, 47, 96, 0, False),
]


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
    durations = [note.end - note.start for note in note_list]
    avg_pitch = float(np.mean(pitches))
    pitch_span = max(pitches) - min(pitches) if pitches else 0
    duration = note_list[-1].end - note_list[0].start if note_list else 0.0
    bars = max(1, int(round(duration / seconds_per_bar(tempo, time_sig))))
    notes_per_bar = len(note_list) / bars if bars else len(note_list)
    tail = sorted(note_list, key=lambda note: note.start)[-8:]
    motif = [note.pitch for note in tail[-4:]] if tail else []
    ioi = [tail[i + 1].start - tail[i].start for i in range(len(tail) - 1)] if len(tail) > 1 else []
    rhythmic_variance = float(np.std(ioi)) if ioi else 0.0
    duration_mean = float(np.mean(durations)) if durations else 0.0
    duration_std = float(np.std(durations)) if durations else 0.0
    repeat_ratio = float(
        sum(1 for i in range(len(pitches) - 1) if abs(pitches[i + 1] - pitches[i]) <= 2) / max(1, len(pitches) - 1)
    )
    syncopation = float(
        np.mean(
            [
                abs((note.start / (60.0 / tempo)) - round(note.start / (60.0 / tempo)))
                for note in note_list
            ]
        )
    ) if note_list else 0.0

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
        "duration_mean": duration_mean,
        "duration_std": duration_std,
        "repeat_ratio": repeat_ratio,
        "syncopation": syncopation,
    }


def decide_action(features: dict[str, float | int | str | list[int]]) -> dict[str, int | str]:
    density = str(features["density"])
    register = str(features["register"])
    pitch_span = int(features["pitch_span"])
    rhythmic_variance = float(features["rhythmic_variance"])
    repeat_ratio = float(features["repeat_ratio"])
    syncopation = float(features["syncopation"])

    takeover_bias = float(
        np.clip(
            0.35 * (1.0 if density == "high" else 0.5 if density == "medium" else 0.2)
            + 0.25 * np.clip(pitch_span / 30.0, 0.0, 1.0)
            + 0.20 * np.clip(rhythmic_variance / 0.18, 0.0, 1.0)
            + 0.10 * np.clip(syncopation / 0.35, 0.0, 1.0)
            + 0.10 * repeat_ratio,
            0.0,
            1.0,
        )
    )

    if density == "high" and register == "high":
        initial_phase = "conflict"
    elif density == "high" and register == "mid":
        initial_phase = "drift"
    elif density == "low":
        initial_phase = "control"
    elif rhythmic_variance > 0.08:
        initial_phase = "drift"
    else:
        initial_phase = "control"

    response_bars = int(np.clip(int(features["bars"]) + 8 + round(takeover_bias * 4), 12, 20))
    human_dropout_bar = int(np.clip(round(response_bars * (0.60 - takeover_bias * 0.20)), 3, response_bars - 2))
    robot_drive = float(np.clip(0.40 + takeover_bias * 0.60, 0.0, 1.0))
    human_drive = float(np.clip(1.0 - takeover_bias * 0.55, 0.15, 1.0))

    return {
        "mode": initial_phase,
        "response_density": density,
        "bars": int(features["bars"]),
        "latency_bars": DEFAULT_LATENCY_BARS,
        "target_notes": 32,
        "octave_shift": 0,
        "takeover_bias": takeover_bias,
        "response_bars": response_bars,
        "human_dropout_bar": human_dropout_bar,
        "robot_drive": robot_drive,
        "human_drive": human_drive,
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


def clamp_pitch(pitch: int, low: int, high: int) -> int:
    return int(np.clip(pitch, low, high))


def get_phase_for_bar(bar_index: int, response_bars: int, takeover_bias: float) -> str:
    progress = bar_index / max(1, response_bars - 1)
    control_end = 0.18 + takeover_bias * 0.08
    drift_end = 0.45 + takeover_bias * 0.08
    conflict_end = 0.78 + takeover_bias * 0.07
    if progress < control_end:
        return "control"
    if progress < drift_end:
        return "drift"
    if progress < conflict_end:
        return "conflict"
    if progress < 0.95:
        return "takeover"
    return "aftermath"


def family_cycle(family: str) -> list[int]:
    if family == "cello":
        return [0, 7, 12, 19]
    if family == "trombone":
        return [0, 5, 10, 14]
    if family == "drumset":
        return [36, 38, 42, 46]
    return [49, 51, 56, 60]


def build_voice_specs() -> list[VoiceSpec]:
    return VOICE_SPECS


def build_voice_instrument(spec: VoiceSpec) -> pretty_midi.Instrument:
    return pretty_midi.Instrument(program=spec.program, is_drum=spec.is_drum, name=spec.name)


def scale_pitch(pitch: int, scale_pc: list[int]) -> int:
    pc = pitch % 12
    if pc in scale_pc:
        return pitch
    closest = min(scale_pc, key=lambda candidate: abs(candidate - pc))
    return pitch - pc + closest


def voice_pattern(
    spec: VoiceSpec,
    phase: str,
    bar_index: int,
    takeover_bias: float,
    human_dropout_bar: int,
    motif: list[int],
) -> list[tuple[int, float, float, int]]:
    patterns = {
        "control": {
            "cello": [0.0, 2.0],
            "trombone": [1.0, 3.0],
            "drumset": [0.0, 1.0, 2.0, 3.0],
            "percussion": [0.5, 2.5],
        },
        "drift": {
            "cello": [0.0, 1.5, 3.0],
            "trombone": [0.5, 2.0, 3.5],
            "drumset": [0.0, 0.75, 1.5, 2.25, 3.0, 3.75],
            "percussion": [0.25, 1.75, 2.75],
        },
        "conflict": {
            "cello": [0.0, 1.0, 2.5, 3.0],
            "trombone": [0.0, 1.25, 2.0, 3.25],
            "drumset": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5],
            "percussion": [0.0, 0.75, 1.75, 2.5, 3.25],
        },
        "takeover": {
            "cello": [0.0, 0.5, 1.0, 1.5],
            "trombone": [0.0, 0.5, 1.0, 1.5],
            "drumset": [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5, 3.75],
            "percussion": [0.125, 0.625, 1.125, 1.625, 2.125, 2.625, 3.125, 3.625],
        },
        "aftermath": {
            "cello": [],
            "trombone": [],
            "drumset": [0.0, 1.0, 2.0, 3.0],
            "percussion": [0.0, 2.0],
        },
    }

    if spec.human and phase == "takeover" and bar_index >= human_dropout_bar:
        return []
    if spec.human and phase == "aftermath":
        return []

    offsets = patterns[phase][spec.family]
    if not offsets:
        return []

    note_events: list[tuple[int, float, float, int]] = []
    family_notes = family_cycle(spec.family)
    is_pitched = not spec.is_drum

    if is_pitched:
        base_cycle = motif or [60, 62, 64, 67]
        if spec.family == "cello":
            transpose = -12 if spec.human else 0
            base_pitch = base_cycle[bar_index % len(base_cycle)] + transpose
        elif spec.family == "trombone":
            transpose = -5 if spec.human else 7
            base_pitch = base_cycle[(bar_index + 1) % len(base_cycle)] + transpose
        else:
            base_pitch = base_cycle[0]

        for idx, offset in enumerate(offsets):
            pitch = base_pitch + (idx % 3) * (2 if phase != "control" else 1)
            if phase in {"conflict", "takeover"} and not spec.human:
                pitch += 7 if idx % 2 else 12
            if phase in {"conflict", "takeover"} and spec.human:
                pitch -= 2 if spec.family == "cello" else 4
            pitch = scale_pitch(pitch, [0, 2, 4, 5, 7, 9, 11])
            pitch = clamp_pitch(pitch, spec.pitch_low, spec.pitch_high)
            if spec.family == "cello" and phase == "takeover" and spec.human:
                velocity = 52
            elif spec.human:
                velocity = 68 + int(6 * np.sin((bar_index + idx) / 2))
            else:
                velocity = 78 + int(8 * takeover_bias) + (4 if phase in {"conflict", "takeover"} else 0)

            duration = 1.6 if spec.family == "cello" else 1.0
            if phase == "drift":
                duration *= 0.9
            elif phase == "conflict":
                duration *= 0.75
            elif phase == "takeover":
                duration *= 0.65 if spec.human else 0.5
            note_events.append((pitch, offset, duration, velocity))
    else:
        if spec.family == "drumset":
            note_map = family_notes
        else:
            note_map = family_notes[::-1]

        for idx, offset in enumerate(offsets):
            pitch = note_map[idx % len(note_map)]
            if spec.family == "percussion" and phase in {"conflict", "takeover"} and not spec.human:
                pitch = note_map[(idx + 1) % len(note_map)]
            if spec.family == "percussion" and spec.human and phase == "takeover":
                pitch = note_map[0]
            if spec.family == "drumset" and phase == "aftermath":
                pitch = note_map[0] if idx % 2 == 0 else note_map[1]
            velocity = 60 + int(20 * takeover_bias) + (10 if not spec.human else 0)
            if spec.family == "drumset" and idx % 4 == 0:
                velocity += 8
            if spec.family == "percussion" and idx % 2 == 1:
                velocity += 4
            duration = 0.18 if spec.family == "drumset" else 0.28
            if phase == "takeover" and not spec.human:
                duration = 0.14 if spec.family == "drumset" else 0.20
            note_events.append((pitch, offset, duration, velocity))

    return note_events


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
    recent_notes = sorted(note_list, key=lambda note: note.start)[-8:]
    motif = [note.pitch for note in recent_notes[-4:]] if recent_notes else []
    motif = motif if motif else [60, 62, 64, 67]

    key_root = detect_key(note_list)
    scale_pc = get_major_scale(key_root)

    bar_len = seconds_per_bar(tempo, time_sig)
    step = (60.0 / tempo) / 2
    current_time = quantize(start_time + int(action["latency_bars"]) * bar_len, step)

    state = PerformanceState(
        phase=str(action["mode"]),
        takeover_bias=float(action["takeover_bias"]),
        response_bars=int(action["response_bars"]),
        human_dropout_bar=int(action["human_dropout_bar"]),
        robot_drive=float(action["robot_drive"]),
        human_drive=float(action["human_drive"]),
    )

    instruments = [build_voice_instrument(spec) for spec in build_voice_specs()]
    instrument_map = {spec.name: instrument for spec, instrument in zip(build_voice_specs(), instruments)}

    for bar_index in range(state.response_bars):
        phase = get_phase_for_bar(bar_index, state.response_bars, state.takeover_bias)
        bar_start = current_time + bar_index * bar_len
        if phase == "takeover":
            takeover_bias = min(1.0, state.takeover_bias + 0.15 + bar_index / max(1, state.response_bars - 1) * 0.2)
        elif phase == "aftermath":
            takeover_bias = 1.0
        else:
            takeover_bias = min(1.0, state.takeover_bias + bar_index / max(1, state.response_bars - 1) * 0.25)

        for spec in build_voice_specs():
            note_events = voice_pattern(spec, phase, bar_index, takeover_bias, state.human_dropout_bar, motif)
            instrument = instrument_map[spec.name]
            for pitch, offset, duration, velocity in note_events:
                start = quantize(bar_start + offset * step, step)
                end = start + max(duration * step, step * 0.5)
                note = pretty_midi.Note(
                    velocity=int(np.clip(velocity, 40, 120)),
                    pitch=int(pitch),
                    start=start,
                    end=end,
                )
                instrument.notes.append(note)

    for instrument in instruments:
        instrument.notes.sort(key=lambda note: note.start)
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

    response_notes = [note for instrument in response_midi.instruments for note in instrument.notes]
    response_instrument = response_midi.instruments[0]

    return PlaybackResult(
        input_path=input_path,
        output_path=output_path,
        features=features,
        action=action,
        source_instrument_name=pretty_midi.program_to_instrument_name(instrument.program),
        response_instrument_name="multi-instrument ensemble",
        response_note_count=len(response_notes),
        response_pitch_min=min(note.pitch for note in response_notes),
        response_pitch_max=max(note.pitch for note in response_notes),
        duration_seconds=midi.get_end_time(),
    )
