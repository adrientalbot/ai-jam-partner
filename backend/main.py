from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
import logging

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.midi_playground import find_repo_root, generate_response

logger = logging.getLogger(__name__)

ROOT = find_repo_root(Path(__file__).resolve())
INPUT_DIR = ROOT / "data" / "input_midi"
OUTPUT_DIR = ROOT / "data" / "output_midi" / "generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="We Are All John Henry")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/generated", StaticFiles(directory=OUTPUT_DIR), name="generated")
app.mount("/inputs", StaticFiles(directory=INPUT_DIR), name="inputs")

SAMPLE_LIBRARY: list[dict[str, str | int]] = [
    {
        "file": "wrong_ensemble_ensemble_seed.mid",
        "name": "Wrong Ensemble Seed",
        "description": "A compact ensemble opening with a deliberately mismatched texture.",
        "instrument_count": 4,
    },
    {
        "file": "wrong_ensemble_chamber_seed.mid",
        "name": "Wrong Ensemble Chamber",
        "description": "A leaner ensemble variant with the same call-and-response character.",
        "instrument_count": 4,
    },
    {
        "file": "wrong_ensemble_takeover_seed.mid",
        "name": "Wrong Ensemble Takeover",
        "description": "Single-line material with a more overt takeover-style contour.",
        "instrument_count": 1,
    },
]


def safe_filename(name: str) -> str:
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in {"-", "_", "."}).strip("._")
    return cleaned or "response.mid"


def list_samples() -> list[dict[str, str | int]]:
    return [sample for sample in SAMPLE_LIBRARY if (INPUT_DIR / sample["file"]).exists()]


def run_generation(input_path: Path, output_name: str):
    output_path = OUTPUT_DIR / safe_filename(output_name)
    result = generate_response(input_path, output_path)
    return {
        "input_file": result.input_path.name,
        "output_file": result.output_path.name,
        "download_url": f"/generated/{result.output_path.name}",
        "features": result.features,
        "action": result.action,
        "source_instrument_name": result.source_instrument_name,
        "response_instrument_name": result.response_instrument_name,
        "response_note_count": result.response_note_count,
        "response_pitch_min": result.response_pitch_min,
        "response_pitch_max": result.response_pitch_max,
        "duration_seconds": result.duration_seconds,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {
        "title": "We Are All John Henry",
        "health": "/api/health",
        "samples": "/api/samples",
        "generate": "/api/generate",
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/samples")
def samples() -> dict[str, list[dict[str, str]]]:
    return {"samples": list_samples()}


@app.post("/api/generate")
async def generate(
    sample: str = Form(default="wrong_ensemble_ensemble_seed.mid"),
    output_name: str = Form(default="wrong_ensemble_response.mid"),
    midi_file: UploadFile | None = File(default=None),
):
    selected_input: Path
    temp_path: Path | None = None

    try:
        if midi_file and midi_file.filename:
            suffix = Path(midi_file.filename).suffix or ".mid"
            with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(await midi_file.read())
                temp_path = Path(temp_file.name)
            selected_input = temp_path
        else:
            selected_input = INPUT_DIR / sample

        if not selected_input.exists():
            raise HTTPException(status_code=404, detail=f"Input MIDI not found: {selected_input.name}")

        return run_generation(selected_input, output_name)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Generation failed for %s", selected_input if 'selected_input' in locals() else sample)
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
