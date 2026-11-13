#!/usr/bin/env bash
# Pico 2 USB/serial health check. Usage: ./pico_check.sh
PORT=${1:-/dev/ttyACM0}
ok(){ printf "  [ OK ] %s\n" "$1"; }
bad(){ printf "  [FAIL] %s\n" "$1"; }

echo "1. USB enumeration"
L=$(lsusb | grep -i 2e8a)
if [ -n "$L" ]; then ok "$L"; else bad "no Raspberry Pi device on the bus (cable/port/board)"; fi

echo "2. Serial port"
if [ -e "$PORT" ]; then ok "$PORT exists"; else bad "$PORT missing"; fi
if id -nG | grep -qE "dialout|uucp"; then ok "user is in dialout group"; else bad "user not in dialout group"; fi

echo "3. Kernel USB errors in the last 5 minutes (error -71 = flaky link)"
E=$(journalctl -k --since "-5min" --no-pager 2>/dev/null | grep -c -E "error -71|unable to enumerate|not accepting address|device descriptor read")
if [ "$E" -eq 0 ]; then ok "none"; else bad "$E error lines (replug, shorter cable, other port)"; fi

echo "4. USB re-enumerations in the last 5 minutes (many = connector dropping out)"
N=$(journalctl -k --since "-5min" --no-pager 2>/dev/null | grep -c "New USB device found")
if [ "$N" -le 1 ]; then ok "$N"; else bad "$N re-enumerations"; fi

echo "5. MicroPython handshake"
if timeout 15 mpremote connect "$PORT" exec "import machine;print('alive, %d MHz' % (machine.freq()//1000000))" 2>/dev/null | grep -q alive; then
  ok "board answers"
else
  bad "no answer (replug the cable; if it persists, hold BOOTSEL while plugging to recover)"
fi
