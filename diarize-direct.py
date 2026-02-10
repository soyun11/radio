import torch
from pyannote.audio import Pipeline
import datetime
import time
import torchaudio
import sys
import os

# ==========================================
# 설정
# ==========================================
BASE_DIR = "/mnt/home_dnlab/jhjung/radio/baechulsu"

def run(date_str):
    audio_file = f"{BASE_DIR}/{date_str}/mp3/{date_str}.mp3"
    output_path = f"{BASE_DIR}/{date_str}/transcript/{date_str}_diarization.txt"

    # 출력 폴더가 없으면 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"🚀 [{date_str}] Pyannote 3.1 분석 시작...")

    try:
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        pipeline.to(device)
        print(f"✅ 사용 장치: {device}")

        # 2. 오디오 로드 및 전처리
        waveform, sample_rate = torchaudio.load(audio_file)

        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            waveform = resampler(waveform)

        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)

        start_time = time.time()

        # 3. 분석 실행
        diarization_output = pipeline({"waveform": waveform, "sample_rate": 16000})

        if hasattr(diarization_output, "speaker_diarization"):
            annotation = diarization_output.speaker_diarization
        else:
            annotation = diarization_output 

        end_time = time.time()

        # 4. 결과 저장
        with open(output_path, "w", encoding="utf-8") as f:
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                f.write(f"START={turn.start:.2f} STOP={turn.end:.2f} SPEAKER={speaker}\n")

        print(f"✨ 분석 성공! 소요시간: {end_time - start_time:.1f}초")
        print(f"📂 저장 완료: {output_path}")

    except Exception as e:
        print(f"❌ [{date_str}] 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diarize-direct.py <DATE>")
        sys.exit(1)
    
    run(sys.argv[1])
