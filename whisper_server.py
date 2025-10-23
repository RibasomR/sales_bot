"""
FastAPI сервер для локальной транскрибации аудио через Whisper.cpp.

Предоставляет REST API для обработки голосовых сообщений.
Используется как альтернатива OpenAI Whisper API.
Whisper.cpp обеспечивает 2-4x лучшую производительность.

:author: Finance Bot Team
:date: 2025-10-20
"""

import os
import tempfile
from typing import Optional

from pywhispercpp.model import Model
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="Whisper.cpp Transcription API", version="2.0.0")

## Load Whisper.cpp model at startup
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_THREADS = int(os.getenv("WHISPER_THREADS", "4"))

print(f"🎤 Загрузка модели Whisper.cpp: {WHISPER_MODEL} (потоков: {WHISPER_THREADS})")
model = Model(
    model=f"ggml-{WHISPER_MODEL}.bin",
    n_threads=WHISPER_THREADS
)
print("✅ Модель Whisper.cpp загружена успешно")


@app.get("/health")
async def health_check():
    """
    Проверка здоровья сервиса.
    
    :return: Статус сервиса
    :rtype: dict
    """
    return {
        "status": "healthy",
        "model": WHISPER_MODEL,
        "backend": "whisper.cpp",
        "threads": WHISPER_THREADS
    }


@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = "ru"
):
    """
    Транскрибирует аудио файл в текст.
    
    :param file: Аудио файл для транскрибации
    :type file: UploadFile
    :param language: Язык аудио (по умолчанию 'ru')
    :type language: str
    :return: Распознанный текст
    :rtype: dict
    
    :raises HTTPException: При ошибке обработки файла
    
    Example:
        >>> # POST /transcribe
        >>> # file: audio.ogg
        >>> # language: ru
        >>> {"text": "Расход 500 рублей на продукты"}
    """
    if not file:
        raise HTTPException(status_code=400, detail="Файл не предоставлен")
    
    # Проверка типа файла
    allowed_extensions = [".mp3", ".wav", ".ogg", ".m4a", ".flac"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдерживаемый формат файла. Разрешены: {allowed_extensions}"
        )
    
    try:
        # Save file to temporary directory
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Transcribe using Whisper.cpp
        result = model.transcribe(
            tmp_file_path,
            language=language
        )
        
        # Delete temporary file
        os.unlink(tmp_file_path)
        
        # Extract text from result
        text = result.strip() if isinstance(result, str) else result.get("text", "").strip()
        
        return JSONResponse({
            "text": text,
            "language": language
        })
    
    except Exception as e:
        # Очистка временного файла в случае ошибки
        if 'tmp_file_path' in locals():
            try:
                os.unlink(tmp_file_path)
            except:
                pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при транскрибации: {str(e)}"
        )


@app.get("/")
async def root():
    """
    Корневой endpoint с информацией об API.
    
    :return: Информация об API
    :rtype: dict
    """
    return {
        "service": "Whisper.cpp Transcription API",
        "version": "2.0.0",
        "model": WHISPER_MODEL,
        "backend": "whisper.cpp",
        "threads": WHISPER_THREADS,
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)"
        }
    }


