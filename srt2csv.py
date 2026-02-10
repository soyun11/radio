import csv
import re
import sys
import os

def parse_timestamp(ts: str) -> float:
    h, m, s = ts.split(":")
    s, ms = s.split(",")
    total = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    return round(total, 3)

def determine_type(duration: float, transcript: str) -> str:
    """
    세그먼트 타입 결정
    - duration >= 60초: 음악 (텍스트가 있어도 - 팝송 가사 전사 케이스)
    - 텍스트 없음: silence 또는 music (gap에서 처리)
    - 그 외: speech
    """
    # 60초 이상이면 음악으로 판단 (가사가 전사되어도)
    if duration >= 35:
        return "music"
    
    # 텍스트가 비어있으면 silence
    if not transcript.strip():
        return "silence"
    
    return "speech"

def srt_to_csv(srt_file: str, csv_file: str):
    # SRT 패턴 (숫자 - 시간 - 내용 - 빈줄)
    pattern = re.compile(
        r"(\d+)\n(\d\d:\d\d:\d\d,\d\d\d) --> (\d\d:\d\d:\d\d,\d\d\d)\n(.+?)(?=\n\n|\Z)",
        re.S
    )

    if not os.path.exists(srt_file):
        print(f"❌ 파일을 찾을 수 없습니다: {srt_file}")
        return

    with open(srt_file, "r", encoding="utf-8") as f:
        srt_text = f.read()

    entries = pattern.findall(srt_text)

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Start Time", "Stop Time", "Duration",
            "Type", "MP3 File", "Transcript File", "Transcript"
        ])

        prev_stop = 0.0
        first = True

        for idx, start_ts, end_ts, text in entries:
            start_sec = parse_timestamp(start_ts)
            end_sec = parse_timestamp(end_ts)
            duration = round(end_sec - start_sec, 3)
            transcript = " ".join(line.strip() for line in text.split("\n")).strip()

            # GAP DETECTION (음악/침묵 구간)
            if not first and start_sec > prev_stop:
                gap_duration = round(start_sec - prev_stop, 3)
                # gap도 60초 기준으로 music/silence 판단
                gap_type = "music" if gap_duration >= 30 else "silence"
                writer.writerow([prev_stop, start_sec, gap_duration, gap_type, "", "", ""])

            first = False

            # 타입 결정 (duration 기반)
            row_type = determine_type(duration, transcript)
            
            writer.writerow([start_sec, end_sec, duration, row_type, "", "", transcript])
            prev_stop = end_sec

    print(f"✔ 변환 완료: {csv_file}")

if __name__ == "__main__":
    # 인자가 2개 미만일 때만 에러 처리 (입력 파일은 필수)
    if len(sys.argv) < 2:
        print("Usage: python srt2csv.py <file.srt> [output.csv]")
        sys.exit(1)

    srt_file = sys.argv[1]

    # 두 번째 인자(CSV 경로)가 들어오면 그걸 쓰고, 안 들어오면 자동으로 생성
    if len(sys.argv) >= 3:
        csv_file = sys.argv[2]
    else:
        csv_file = srt_file.replace(".srt", ".csv")

    srt_to_csv(srt_file, csv_file)
