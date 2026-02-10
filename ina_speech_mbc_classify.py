import pandas as pd
import numpy as np
import librosa
import re
from tqdm import tqdm

# ===============================
# 1. 경로 설정
# ===============================

CSV_PATH = "/mnt/home_dnlab/jhjung/radio/jeongeunim/20260124/transcript/20260124_with_speaker_ratio.csv"
MP3_PATH = "/mnt/home_dnlab/jhjung/radio/jeongeunim/20260124/mp3/20260124.mp3"

SR = 32000

# ===============================
# 2. 보조 함수들
# ===============================

def get_speaker_ratio(speaker_str):
    """
    Speakers 컬럼에서 가장 지배적인 화자 비율 추출
    """
    if not isinstance(speaker_str, str):
        return 0.0

    ratios = re.findall(r"\((0\.\d+|1\.0+)\)", speaker_str)
    ratios = [float(r) for r in ratios]

    return max(ratios) if ratios else 0.0


def text_density(transcript, duration):
    """
    초당 문자 수
    """
    if not isinstance(transcript, str) or duration <= 0:
        return 0.0
    return len(transcript.strip()) / duration


def extract_spectral_features(y, sr):
    """
    speech / music 구분에 강력한 주파수 기반 특징
    """
    return {
        "bandwidth": float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))),
        "rolloff": float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))),
        "flatness": float(np.mean(librosa.feature.spectral_flatness(y=y))),
        "zcr": float(np.mean(librosa.feature.zero_crossing_rate(y)))
    }


def classify_speech_music(row, features):
    """
    최종 분류 함수 (speech / music)
    """
    duration = float(row["Duration"])
    transcript = str(row["Transcript"]) if pd.notna(row["Transcript"]) else ""
    speaker_ratio = get_speaker_ratio(row["Speakers"])
    density = text_density(transcript, duration)

    bw = features["bandwidth"]
    roll = features["rolloff"]
    flat = features["flatness"]

    # 1️⃣ 사람이 지배적이면 무조건 speech
    if speaker_ratio >= 0.6:
        return "speech"

    # 2️⃣ 음악의 물리적 특징 (가장 중요)
    if (
        bw > 2500 and
        roll > 6000 and
        flat > 0.15 and
        duration >= 15
    ):
        return "music"

    # 3️⃣ 말이 거의 없고 길면 music
    if density < 2.0 and duration >= 20:
        return "music"

    # 4️⃣ 그 외는 speech
    return "speech"


# ===============================
# 3. CSV 로드
# ===============================

df = pd.read_csv(CSV_PATH)

# silence 제거
df = df[df["Type"] != "silence"].reset_index(drop=True)

# ===============================
# 4. MP3 전체 로드 (한 번만)
# ===============================

print("▶ Loading full MP3...")
audio_full, _ = librosa.load(MP3_PATH, sr=SR, mono=True)
audio_full = audio_full.astype(np.float32)

# ===============================
# 5. 세그먼트별 분류
# ===============================

results = []

print("▶ Classifying segments (speech / music)...")

for _, row in tqdm(df.iterrows(), total=len(df)):
    start = float(row["Start Time"])
    end = float(row["Stop Time"])
    duration = float(row["Duration"])

    if duration < 1.0:
        continue

    s = int(start * SR)
    e = int(end * SR)

    seg_audio = audio_full[s:e]

    if len(seg_audio) < SR * 0.5:
        continue

    features = extract_spectral_features(seg_audio, SR)
    label = classify_speech_music(row, features)

    results.append({
        "start": start,
        "stop": end,
        "duration": duration,
        "label": label,
        "speaker_ratio": get_speaker_ratio(row["Speakers"]),
        "text_density": text_density(row["Transcript"], duration),
        "bandwidth": features["bandwidth"],
        "rolloff": features["rolloff"],
        "flatness": features["flatness"],
        "transcript": row["Transcript"]
    })

# ===============================
# 6. 결과 저장
# ===============================

out_df = pd.DataFrame(results)
out_path = CSV_PATH.replace(".csv", "_speech_music_spectral.csv")
out_df.to_csv(out_path, index=False, encoding="utf-8-sig")

print("✅ Saved:", out_path)

