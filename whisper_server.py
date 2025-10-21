"""
FastAPI сервер для локальной транскрибации аудио через Whisper.

Предоставляет REST API для обработки голосовых сообщений.
Используется как альтернатива OpenAI Whisper API.

:author: Finance Bot Team
:date: 2025-10-20
"""

import os
import tempfile
from typing import Optional

import whisper
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import torch

app = FastAPI(title="Whisper Transcription API", version="1.0.0")

## Загрузка модели Whisper при старте
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")

# Проверка доступности CUDA
if WHISPER_DEVICE == "cuda" and not torch.cuda.is_available():
    WHISPER_DEVICE = "cpu"
    print("⚠️ CUDA недоступна, используется CPU")

print(f"🎤 Загрузка модели Whisper: {WHISPER_MODEL} на устройстве: {WHISPER_DEVICE}")
model = whisper.load_model(WHISPER_MODEL, device=WHISPER_DEVICE)
print("✅ Модель Whisper загружена успешно")


@app.get("/health")
async def health_check():
    """
    Проверка здоровья сервиса.
    
    :return: Статус сервиса
    :rtype: dict
    """
    return {"status": "healthy", "model": WHISPER_MODEL, "device": WHISPER_DEVICE}


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
        # Сохранение файла во временную директорию
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        # Транскрибация
        result = model.transcribe(
            tmp_file_path,
            language=language,
            fp16=False  # Отключаем fp16 для CPU
        )
        
        # Удаление временного файла
        os.unlink(tmp_file_path)
        
        return JSONResponse({
            "text": result["text"].strip(),
            "language": result.get("language", language)
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
        "service": "Whisper Transcription API",
        "version": "1.0.0",
        "model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
        "endpoints": {
            "health": "/health",
            "transcribe": "/transcribe (POST)"
        }
    }


