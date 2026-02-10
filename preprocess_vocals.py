import os
import sys
import subprocess
from pathlib import Path

def separate_vocals(input_path, output_dir):
    """
    Demucs를 이용해 목소리(vocals)와 배경음(noises)을 분리
    """
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"❌ Input missing: {input_path}")
        return None

    print(f"🎵 Separating Vocals: {input_file.name}...")
    
    # Demucs 실행 (htdemucs 모델, 2 stems)
    cmd = [
        "demucs",
        "--two-stems=vocals",
        "-n", "htdemucs",
        "-o", str(output_dir),
        str(input_file)
    ]
    
    try:
        subprocess.run(cmd, check=True)
        # 생성된 파일 위치 찾기 (htdemucs/파일명/vocals.wav)
        model_name = "htdemucs"
        song_name = input_file.stem
        vocal_wav = Path(output_dir) / model_name / song_name / "vocals.wav"
        
        if vocal_wav.exists():
            return str(vocal_wav)
    except Exception as e:
        print(f"❌ Demucs Error: {e}")
    
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python preprocess.py <input_mp3> <output_dir>")
        sys.exit(1)
    
    separate_vocals(sys.argv[1], sys.argv[2])