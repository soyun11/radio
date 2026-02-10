import sys
import subprocess
import os
from datetime import datetime, timedelta

# ==========================================
# 설정
# ==========================================
START_DATE = "20241126"
END_DATE   = "20241224"

# 데이터가 있는 기본 경로 (파일 존재 확인용)
# 배철수인지 정은임인지 확인해서 수정하세요
BASE_PATH = "/mnt/home_dnlab/jhjung/radio/baechulsu" 
# BASE_PATH = "/mnt/home_dnlab/jhjung/radio/baechulsu"

def run_range():
    # 날짜 변환
    start = datetime.strptime(START_DATE, "%Y%m%d")
    end = datetime.strptime(END_DATE, "%Y%m%d")
    
    current = start
    
    while current <= end:
        date_str = current.strftime("%Y%m%d")
        
        # 1. 해당 날짜의 MP3 파일이 있는지 확인
        target_mp3 = os.path.join(BASE_PATH, date_str, "mp3", f"{date_str}.mp3")
        
        print(f"\n" + "="*50)
        print(f"📅 Processing Date: {date_str}")
        print(f"="*50)

        if os.path.exists(target_mp3):
            try:
                # 2. auto_run.py 실행 (하루치 파이프라인 수행)
                # subprocess를 써야 메모리 누수 없이 깔끔하게 돕니다.
                subprocess.run(["python", "auto_run.py", date_str], check=True)
                print(f"✅ {date_str} 완료!")
                
            except subprocess.CalledProcessError:
                print(f"❌ {date_str} 실행 중 에러 발생! (다음 날짜로 넘어갑니다)")
                # 에러 로그 파일에 기록
                with open("error_log.txt", "a") as f:
                    f.write(f"{date_str}: Pipeline Failed\n")
        else:
            print(f"⚠️  파일 없음 (Skip): {target_mp3}")
        
        # 하루 더하기
        current += timedelta(days=1)

if __name__ == "__main__":
    run_range()