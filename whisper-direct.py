#!/usr/bin/env python3
import torch
from faster_whisper import WhisperModel
import os
import sys
import re

# ============================================================
# 1. Timestamp Formatter
# ============================================================
def format_timestamp(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hrs:02}:{mins:02}:{secs:02},{millis:03}"

# ============================================================
# 2. Hard Filter (환각 방지용 강력 필터)
# ============================================================
def is_hallucination(text):
    """
    Whisper 모델이 음악/무음 구간에서 자주 뱉는 환각(Hallucination) 키워드 필터링
    """
    text = text.strip()
    
    # 1. 너무 짧거나 특수문자만 있는 경우 삭제
    if len(text) < 2:
        return True
    
    # 2. 블랙리스트 (라디오/음악 환각 전용)
    blacklist = [
        "한글자막", "자막 by", "Subtitle",
        "시청해 주셔서", "구독과 좋아요", "알림 설정", "좋아요", "구독",
        "다음 주에 만나요", "다음 영상에서"
    ]
    
    for word in blacklist:
        # 대소문자 무시하고 포함 여부 확인
        if word.lower() in text.lower():
            # 문장이 너무 짧은데(10글자 미만) 저 단어가 포함되면 100% 환각
            if len(text) < 15:
                return True
            # 문장이 길더라도 'MBC 라디오입니다' 같이 딱 떨어지면 환각
            if text == word:
                return True

    # 3. 반복 문자 필터링 (예: ".......", "!!!!", "으으으으")
    if len(text) > 5 and len(set(text)) < 3:
        return True
    
    # 4. 반복 구문 필터링 (예: "행복하세요 행복하세요 행복하세요")
    if len(text) > 20:
        words = text.split()
        if len(words) > 4 and len(set(words)) < len(words) / 2:
            return True
        
    return False

# ============================================================
# 3. Main Execution
# ============================================================
if len(sys.argv) != 2:
    print("Usage: python whisper-direct.py <date_or_filepath>")
    print("Example 1: python whisper-direct.py 20260131")
    print("Example 2: python whisper-direct.py /path/to/audio.mp3")
    exit(1)

INPUT_ARG = sys.argv[1]

# 입력이 날짜인지 파일 경로인지 판단하여 경로 설정
if os.path.isfile(INPUT_ARG):
    # 직접 파일 경로를 입력받은 경우
    AUDIO_FILE = INPUT_ARG
    BASE_DIR = os.path.dirname(os.path.dirname(AUDIO_FILE)) # ../../
    DATE = os.path.splitext(os.path.basename(AUDIO_FILE))[0]
    OUTPUT_DIR = os.path.join(os.path.dirname(AUDIO_FILE), "../transcript")
else:
    # 날짜(YYYYMMDD)만 입력받은 경우 (기본 설정)
    DATE = INPUT_ARG
    # ★ 주의: 본인 환경에 맞게 baechulsu 또는 jeongeunim 수정 필요 ★
    BASE_DIR = f"/mnt/home_dnlab/jhjung/radio/baechulsu/{DATE}"
    AUDIO_FILE = f"{BASE_DIR}/mp3/{DATE}.mp3"
    OUTPUT_DIR = f"{BASE_DIR}/transcript"

# 출력 폴더 생성
os.makedirs(OUTPUT_DIR, exist_ok=True)

OUTPUT_TEXT = f"{OUTPUT_DIR}/{DATE}.txt"
OUTPUT_SRT = f"{OUTPUT_DIR}/{DATE}.srt"

if not os.path.exists(AUDIO_FILE):
    print(f"❌ Audio file not found: {AUDIO_FILE}")
    exit(1)

# 모델 설정
WHISPER_MODEL_SIZE = "large-v3"
LANGUAGE = "ko"
USE_VAD = True

print("🚀 Loading faster-whisper model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# 모델 로드 (float16 사용으로 속도 최적화)
model = WhisperModel(
    WHISPER_MODEL_SIZE,
    device=device,
    compute_type="float16"
)

print(f"\n▶ Starting transcription for: {AUDIO_FILE}")
print(f"Model: {WHISPER_MODEL_SIZE} | Language: {LANGUAGE} | VAD: {USE_VAD}")

# ============================================================
# 4. Transcribe (튜닝된 파라미터)
# ============================================================
segments, info = model.transcribe(
    AUDIO_FILE,
    language=LANGUAGE,
    beam_size=5,
    best_of=5,
    
    # [VAD] 0.5초 이상의 침묵은 무시 (Demucs로 음악이 지워진 구간 스킵용)
    vad_filter=USE_VAD,
    vad_parameters=dict(min_silence_duration_ms=500),


    # [중요] 이전 문맥 참조 끄기 (음악 구간 반복 생성 방지)
    condition_on_previous_text=False,

    # [중요] 프롬프트 엔지니어링 (환각 억제)
    initial_prompt="라디오 방송입니다. 음악을 제외한 모든 발화를 전사합니다.",

    # [탐색] 인식이 잘 안 될 때 온도를 높여가며 재시도
    temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],

    # [필터] 반복 패널티
    repetition_penalty=1.2,
    no_speech_threshold=0.6,
    
    word_timestamps=True
)

print("\n🎤 Transcription Completed!")
print(f"Detected language: {info.language} ({info.language_probability:.2f})")
print(f"Duration: {info.duration:.2f} sec")

# ============================================================
# 5. Save Output
# ============================================================
print(f"\n💾 Saving output...")

with open(OUTPUT_TEXT, "w", encoding="utf-8") as f_text, \
     open(OUTPUT_SRT, "w", encoding="utf-8") as f_srt:

    seg_idx = 1
    hallucination_count = 0

    for seg in segments:
        start = seg.start
        end = seg.end
        text = seg.text.strip()

        if not text:
            continue
            
        # 환각 필터링
        if is_hallucination(text):
            hallucination_count += 1
            continue

        # TXT 저장
        f_text.write(f"[{format_timestamp(start)} → {format_timestamp(end)}] {text}\n")

        # SRT 저장
        f_srt.write(f"{seg_idx}\n")
        f_srt.write(f"{format_timestamp(start)} --> {format_timestamp(end)}\n")
        f_srt.write(f"{text}\n\n")

        seg_idx += 1

print("\n🎉 ALL DONE!")
print(f"Filtered {hallucination_count} hallucination segments.")
print(f"Check output files:\n  {OUTPUT_TEXT}\n  {OUTPUT_SRT}")