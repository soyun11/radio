import pandas as pd
import re
import sys
import os

def get_dominant_speaker(speaker_str):
    if not isinstance(speaker_str, str): return None
    m = re.search(r"(SPEAKER_\d+)", speaker_str)
    return m.group(1) if m else None

def calculate_stats_simple(df):
    """
    간단한 로직:
    1. 발화량 1위 = DJ
    2. DJ와 interaction 압도적 1위 = GUEST
    3. 나머지 = AD_SPEAKER
    """
    # Dominant Speaker 컬럼 추가
    df['Dominant_Speaker'] = df.apply(
        lambda row: get_dominant_speaker(row.get('Speakers', '')) if row['Type'] == 'speech' else None,
        axis=1
    )
    
    # 화자별 총 발화 시간 계산
    duration_stats = {}
    for _, row in df.iterrows():
        if row['Type'] != 'speech': continue
        spk = row['Dominant_Speaker']
        if spk:
            duration_stats[spk] = duration_stats.get(spk, 0.0) + row['Duration']
    
    # DJ 선정 (발화량 1위)
    sorted_durations = sorted(duration_stats.items(), key=lambda x: x[1], reverse=True)
    if not sorted_durations:
        return pd.DataFrame()
    
    dj_id = sorted_durations[0][0]
    dj_duration = sorted_durations[0][1]
    print(f"👑 DJ Identified: {dj_id} (Duration: {dj_duration:.1f}s)")
    
    # 화자별 DJ와의 interaction 카운트
    speaker_indices = {spk: [] for spk in duration_stats.keys()}
    for idx, row in df.iterrows():
        if row['Type'] != 'speech': continue
        spk = row['Dominant_Speaker']
        if spk:
            speaker_indices[spk].append(idx)
    
    interaction_counts = {}
    for spk, indices in speaker_indices.items():
        if spk == dj_id:
            interaction_counts[spk] = 0  # DJ 자신은 카운트 안함
            continue
        
        count = 0
        for idx in indices:
            # 앞뒤 세그먼트에 DJ 있으면 카운트
            for offset in [-3, -2, -1, 1, 2, 3]:
                neighbor_idx = idx + offset
                if 0 <= neighbor_idx < len(df):
                    neighbor_spk = df.iloc[neighbor_idx].get('Dominant_Speaker')
                    if neighbor_spk == dj_id:
                        count += 1
                        break
        
        interaction_counts[spk] = count
    
    # Interaction 순위 정렬
    sorted_interactions = sorted(
        [(spk, cnt) for spk, cnt in interaction_counts.items() if spk != dj_id],
        key=lambda x: x[1], 
        reverse=True
    )
    
    print(f"\n📊 Interaction Rankings:")
    for i, (spk, cnt) in enumerate(sorted_interactions[:5], 1):
        print(f"   {i}. {spk}: {cnt} interactions")
    
    # 게스트 판별: interaction 1위가 2위보다 압도적으로 많으면
    guest_id = None
    if len(sorted_interactions) >= 2:
        first_spk, first_count = sorted_interactions[0]
        second_spk, second_count = sorted_interactions[1]
        
        # 2배 이상 차이나면 압도적 1위
        if first_count >= 2 * second_count and first_count >= 7:
            guest_id = first_spk
            print(f"\n✅ GUEST Detected: {guest_id} ({first_count} interactions, 2nd place: {second_count})")
        else:
            print(f"\n⚠️  No clear GUEST (1st: {first_count}, 2nd: {second_count})")
    elif len(sorted_interactions) == 1:
        # 화자가 DJ 포함 2명뿐이면 나머지 1명은 게스트
        first_spk, first_count = sorted_interactions[0]
        if first_count >= 7:
            guest_id = first_spk
            print(f"\n✅ GUEST Detected: {guest_id} ({first_count} interactions, only non-DJ speaker)")
    
    # 결과 생성
    results = []
    for spk, total_dur in sorted_durations:
        is_dj = (spk == dj_id)
        is_guest = (spk == guest_id)
        
        if is_dj:
            role = "DJ"
        elif is_guest:
            role = "GUEST"
        else:
            role = "AD_SPEAKER"
        
        ratio_to_dj = (total_dur / dj_duration * 100) if not is_dj else 100.0
        interact_count = interaction_counts.get(spk, 0)
        
        results.append({
            'Speaker': spk,
            'Role': role,
            'Total_Duration': round(total_dur, 2),
            'Ratio_to_DJ': f"{ratio_to_dj:.1f}%",
            'Interaction_Count': interact_count
        })
    
    return pd.DataFrame(results)

# ==========================================
# MAIN
# ==========================================
def main():
    if len(sys.argv) != 2:
        print("Usage: python dj_stat_interaction.py <YYYYMMDD>")
        sys.exit(1)

    date = sys.argv[1]
    base_dir = f"/mnt/home_dnlab/jhjung/radio/baechulsu/{date}/transcript"

    input_csv = os.path.join(base_dir, f"{date}_with_speaker_ratio.csv")
    output_csv = os.path.join(base_dir, f"{date}-dj_stats.csv")

    if not os.path.exists(input_csv):
        print(f"❌ Input not found: {input_csv}")
        sys.exit(1)

    print(f"📥 Loading {input_csv}...")
    df = pd.read_csv(input_csv)

    print("📊 Simple Analysis: DJ + Interaction-based GUEST detection")
    stats_df = calculate_stats_simple(df)
    
    print("\n" + "="*70)
    print(stats_df.to_string(index=False))
    print("="*70)
    
    # 역할별 요약
    print("\n📈 Role Summary:")
    print(stats_df['Role'].value_counts())
    
    stats_df.to_csv(output_csv, index=False)
    print(f"\n💾 Saved to {output_csv}")

if __name__ == "__main__":
    main()