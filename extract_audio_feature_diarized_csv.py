import os
import csv
import json
import argparse
import librosa
import numpy as np
from tqdm import tqdm

def extract_features(y, sr):
    if len(y) < 512:
        return [0.0] * 31
    try:
        rms = float(np.mean(librosa.feature.rms(y=y)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=y)))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
        flatness = float(np.mean(librosa.feature.spectral_flatness(y=y)))
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1).tolist()
        mfcc_std = np.std(mfcc, axis=1).tolist()
        return [rms, zcr, centroid, bandwidth, flatness] + mfcc_mean + mfcc_std
    except:
        return [0.0] * 31

def sliding_window_from_buffer(y_sub, sr, window_sec=1.0):
    win_len = int(window_sec * sr)
    all_features = []
    if len(y_sub) <= win_len:
        return [extract_features(y_sub, sr)]
    for start in range(0, len(y_sub) - win_len + 1, win_len):
        window = y_sub[start:start+win_len]
        all_features.append(extract_features(window, sr))
    return all_features

#def process_date(date_str, out_base_dir):
def process_date(date_str):
    # 경로 설정
    input_base_dir = f"/mnt/home_dnlab/jhjung/radio/jeongeunim/{date_str}"
    output_base_dir = f"/mnt/home_dnlab/jhjung/radio/jeongeunim/{date_str}/transcript"
    #output_base_dir = f"/home/yslee/ad_detection/diarize/mbc-test/{date_str}"
    csv_file = os.path.join(input_base_dir, "transcript", f"{date_str}_with_speaker.csv")
    mp3_file = os.path.join(input_base_dir, "mp3", f"{date_str}.mp3")
    
    # 출력 디렉토리 생성
    #os.makedirs(out_base_dir, exist_ok=True)
    out_file = os.path.join(output_base_dir, f"{date_str}_features.jsonl")
    #out_file = os.path.join(out_base_dir, f"{date_str}_features.jsonl")

    if not os.path.exists(csv_file):
        print(f"❌ CSV 없음: {csv_file}")
        return
    if not os.path.exists(mp3_file):
        print(f"❌ MP3 없음: {mp3_file}")
        return

    print(f"🚀 [{date_str}] 분석 시작... (저장처: {out_file})")
    y_full, sr = librosa.load(mp3_file, sr=16000)
    
    results_count = 0
    # encoding='utf-8-sig'를 사용하여 BOM 문제를 해결하고, 
    # strip()을 통해 컬럼명 공백 문제를 방지합니다.
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        # 컬럼명의 공백을 자동으로 제거하도록 설정
        reader = csv.DictReader(f)
        reader.fieldnames = [name.strip() for name in reader.fieldnames]

        with open(out_file, "w", encoding="utf-8") as fout:
            for row in tqdm(reader, desc="피처 추출 중"):
                try:
                    # 'Start Time' 키가 있는지 확인 후 데이터 추출
                    st = row.get("Start Time")
                    et = row.get("Stop Time")
                    if st is None or et is None: continue
                    
                    start_sec = float(st)
                    stop_sec = float(et)
                    
                    start_idx = int(start_sec * sr)
                    stop_idx = int(stop_sec * sr)
                    y_segment = y_full[start_idx:stop_idx]
                    
                    if len(y_segment) == 0: continue

                    features = sliding_window_from_buffer(y_segment, sr, window_sec=1.0)
                    record = {
                        "date": date_str,
                        "start": start_sec,
                        "stop": stop_sec,
                        "type": row.get("Type", ""),
                        "speaker": row.get("Speaker", ""),
                        "transcript": row.get("Transcript"),
                        "audio_features": features
                    }
                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                    results_count += 1
                except Exception as e:
                    # 구체적인 에러 확인용
                    # print(f"에러 내용: {e}") 
                    continue

    print(f"✅ 완료: {results_count}개 구간 저장 완료")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="날짜 (YYYYMMDD)")
    #parser.add_argument("--out_dir", required=True, help="결과를 저장할 디렉토리 경로")
    args = parser.parse_args()

    process_date(args.date)
    #process_date(args.date, args.out_dir)