# convert_features_to_csv.py
import json
import pandas as pd
import numpy as np
import argparse
import os

def describe_energy(rms):
    """RMS 값을 자연어로"""
    if rms > 0.3:
        return "Very high energy detected (music or loud speech)"
    elif rms > 0.15:
        return "High energy speech detected"
    elif rms > 0.05:
        return "Normal speech energy level"
    else:
        return "Low energy (silence or background noise)"

def describe_spectral(centroid, zcr, bandwidth):
    """스펙트럴 특성 설명"""
    if centroid > 5000 and zcr > 0.2:
        return "Bright, high-frequency content (music or commercial)"
    elif centroid > 3000 and bandwidth > 2500:
        return "Moderate spectral brightness with wide bandwidth (speech with music)"
    elif centroid > 3000:
        return "Moderate spectral brightness (animated speech)"
    else:
        return "Low spectral brightness (pure speech)"

def describe_stability(mfcc_std_avg):
    """안정성 설명 (MFCC 표준편차 평균)"""
    if mfcc_std_avg > 50:
        return "Highly variable acoustic pattern (music/advertisement)"
    elif mfcc_std_avg > 25:
        return "Moderate variation (animated speech or background music)"
    else:
        return "Stable acoustic pattern (calm speech)"

def summarize_audio(rms, zcr, centroid, bandwidth, flatness):
    """전체 요약"""
    if rms > 0.25 and zcr > 0.15 and bandwidth > 3000:
        return "Likely music or advertisement: high energy with complex frequency spectrum"
    elif rms > 0.20 and centroid > 4000:
        return "Energetic content with bright timbre, possibly commercial"
    elif rms < 0.1 and centroid < 2500 and bandwidth < 2000:
        return "Likely DJ speech: stable, moderate energy with narrow spectrum"
    elif bandwidth > 3500:
        return "Complex audio with wide frequency range suggesting mixed content"
    elif flatness > 0.1:
        return "Noisy characteristics suggesting background music or transition"
    else:
        return "Simple speech pattern with consistent characteristics"

def convert_jsonl_to_csv(jsonl_path, output_csv):
    """JSONL → CSV 변환 (자연어 설명 추가)"""
    
    rows = []
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            
            # audio_features는 리스트의 리스트 (각 윈도우별)
            features_list = record['audio_features']
            
            if not features_list or len(features_list) == 0:
                continue
                
            # 모든 윈도우의 평균 계산
            avg_features = np.mean(features_list, axis=0)
            
            # 특성 추출 (extract_features.py 순서대로)
            rms = avg_features[0]
            zcr = avg_features[1]
            centroid = avg_features[2]
            bandwidth = avg_features[3]
            flatness = avg_features[4]
            mfcc_mean = avg_features[5:18]   # 13개
            mfcc_std = avg_features[18:31]   # 13개
            
            mfcc_std_avg = np.mean(mfcc_std)
            
            # 자연어 설명 생성
            row = {
                'start': record['start'],
                'stop': record['stop'],
                'type': record.get('type', ''),
                'speaker': record.get('speaker', ''),
                'transcript': record.get('transcript', ''),
                
                # classify_audio_text.py에서 사용하는 컬럼들
                'speech_energy_desc': describe_energy(rms),
                'spectral_desc': describe_spectral(centroid, zcr, bandwidth),
                'stability_desc': describe_stability(mfcc_std_avg),
                'audio_summary': summarize_audio(rms, zcr, centroid, bandwidth, flatness),
                
                # 원본 숫자값도 보관
                'rms': round(rms, 4),
                'zcr': round(zcr, 4),
                'centroid': round(centroid, 2),
                'bandwidth': round(bandwidth, 2),
                'flatness': round(flatness, 4),
                'mfcc_std_avg': round(mfcc_std_avg, 2)
            }
            
            rows.append(row)
    
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"✅ 변환 완료: {len(df)}개 구간")
    print(f"   입력: {jsonl_path}")
    print(f"   출력: {output_csv}")
    return len(df)

def process_date(date_str):
    """특정 날짜 처리"""
    # 경로 설정
    base_dir = f"/mnt/home_dnlab/jhjung/radio/jeongeunim/{date_str}"
    transcript_dir = os.path.join(base_dir, "transcript")
    
    # 입력/출력 파일
    jsonl_file = os.path.join(transcript_dir, f"{date_str}_features.jsonl")
    output_csv = os.path.join(transcript_dir, f"{date_str}_audio_features_speech_music_spectral.csv")
    
    # 파일 존재 확인
    if not os.path.exists(jsonl_file):
        print(f"❌ JSONL 파일 없음: {jsonl_file}")
        print(f"   먼저 extract_features.py를 실행하세요:")
        print(f"   python extract_features.py --date {date_str}")
        return
    
    print(f"🚀 [{date_str}] JSONL → CSV 변환 시작...")
    convert_jsonl_to_csv(jsonl_file, output_csv)
    print(f"✅ 완료! 이제 classify_audio_text.py를 실행할 수 있습니다.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSONL 특성 파일을 CSV로 변환 (자연어 설명 추가)")
    parser.add_argument("--date", required=True, help="날짜 (YYYYMMDD)")
    args = parser.parse_args()
    
    process_date(args.date)