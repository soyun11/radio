#!/bin/bash

### -----------------------------
### CUDA/cuDNN for cron
### -----------------------------
export LD_LIBRARY_PATH=/mnt/home_yslee/yslee/ad_detection/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/mnt/home_yslee/yslee/ad_detection/.venv/lib/python3.12/site-packages/ctranslate2.libs:$LD_LIBRARY_PATH
export PATH=/usr/local/cuda/bin:$PATH

# Change to the working directory
cd /home/yslee/radio/mbc || exit
source /home/yslee/ad_detection/.venv/bin/activate

# Fetch streaming URL
URL=$(curl -s "https://sminiplay.imbc.com/aacplay.ashx?agent=webapp&channel=mfm" | grep -oP 'http.*')

# Record audio with ffmpeg
ffmpeg -i "$URL" -acodec mp3 mbc-test.mp3 > /dev/null 2>&1 &
pid_player=$!

# Sleep for 5 minutes
sleep 7200

# Stop recording
if kill -0 $pid_player 2>/dev/null; then
    kill $pid_player
fi

# Rename and organize files
today=$(date +%Y%m%d)
mv mbc-test.mp3 "$today.mp3"

mkdir -p /home/yslee/radio/mbc/baechulsu/$today/mp3
mkdir -p /home/yslee/radio/mbc/baechulsu/$today/output
mkdir -p /home/yslee/radio/mbc/baechulsu/$today/output/output-$today
mkdir -p /home/yslee/radio/mbc/baechulsu/$today/transcript

mv "$today.mp3" /home/yslee/radio/mbc/baechulsu/$today/mp3

TARGET_BASE_DIR="/home/yslee/radio/mbc/baechulsu"

# Run Python scripts
sleep 5
/home/yslee/ad_detection/.venv/bin/python /home/yslee/radio/mbc/whisper-direct.py $today >> /home/yslee/radio/mbc/log.txt 2>&1
sleep 5
/home/yslee/ad_detection/.venv/bin/python /home/yslee/radio/mbc/srt2csv.py /home/yslee/radio/mbc/baechulsu/$today/transcript/$today.srt >> /home/yslee/radio/mbc/log.txt 2>&1
sleep 5
/home/yslee/ad_detection/.venv/bin/python /home/yslee/radio/mbc/diarize-direct.py $today >> /home/yslee/radio/mbc/log.txt 2>&1
sleep 5
/home/yslee/ad_detection/.venv/bin/python /home/yslee/radio/mbc/merge_speaker.py $TARGET_BASE_DIR/$today/transcript/$today.csv $TARGET_BASE_DIR/$today/transcript/$today'_'diarization.txt >> /home/yslee/radio/mbc/log.txt 2>&1

#/home/yslee/anaconda3/bin/python /home/yslee/radio/mbc/ina-script.py --input_mp3_dir /home/yslee/radio/mbc/baechulsu/$today/mp3 --output_dir /home/yslee/radio/mbc/baechulsu/$today/output  >> /home/yslee/radio/log.txt 2>&1
#sleep 30
#/home/yslee/anaconda3/bin/python /home/yslee/radio/mbc/merge-remove-noenergy2.py /home/yslee/radio/mbc/baechulsu/$today/output
#sleep 10
#/home/yslee/anaconda3/bin/python /home/yslee/radio/mbc/run-mp3-segmentation-3.py --mp3_file_dir /home/yslee/radio/mbc/baechulsu/$today/mp3 --output_base_dir /home/yslee/radio/mbc/baechulsu/$today/output --transcript_base_dir /home/yslee/radio/mbc/baechulsu/$today/transcript
#sleep 10
#scp -r -P 8002 yslee-office.asuscomm.com:/home/yslee/radio/mbc/baechulsu/$today/playlist /home/yslee/radio/mbc/baechulsu/$today/
#sleep 10
#/home/yslee/anaconda3/bin/python /home/yslee/radio/mbc/radio-openai-summary-folder3.py 
