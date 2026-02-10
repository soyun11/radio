import os
import sys
import shutil
import subprocess

# ==========================================
# 설정
# ==========================================
PROGRAM_NAME = "baechulsu"
BASE_PATH = f"/mnt/home_dnlab/jhjung/radio/{PROGRAM_NAME}"

def run_command(cmd):
    """명령어 실행"""
    print(f"🚀 Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

def main(date_str):
    target_dir = os.path.join(BASE_PATH, date_str)
    mp3_dir = os.path.join(target_dir, "mp3")
    transcript_dir = os.path.join(target_dir, "transcript")
    
    original_mp3 = os.path.join(mp3_dir, f"{date_str}.mp3")
    vocals_mp3 = os.path.join(mp3_dir, f"{date_str}_vocals.mp3")
    
    print(f"🔥 Starting Pipeline for {date_str}...")

    # ==========================================
    # Step 0: 원본 파일 확인
    # ==========================================
    if not os.path.exists(original_mp3):
        print(f"❌ Original MP3 not found: {original_mp3}")
        sys.exit(1)

    # ==========================================
    # Step 1: Vocal 분리 (Diarization용만!)
    # ==========================================
    if not os.path.exists(vocals_mp3):
        print("🎵 [Step 1] Separating Vocals for Diarization...")
        
        temp_dir = os.path.join(mp3_dir, "temp_demucs")
        
        # Demucs 실행
        run_command(["python", "preprocess_vocals.py", original_mp3, temp_dir])
        
        # 분리된 vocal 파일 경로
        vocal_wav = os.path.join(temp_dir, "htdemucs", date_str, "vocals.wav")
        
        if not os.path.exists(vocal_wav):
            print(f"❌ Vocal file not found: {vocal_wav}")
            sys.exit(1)
        
        # Vocals를 MP3로 변환 (16kHz mono)
        run_command([
            "ffmpeg", "-i", vocal_wav,
            "-ac", "1",           # Mono
            "-ar", "16000",       # 16kHz
            "-b:a", "64k",        # 64kbps
            "-y",
            vocals_mp3
        ])
        print(f"   ✅ Created vocals MP3: {vocals_mp3}")
        
        # 임시 폴더 삭제
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    else:
        print("⚠️  Vocals MP3 already exists - skipping separation")

    # ==========================================
    # Step 2: Whisper 전사 (원본으로!)
    # ==========================================
    print("🗣️  [Step 2] Transcribing with Whisper (original audio)...")
    print("   ℹ️  Using original MP3 - music provides context!")
    run_command(["python", "whisper-direct.py", date_str])

    # ==========================================
    # Step 3: SRT → CSV 변환
    # ==========================================
    print("📝 [Step 3] Converting SRT to CSV...")
    srt_file = os.path.join(transcript_dir, f"{date_str}.srt")
    csv_file = os.path.join(transcript_dir, f"{date_str}.csv")
    run_command(["python", "srt2csv.py", srt_file, csv_file])

    # ==========================================
    # Step 4: Speaker Diarization (Vocals로!)
    # ==========================================
    print("👥 [Step 4] Running Speaker Diarization (vocals only)...")
    print("   ℹ️  Using clean vocals for better speaker separation")
    
    # diarize-direct.py가 기본으로 vocals 사용 (수정됨)
    run_command(["python", "diarize-direct.py", date_str])

    # ==========================================
    # Step 5-8: 나머지 파이프라인
    # ==========================================
    print("🔗 [Step 5] Merging Transcript and Diarization...")
    run_command(["python", "merge_speaker_overlap_ratio.py", date_str])

    print("🧠 [Step 6] Analyzing Roles...")
    run_command(["python", "dj_stat_ratio5.py", date_str])
    
    print("🧱 [Step 7] Merging Blocks...")
    run_command(["python", "dj_merge_block3.py", date_str])

    print("🏷️  [Step 8] Creating Ground Truth...")
    run_command(["python", "make_ground_truth.py", date_str])

    print(f"\n🎉 All Done for {date_str}!")
    print(f"\n📊 Summary:")
    print(f"   • Whisper: ✅ (used original MP3)")
    print(f"   • Diarization: ✅ (used vocals MP3)")
    print(f"   • Files created:")
    print(f"     - {original_mp3} (kept)")
    print(f"     - {vocals_mp3} (created)")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python auto_run.py <YYYYMMDD>")
        print("Example: python auto_run.py 20241124")
        sys.exit(1)
    
    main(sys.argv[1])