import sys
import os
import pandas as pd
import tensorflow as tf

# ==========================================
# 🚀 GPU 설정 (충돌 방지 + 가속)
# ==========================================
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        # GPU 메모리를 처음부터 100% 잡지 말고, 필요할 때만 늘려가도록 설정
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f"✅ GPU Enabled: {len(gpus)} GPUs detected (Memory Growth ON)")
    except RuntimeError as e:
        print(f"⚠️ GPU Setup Error: {e}")
else:
    print("⚠️ No GPU detected. Running on CPU.")

# 경고 메시지 끄기
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
from inaSpeechSegmenter import Segmenter

def run_segmentation(input_file, output_csv):
    print(f"📂 Loading File: {input_file}")
    
    # 1. 모델 로드
    print("🔧 Loading Model (GPU Mode)...")
    try:
        # 배치 사이즈를 키우면 더 빨라지지만 메모리 터질 수 있음 (기본값 사용)
        seg = Segmenter(vad_engine='smn', detect_gender=True)
    except Exception as e:
        print(f"❌ Model Load Error: {e}")
        return

    print("🔍 Analyzing audio (Fast Mode)...")
    
    # 2. 분석 실행
    try:
        segmentation = seg(input_file)
    except Exception as e:
        print(f"❌ Segmentation Error: {e}")
        print("💡 팁: 만약 'CUDNN_STATUS_INTERNAL_ERROR' 같은 게 뜨면 GPU 메모리 부족입니다.")
        return
    
    # 3. 결과 정리
    results = []
    print("📝 Processing Results...")
    
    for label, start, end in segmentation:
        # 라벨 정리
        category = "OTHER"
        if label in ["male", "female"]:
            category = "SPEAKER"
        elif label == "music":
            category = "MUSIC"
        elif label == "noise":
            category = "NOISE"
            
        results.append({
            "Start": round(start, 2),
            "Stop": round(end, 2),
            "Duration": round(end - start, 2),
            "Label": label,
            "Category": category
        })
    
    # 4. CSV 저장
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    print("\n" + "="*50)
    print(f"📊 Analysis Result (Top 5)")
    print("-" * 50)
    print(df.head(5).to_string(index=False))
    print("=" * 50)
    print(f"✅ Saved to: {output_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_ina.py <input.mp3> [output.csv]")
        sys.exit(1)
        
    input_path = sys.argv[1]
    
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        output_path = input_path.rsplit('.', 1)[0] + "_ina.csv"
    
    if not os.path.exists(input_path):
        print(f"❌ File not found: {input_path}")
        sys.exit(1)
        
    run_segmentation(input_path, output_path)