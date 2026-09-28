import asyncio
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..security import current_user
from ..services.policy import get_policy

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])


@lru_cache(maxsize=1)
def local_model():
    from faster_whisper import WhisperModel

    return WhisperModel(
        settings.speech_model,
        device="cpu",
        compute_type="int8",
        download_root=str(Path(settings.data_dir) / "models"),
        local_files_only=True,
    )


def transcribe_file(path: Path) -> dict:
    model = local_model()
    segments, info = model.transcribe(str(path), beam_size=3, vad_filter=True)
    text = " ".join(part.text.strip() for part in segments).strip()
    return {"text": text, "language": info.language, "language_probability": round(info.language_probability, 3), "provider": "local_faster_whisper", "requires_review": True}


@router.post("/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not get_policy(db)["feature_flags"]["voice"]:
        raise HTTPException(409, "Voice entry is disabled by platform policy")
    if file.content_type not in {"audio/webm", "audio/ogg", "audio/wav", "audio/mp4", "audio/mpeg"}:
        raise HTTPException(415, "Unsupported audio format")
    payload = await file.read(10 * 1024 * 1024 + 1)
    if len(payload) > 10 * 1024 * 1024:
        raise HTTPException(413, "Audio exceeds 10 MB")
    if len(payload) < 100:
        raise HTTPException(422, "Audio is too short")
    storage = Path(settings.data_dir) / "temporary_audio"
    storage.mkdir(parents=True, exist_ok=True)
    path = storage / f"{uuid.uuid4()}.audio"
    try:
        path.write_bytes(payload)
        try:
            result = await asyncio.to_thread(transcribe_file, path)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(503, "Local speech model unavailable. Continue by typing or install the speech model.") from exc
        if not result["text"]:
            raise HTTPException(422, "No speech was detected. You can type the request instead.")
        return result
    finally:
        path.unlink(missing_ok=True)
