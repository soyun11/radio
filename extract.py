from faster_whisper import WhisperModel

def transcribe_mp3(audio_path, output_path=None, language="ko"):
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segments, info = model.transcribe(audio_path, language=language)
    
    results = []
    full_text = []
    
    for segment in segments:
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        full_text.append(segment.text)
    
    # 파일로 저장
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(f"[{r['start']:.2f} - {r['end']:.2f}] {r['text']}\n")
    
    return {
        "segments": results,
        "full_text": "".join(full_text),
        "language": info.language
    }

# 사용
result = transcribe_mp3("rl.m4a", "output.txt")
print(result["full_text"])
