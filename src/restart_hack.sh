#!/usr/bin/env bash

cpu_usage="$(top -b -n2 -p 1 | fgrep "Cpu(s)" | tail -1 | awk -F'id,' -v prefix="$prefix" '{ split($1, vs, ","); v=vs[length(vs)]; sub("%", "", v); printf "%s%.1f\n", prefix, 100 - v }')"
too_low="$(echo "$cpu_usage < 75.0" | bc)"
echo $too_low

if [ "$too_low" -eq 1 ];then
    old_pid=$(cat /tmp/analyze_pid.txt)
    pkill -TERM -g $old_pid
    
    echo "Restarted computation..."  >> /root/out/logs/results18.log
    nohup /root/anaconda3/bin/python analyze.py >> /root/out/logs/results19.log 2>&1 &
    echo $! > /tmp/analyze_pid.txt
fi