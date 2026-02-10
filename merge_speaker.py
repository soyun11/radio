import pandas as pd
import re
import sys

def parse_diarization(file_path):
    """diarization.txt 파일을 읽어 리스트로 반환"""
    segments = []
    # START=0.03 STOP=1.03 SPEAKER=SPEAKER_26 패턴 추출
    pattern = re.compile(r"START=(\d+\.\d+) STOP=(\d+\.\d+) SPEAKER=(SPEAKER_\d+)")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                segments.append({
                    'start': float(match.group(1)),
                    'stop': float(match.group(2)),
                    'speaker': match.group(3)
                })
    return segments

def get_best_speaker(start, stop, diar_segments):
    """특정 시간대(start~stop)에 가장 많이 겹치는 화자를 반환"""
    overlap_dict = {}
    
    for seg in diar_segments:
        # 두 구간이 겹치는 영역 계산
        overlap_start = max(start, seg['start'])
        overlap_stop = min(stop, seg['stop'])
        
        if overlap_start < overlap_stop:
            duration = overlap_stop - overlap_start
            overlap_dict[seg['speaker']] = overlap_dict.get(seg['speaker'], 0) + duration
            
    if not overlap_dict:
        return "UNKNOWN"
    
    # 가장 오래 말한 화자 반환
    return max(overlap_dict, key=overlap_dict.get)

def merge(csv_file, diar_file, output_file):
    # 1. 데이터 로드
    df = pd.read_csv(csv_file)
    diar_segments = parse_diarization(diar_file)
    
    # 2. Speaker 컬럼 추가 (기본값 설정)
    df['Speaker'] = ""
    
    # 3. Speech 타입인 경우에만 화자 매핑
    for idx, row in df.iterrows():
        if row['Type'] == 'speech':
            speaker = get_best_speaker(row['Start Time'], row['Stop Time'], diar_segments)
            df.at[idx, 'Speaker'] = speaker
        else:
            # music이나 silence 구간은 화자 정보 제외
            df.at[idx, 'Speaker'] = ""
            
    # 컬럼 순서 조정 (Speaker를 앞쪽으로)
    cols = ['Start Time', 'Stop Time', 'Duration', 'Type', 'Speaker', 'Transcript']
    # 기존에 있던 MP3 File 등 다른 컬럼이 있다면 유지하기 위해 존재하는 컬럼만 필터링
    df = df[[c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]]
    
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✅ 병합 완료: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python merge_speaker.py <file.csv> <diarization.txt>")
        sys.exit(1)
        
    csv_in = sys.argv[1]
    diar_in = sys.argv[2]
    out = csv_in.replace(".csv", "_with_speaker.csv")
    
    merge(csv_in, diar_in, out)
