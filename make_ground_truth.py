import pandas as pd
import re
import sys
import os
import argparse
import numpy as np

# ==========================================
# 1. 화자 정보 파싱 함수
# ==========================================
def get_dominant_speaker(speaker_str):
    if not isinstance(speaker_str, str) or not speaker_str.strip():
        return None
    parsed = []
    parts = speaker_str.split(';')
    for p in parts:
        m = re.match(r"(SPEAKER_\d+):[\d\.]+s\(([\d\.]+)\)", p.strip())
        if m:
            parsed.append((m.group(1), float(m.group(2))))
    if not parsed:
        return None
    parsed.sort(key=lambda x: x[1], reverse=True)
    return parsed[0][0]

# ==========================================
# 2. 화자 특성 분석 (Interaction & Count Only)
# ==========================================
def analyze_speaker_characteristics(df, role_map):
    speaker_sequence = [] 
    speaker_counts = {}

    # 1단계: 순서 및 빈도 수집
    for _, row in df.iterrows():
        spk = get_dominant_speaker(row.get('Speakers', ''))
        
        if spk:
            if spk not in speaker_counts:
                speaker_counts[spk] = 0
            speaker_counts[spk] += 1

            # 연속된 동일 화자 병합 (핑퐁 계산 정확도 향상)
            if not speaker_sequence or speaker_sequence[-1] != spk:
                speaker_sequence.append(spk)
    
    # 2단계: Interaction Rate 계산
    speaker_stats = {}
    unique_speakers = list(speaker_counts.keys())
    
    for spk in unique_speakers:
        interaction_count = 0
        my_turns = [i for i, x in enumerate(speaker_sequence) if x == spk]
        
        for idx in my_turns:
            prev_spk = speaker_sequence[idx-1] if idx > 0 else None
            next_spk = speaker_sequence[idx+1] if idx < len(speaker_sequence)-1 else None
            
            is_dj_nearby = False
            # 앞뒤에 DJ가 있으면 Interaction 인정
            if prev_spk and role_map.get(prev_spk) == 'DJ': is_dj_nearby = True
            if next_spk and role_map.get(next_spk) == 'DJ': is_dj_nearby = True
            
            if is_dj_nearby:
                interaction_count += 1
        
        interaction_rate = interaction_count / len(my_turns) if my_turns else 0

        speaker_stats[spk] = {
            'count': speaker_counts[spk],      # 총 등장 횟수
            'interaction_rate': interaction_rate # DJ와 대화 비율
        }
        
    return speaker_stats

# ==========================================
# 3. 라벨 결정 로직 (Guest vs AD 이분법)
# ==========================================
def decide_label(row, role_map, speaker_stats):
    seg_type = str(row.get('Type', '')).lower().strip()
    
    try:
        duration = float(row['Stop Time']) - float(row['Start Time'])
    except:
        duration = 0

    # 1. 비발화 구간
    if 'music' in seg_type: return 'Music'
    if 'silence' in seg_type: return 'Silence'

    # 2. 화자 식별
    dom_speaker = get_dominant_speaker(row.get('Speakers', ''))
    if not dom_speaker: return 'Program'

    # 3. 절대 기준 (DJ는 무조건 프리패스)
    role = role_map.get(dom_speaker, 'UNKNOWN')
    if role == 'DJ': return 'DJ'
    if role == 'AD_SPEAKER': return 'AD'

    # ----------------------------------------
    # [패턴 분석 로드]
    # ----------------------------------------
    stats = speaker_stats.get(dom_speaker, {'count': 0, 'interaction_rate': 0})
    count = stats['count']
    interaction_rate = stats['interaction_rate']

    # ----------------------------------------
    # [Step 1] 게스트(Guest) 인증
    # 조건: "DJ랑 20% 이상 대화" AND "5번 이상 등장"
    # -> 이 정도는 되어야 '출연자'라고 볼 수 있음.
    # ----------------------------------------
    is_guest = (interaction_rate >= 0.2) and (count >= 5)

    if is_guest:
        return 'Guest'

    # ----------------------------------------
    # [Step 2] 나머지는 전부 광고(AD)
    # 게스트가 아니면? -> 볼 것도 없이 광고/안내/ARS
    # ----------------------------------------
    
    # 아주 짧은 0.5초 멘트부터 허용 (최대 길이는 데이터상 60초 넘는게 없으므로 넉넉히 100초 줌)
    if 0.5 <= duration <= 100.0:
        return 'AD'

    # 여기까지 올 일은 거의 없지만, 안전장치로 Program 반환
    return 'Program'

# ==========================================
# 4. 실행 함수
# ==========================================
def process_date(date_str, base_path):
    print(f"🚀 Processing: {date_str} ...")
    
    transcript_dir = os.path.join(base_path, date_str, "transcript")
    input_csv = os.path.join(transcript_dir, f"{date_str}_with_speaker_ratio.csv")
    stats_csv = os.path.join(transcript_dir, f"{date_str}-dj_stats.csv")
    output_csv = os.path.join(transcript_dir, f"{date_str}-inference_result_ratio.csv")

    if not os.path.exists(input_csv) or not os.path.exists(stats_csv):
        print("  ❌ Files missing.")
        return

    df_data = pd.read_csv(input_csv)
    df_stats = pd.read_csv(stats_csv)
    role_map = dict(zip(df_stats['Speaker'], df_stats['Role']))

    print("  ⏱️  Analyzing speaker patterns (Simpler is Better)...")
    speaker_stats = analyze_speaker_characteristics(df_data, role_map)

    print("  🏷️  Applying final labels...")
    df_data['Predicted_Label'] = df_data.apply(
        lambda row: decide_label(row, role_map, speaker_stats), 
        axis=1
    )

    df_data.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"  ✅ Created: {output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("date", help="Target Date")
    parser.add_argument("--base_dir", default="/mnt/home_dnlab/jhjung/radio/baechulsu")
    args = parser.parse_args()

    if args.date == 'all':
        if not os.path.exists(args.base_dir): sys.exit(1)
        for d in sorted(os.listdir(args.base_dir)):
            if d.isdigit() and len(d) == 8: process_date(d, args.base_dir)
    else:
        process_date(args.date, args.base_dir)