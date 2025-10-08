#!/usr/bin/env python3
"""
macOS 외장 디스크 온도 및 I/O 속도 모니터링 프로그램
"""

import subprocess
import re
import time
import os
from datetime import datetime
from collections import defaultdict

class DiskMonitor:
    def __init__(self):
        self.previous_stats = {}

    def get_external_disks(self):
        """외장 디스크 목록 가져오기"""
        try:
            result = subprocess.run(['diskutil', 'list'],
                                  capture_output=True, text=True, check=True)

            disks = []
            for line in result.stdout.split('\n'):
                if 'external, physical' in line:
                    match = re.search(r'/dev/(disk\d+)', line)
                    if match:
                        disks.append(match.group(1))

            return disks
        except Exception as e:
            print(f"디스크 목록 가져오기 오류: {e}")
            return []

    def get_disk_info(self, disk):
        """디스크 정보 가져오기"""
        try:
            result = subprocess.run(['diskutil', 'info', disk],
                                  capture_output=True, text=True, check=True)

            info = {}
            for line in result.stdout.split('\n'):
                if 'Device / Media Name:' in line:
                    info['name'] = line.split(':', 1)[1].strip()
                elif 'Disk Size:' in line:
                    info['size'] = line.split(':', 1)[1].strip().split('(')[0].strip()

            return info
        except Exception as e:
            return {'name': disk, 'size': 'Unknown'}

    def get_disk_temperature(self, disk):
        """디스크 온도 가져오기 (smartctl 사용)"""
        try:
            # smartctl이 설치되어 있는지 확인
            result = subprocess.run(['which', 'smartctl'],
                                  capture_output=True, text=True)

            if result.returncode != 0:
                return "N/A (smartctl 필요)"

            # sudo 없이 시도
            result = subprocess.run(['smartctl', '-a', f'/dev/{disk}'],
                                  capture_output=True, text=True, timeout=5)

            # Temperature 찾기
            for line in result.stdout.split('\n'):
                if 'Temperature' in line or 'temperature' in line.lower():
                    # 숫자 추출
                    temp_match = re.search(r'(\d+)\s*C', line)
                    if temp_match:
                        return f"{temp_match.group(1)}°C"

            # 온도 정보가 없는 경우
            return "N/A"

        except subprocess.TimeoutExpired:
            return "Timeout"
        except Exception as e:
            return "N/A"

    def get_disk_io_stats(self, disk):
        """디스크 I/O 통계 가져오기"""
        try:
            result = subprocess.run(['iostat', '-Id', disk],
                                  capture_output=True, text=True, check=True, timeout=2)

            lines = result.stdout.strip().split('\n')
            if len(lines) >= 3:
                # 마지막 라인에서 통계 추출
                stats_line = lines[-1].split()
                if len(stats_line) >= 3:
                    kb_read = float(stats_line[0])  # KB/t read
                    kb_write = float(stats_line[1])  # KB/t write
                    mb_read = float(stats_line[2])  # MB/s read (실제로는 총 MB)

                    return {
                        'kb_per_transfer_read': kb_read,
                        'kb_per_transfer_write': kb_write,
                        'timestamp': time.time()
                    }

            return None
        except Exception as e:
            return None

    def calculate_speed(self, disk, current_stats):
        """읽기/쓰기 속도 계산"""
        if disk not in self.previous_stats or current_stats is None:
            self.previous_stats[disk] = current_stats
            return "측정 중...", "측정 중..."

        prev = self.previous_stats[disk]
        if prev is None:
            self.previous_stats[disk] = current_stats
            return "측정 중...", "측정 중..."

        time_diff = current_stats['timestamp'] - prev['timestamp']

        if time_diff < 0.1:  # 너무 짧은 시간 간격
            return "측정 중...", "측정 중..."

        # iostat은 누적 통계를 제공하므로 간단히 현재 값 사용
        read_speed = current_stats['kb_per_transfer_read']
        write_speed = current_stats['kb_per_transfer_write']

        self.previous_stats[disk] = current_stats

        # KB를 MB로 변환
        read_mb = read_speed / 1024
        write_mb = write_speed / 1024

        return f"{read_mb:.2f} MB/s", f"{write_mb:.2f} MB/s"

    def clear_screen(self):
        """화면 지우기"""
        os.system('clear')

    def monitor(self, interval=2):
        """실시간 모니터링"""
        print("외장 디스크 모니터 시작... (Ctrl+C로 종료)")
        print("참고: 온도 정보는 smartctl이 필요합니다 (brew install smartmontools)")
        print()

        try:
            while True:
                self.clear_screen()

                print("=" * 100)
                print(f"외장 디스크 모니터 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 100)
                print()

                disks = self.get_external_disks()

                if not disks:
                    print("외장 디스크를 찾을 수 없습니다.")
                else:
                    for disk in disks:
                        info = self.get_disk_info(disk)
                        temp = self.get_disk_temperature(disk)
                        io_stats = self.get_disk_io_stats(disk)
                        read_speed, write_speed = self.calculate_speed(disk, io_stats)

                        print(f"┌─ /dev/{disk} ─────────────────────────────────────────────────────")
                        print(f"│  이름:      {info.get('name', 'Unknown')}")
                        print(f"│  크기:      {info.get('size', 'Unknown')}")
                        print(f"│  온도:      {temp}")
                        print(f"│  읽기 속도:  {read_speed}")
                        print(f"│  쓰기 속도:  {write_speed}")
                        print(f"└─────────────────────────────────────────────────────────────────")
                        print()

                print(f"\n다음 업데이트: {interval}초 후... (Ctrl+C로 종료)")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n모니터링을 종료합니다.")

def main():
    monitor = DiskMonitor()
    monitor.monitor(interval=2)

if __name__ == "__main__":
    main()
