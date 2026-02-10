#!/usr/bin/env python3
import pandas as pd
import re
import sys
import os

############################################
# 유틸
############################################
def extract_speakers(speaker_field):
    speakers = set()
    if not isinstance(speaker_field, str):
        return speakers
    for part in speaker_field.split(";"):
        m = re.match(r"(SPEAKER_\d+):", part.strip())
        if m:
            speakers.add(m.group(1))
    return speakers

############################################
# 간단한 블록 타입 판정 (4가지만!)
############################################
def decide_block_type(rows, speaker_role_map):
    speakers = set()
    total_duration = sum(r["Duration"] for r in rows)

    music_duration = 0.0
    speech_duration = 0.0

    for r in rows:
        if r["Type"] == "music":
            music_duration += r["Duration"]
        elif r["Type"] == "speech":
            speech_duration += r["Duration"]
            speakers |= extract_speakers(r.get("Speakers", ""))

    music_ratio = music_duration / max(total_duration, 1e-6)
    roles = set(speaker_role_map.get(s, "MINOR") for s in speakers)

    has_dj = "DJ" in roles
    has_guest = "GUEST" in roles
    has_ad = "AD_SPEAKER" in roles

    # 🎵 RULE 1: 음악 (최우선)
    if music_duration >= 60 or music_ratio >= 0.7:
        return "MUSIC"

    # 🗣️ RULE 2: 게스트 (DJ + GUEST 또는 GUEST만)
    if has_guest:
        return "GUEST"

    # 🎙️ RULE 3: DJ
    if has_dj:
        return "DJ"

    # 📢 RULE 4: 광고
    if has_ad or speech_duration > 0:
        return "AD"

    # 🎵 RULE 5: Speech 없고 Music만
    if speech_duration == 0 and music_duration > 0:
        return "MUSIC"

    # Fallback
    return "AD"

############################################
# Block Merge
############################################
def merge_blocks(df, speaker_role_map):
    blocks = []
    current = []
    last_type = None

    def flush():
        if not current:
            return

        block_type = decide_block_type(current, speaker_role_map)

        speakers_in_block = set().union(*[
            extract_speakers(r.get("Speakers", "")) for r in current
        ])

        blocks.append({
            "block_type": block_type,
            "start": current[0]["Start Time"],
            "end": current[-1]["Stop Time"],
            "duration": round(sum(r["Duration"] for r in current), 2),
            "segments": len(current),
            "speaker_count": len(speakers_in_block),
            "speakers": ",".join(sorted(speakers_in_block)),
            "text": " ".join(
                str(r["Transcript"]) for r in current
                if r["Type"] == "speech" and isinstance(r["Transcript"], str)
            )
        })
        current.clear()

    for _, row in df.iterrows():
        # Silence: flush
        if row["Type"] == "silence":
            flush()
            last_type = "silence"
            continue
        
        # Type 바뀌면 flush
        if last_type and row["Type"] != last_type:
            flush()
        
        current.append(row)
        last_type = row["Type"]

    flush()
    return pd.DataFrame(blocks)

############################################
# 연속된 같은 타입 블록 병합
############################################
def merge_consecutive_same_blocks(blocks_df):
    if len(blocks_df) == 0:
        return blocks_df
    
    merged = []
    current = blocks_df.iloc[0].to_dict()
    
    for i in range(1, len(blocks_df)):
        row = blocks_df.iloc[i]
        
        # 같은 타입이면 합치기
        if row["block_type"] == current["block_type"]:
            current["end"] = row["end"]
            current["duration"] = round(current["end"] - current["start"], 2)
            current["segments"] += row["segments"]
            
            # Speaker 합치기
            curr_speakers = set(current["speakers"].split(",")) if current["speakers"] else set()
            new_speakers = set(row["speakers"].split(",")) if row["speakers"] else set()
            current["speakers"] = ",".join(sorted(curr_speakers | new_speakers))
            current["speaker_count"] = len(curr_speakers | new_speakers)
            
            # Text 합치기
            if row["text"]:
                current["text"] = (current["text"] + " " + row["text"]).strip()
        else:
            merged.append(current)
            current = row.to_dict()
    
    merged.append(current)
    return pd.DataFrame(merged)

############################################
# MAIN
############################################
def main():
    if len(sys.argv) != 2:
        print("Usage: python dj_merge_block3.py <YYYYMMDD>")
        sys.exit(1)

    date = sys.argv[1]
    base_dir = f"/mnt/home_dnlab/jhjung/radio/baechulsu/{date}/transcript"

    input_csv = os.path.join(base_dir, f"{date}_with_speaker_ratio.csv")
    dj_csv = os.path.join(base_dir, f"{date}-dj_stats.csv")
    output_csv = os.path.join(base_dir, f"{date}-blocks.csv")

    if not os.path.exists(input_csv):
        print(f"❌ Input CSV not found: {input_csv}")
        sys.exit(1)

    if not os.path.exists(dj_csv):
        print(f"❌ DJ stats CSV not found: {dj_csv}")
        sys.exit(1)

    print(f"📥 Loading segments: {input_csv}")
    df = pd.read_csv(input_csv)

    print(f"🎙 Loading DJ stats: {dj_csv}")
    dj_df = pd.read_csv(dj_csv)

    # Speaker → Role 맵
    speaker_role_map = dict(zip(dj_df["Speaker"], dj_df["Role"]))

    print("🧱 Merging blocks (simplified: AD/MUSIC/DJ/GUEST)...")
    blocks = merge_blocks(df, speaker_role_map)

    print("🔗 Merging consecutive same-type blocks...")
    blocks = merge_consecutive_same_blocks(blocks)

    blocks.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ Saved blocks → {output_csv}")
    print("\n📊 Block Summary:")
    print(blocks["block_type"].value_counts())
    print(f"\nTotal blocks: {len(blocks)}")

if __name__ == "__main__":
    main()