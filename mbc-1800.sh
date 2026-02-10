#!/bin/bash

# 1. 환경변수 (필수)
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH

# 2. 경로 설정
WORK_DIR="/mnt/home_dnlab/jhjung/radio/mbc_radio"
DATE=$(date +%y%m%d%H%M)
FILENAME="mbc-${DATE}.mp3"

# 3. 폴더 이동
mkdir -p "$WORK_DIR"
cd "$WORK_DIR" || exit

# 4. 스트리밍 주소 추출 (여기가 핵심 수정! ⭐️)
# 설명: webapp 에이전트를 쓰고, 결과에서 'http'로 시작하는 주소 전체를 가져옵니다.
# 불필요한 cut, head, tail 명령어를 다 뺐습니다.
STREAM_URL=$(curl -s -L "https://sminiplay.imbc.com/aacplay.ashx?agent=webapp&channel=mfm" | grep -o "http.*")

# 5. 주소 확인 (디버깅용)
# 만약 주소가 비어있으면 에러 로그를 남기고 종료
if [ -z "$STREAM_URL" ]; then
    echo "Error: Failed to get stream URL. Curl output was empty."
    exit 1
fi

echo "URL Found: $STREAM_URL"

# 6. 녹음 시작 (2시간)
# -re 옵션은 생방송 녹음 시 싱크를 맞춰줍니다.
ffmpeg -y -re -i "$STREAM_URL" -t 7200 -acodec mp3 "$FILENAME" > /dev/null 2>&1

# 7. 권한 설정
chmod 644 "$FILENAME"