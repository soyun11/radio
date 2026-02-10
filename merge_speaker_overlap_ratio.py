#!/usr/bin/env python3
import pandas as pd
import re
import sys
import os

# =====================================================
# diarization.txt 파싱
# =====================================================
def parse_diarization(file_path):
    segments = []
    pattern = re.compile(r"START=(\d+\.\d+) STOP=(\d+\.\d+) SPEAKER=(SPEAKER_\d+)")

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                start = float(m.group(1))
                stop = float(m.group(2))
                segments.append({
                    "start": start,
                    "stop": stop,
                    "speaker": m.group(3),
                    "duration": stop - start
                })
    return segments

# =====================================================
# Speaker 겹침 비율 계산
# =====================================================
def get_speaker_overlap_ratios(start, stop, diar_segments):
    overlap = {}
    total_overlap = 0.0

    for seg in diar_segments:
        overlap_start = max(start, seg["start"])
        overlap_stop = min(stop, seg["stop"])

        if overlap_start < overlap_stop:
            dur = overlap_stop - overlap_start
            overlap[seg["speaker"]] = overlap.get(seg["speaker"], 0.0) + dur
            total_overlap += dur

    if not overlap or total_overlap == 0:
        return ""

    parts = []
    for spk, dur in sorted(overlap.items(), key=lambda x: x[1], reverse=True):
        ratio = dur / total_overlap
        parts.append(f"{spk}:{dur:.2f}s({ratio:.3f})")

    return ";".join(parts)

# =====================================================
# ⭐ 안전한 Transcript 체크 함수
# =====================================================
def has_transcript(row):
    """
    Transcript가 실제로 있는지 안전하게 체크
    """
    transcript = row.get('Transcript', '')
    
    # NaN 체크
    if pd.isna(transcript):
        return False
    
    # 문자열 변환 후 체크
    transcript = str(transcript).strip()
    
    # 빈 문자열 체크
    if not transcript:
        return False
    
    # "nan" 문자열 체크
    if transcript.lower() == "nan":
        return False
    
    return True

# =====================================================
# CSV + diarization 병합
# =====================================================
def merge(csv_file, diar_file, output_file):
    print("📥 Loading CSV...")
    df = pd.read_csv(csv_file)
    
    print(f"   Columns: {df.columns.tolist()}")
    print(f"   Total: {len(df)} segments")

    print("\n📥 Loading Diarization...")
    diar_segments = parse_diarization(diar_file)
    print(f"   Total: {len(diar_segments)} speaker segments")
    
    speakers = set(seg['speaker'] for seg in diar_segments)
    print(f"   Speakers: {sorted(speakers)}")

    # Speakers 컬럼 초기화
    df["Speakers"] = ""

    # Step 1: speech → music 변환
    print("\n🎵 Converting empty-transcript speech to music...")
    empty_count = 0

    for idx, row in df.iterrows():
        if row["Type"] == "speech":
            if not has_transcript(row):  # ⭐ 안전한 체크
                df.at[idx, "Type"] = "music"
                empty_count += 1

    print(f"   ✅ Converted {empty_count} speech segments to music")

    # Step 2: Speaker 계산
    print("\n🔄 Calculating speaker ratios...")
    speaker_count = 0
    
    for idx, row in df.iterrows():
        # ⭐ Transcript 있을 때만 계산!
        if has_transcript(row):
            if row["Type"] in ["speech", "music"]:
                speakers_str = get_speaker_overlap_ratios(
                    row["Start Time"],
                    row["Stop Time"],
                    diar_segments
                )
                df.at[idx, "Speakers"] = speakers_str
                speaker_count += 1
    
    print(f"   ✅ Added speakers to {speaker_count} segments")

    # Step 3: 최종 검증
    print("\n🧹 Final validation...")
    cleaned_count = 0
    
    for idx, row in df.iterrows():
        if not has_transcript(row) and row["Speakers"]:
            df.at[idx, "Speakers"] = ""
            cleaned_count += 1
    
    print(f"   ✅ Cleaned {cleaned_count} segments")

    # Step 4: 저장
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"\n✅ Saved: {output_file}")
    print(f"   Total segments: {len(df)}")
    
    # 최종 검증
    print("\n🔍 Final check:")
    problem_count = 0
    for idx, row in df.iterrows():
        if not has_transcript(row) and row["Speakers"]:
            print(f"   ❌ [{row['Start Time']:.1f}] {row['Type']}: Speakers={row['Speakers'][:50]}")
            problem_count += 1
    
    if problem_count == 0:
        print("   ✅ Perfect! No problems found!")
    else:
        print(f"   ⚠️  Still {problem_count} problems!")

# =====================================================
# main
# =====================================================
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge_speaker_overlap_ratio.py <YYYYMMDD>")
        sys.exit(1)

    date_str = sys.argv[1]
    base_dir = f"/mnt/home_dnlab/jhjung/radio/baechulsu/{date_str}/transcript"
    
    csv_in = os.path.join(base_dir, f"{date_str}.csv")
    diar_in = os.path.join(base_dir, f"{date_str}_diarization.txt")
    out = os.path.join(base_dir, f"{date_str}_with_speaker_ratio.csv")
    
    if not os.path.exists(csv_in):
        print(f"❌ CSV not found: {csv_in}")
        sys.exit(1)
    
    if not os.path.exists(diar_in):
        print(f"❌ Diarization not found: {diar_in}")
        sys.exit(1)
    
    merge(csv_in, diar_in, out)