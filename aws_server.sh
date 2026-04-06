#!/bin/bash
# AWS Relay Server startup script
# Usage: sh aws_server.sh [start|stop|status|log]

LOG_DIR="/opt/workspace/mytest/bl/log"
LOG_FILE="$LOG_DIR/relay.log"
PID_FILE="$LOG_DIR/relay.pid"
PORT=8080
API_KEY="${BLENDER_RELAY_API_KEY:-mysecretkey}"

mkdir -p "$LOG_DIR"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "Relay already running (PID $(cat $PID_FILE))"
        return
    fi

    # Check port
    if ss -tlnp | grep -q ":$PORT "; then
        echo "Error: port $PORT is already in use"
        ss -tlnp | grep ":$PORT "
        return 1
    fi

    echo "Starting Relay Server on port $PORT..."
    echo "Log: $LOG_FILE"

    cd /opt/workspace/mytest/bl/relay
    BLENDER_RELAY_API_KEY="$API_KEY" \
        nohup uvicorn server:app --host 0.0.0.0 --port $PORT \
        >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    sleep 1
    if kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "Relay started (PID $(cat $PID_FILE))"
        curl -s http://localhost:$PORT/health
        echo ""
    else
        echo "Failed to start. Check log: $LOG_FILE"
        tail -5 "$LOG_FILE"
    fi
}

stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID"
            echo "Relay stopped (PID $PID)"
        else
            echo "Process $PID not running"
        fi
        rm -f "$PID_FILE"
    else
        echo "No PID file found"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
        echo "Relay running (PID $(cat $PID_FILE))"
        curl -s http://localhost:$PORT/health
        echo ""
    else
        echo "Relay not running"
    fi
}

log() {
    if [ -f "$LOG_FILE" ]; then
        tail -${1:-50} "$LOG_FILE"
    else
        echo "No log file: $LOG_FILE"
    fi
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    log)    log "$2" ;;
    restart) stop; sleep 1; start ;;
    *)      echo "Usage: $0 {start|stop|status|restart|log [lines]}" ;;
esac
