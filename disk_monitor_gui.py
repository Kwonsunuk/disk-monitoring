#!/usr/bin/env python3
"""
macOS 외장 디스크 온도 및 I/O 속도 모니터링 프로그램 (GUI 버전)
"""

import subprocess
import re
import time
import sys
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QLabel, QFrame, QPushButton, QScrollArea)
from PyQt5.QtCore import QTimer, Qt, QPoint
from PyQt5.QtGui import QFont, QPalette, QColor, QScreen

class DiskMonitor:
    def __init__(self):
        self.previous_stats = {}
        self.speed_cache = {}  # 속도 캐시
        self.last_speed_update = {}  # 마지막 속도 업데이트 시간

    def get_raid_info(self):
        """RAID 구성 정보 가져오기"""
        try:
            result = subprocess.run(['diskutil', 'appleRAID', 'list'],
                                  capture_output=True, text=True, check=True)

            raids = {}
            current_raid = None
            raid_members = []

            for line in result.stdout.split('\n'):
                if 'Name:' in line:
                    if current_raid and raid_members:
                        raids[current_raid] = raid_members
                    current_raid = line.split('Name:')[1].strip()
                    raid_members = []
                elif re.match(r'^\d+\s+disk\d+', line.strip()):
                    # RAID 멤버 디스크 찾기
                    parts = line.split()
                    if len(parts) >= 2:
                        disk_match = re.search(r'disk(\d+)', parts[1])
                        if disk_match:
                            raid_members.append(f"disk{disk_match.group(1)}")

            if current_raid and raid_members:
                raids[current_raid] = raid_members

            return raids
        except Exception as e:
            return {}

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
            return []

    def group_disks_by_raid(self):
        """RAID별로 디스크 그룹화"""
        all_disks = self.get_external_disks()
        raids = self.get_raid_info()

        grouped = {
            'raids': {},
            'standalone': []
        }

        # RAID에 속한 디스크 찾기
        raid_disk_set = set()
        for raid_name, members in raids.items():
            raid_disks = [disk for disk in members if disk in all_disks]
            if raid_disks:
                grouped['raids'][raid_name] = raid_disks
                raid_disk_set.update(raid_disks)

        # 독립 디스크 찾기
        for disk in all_disks:
            if disk not in raid_disk_set:
                grouped['standalone'].append(disk)

        return grouped

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
            result = subprocess.run(['which', 'smartctl'],
                                  capture_output=True, text=True)

            if result.returncode != 0:
                return "N/A"

            result = subprocess.run(['smartctl', '-a', f'/dev/{disk}'],
                                  capture_output=True, text=True, timeout=5)

            for line in result.stdout.split('\n'):
                if 'Temperature' in line or 'temperature' in line.lower():
                    temp_match = re.search(r'(\d+)\s*C', line)
                    if temp_match:
                        return f"{temp_match.group(1)}°C"

            return "N/A"

        except subprocess.TimeoutExpired:
            return "Timeout"
        except Exception as e:
            return "N/A"

    def get_disk_io_stats(self, disk):
        """디스크 I/O 통계 가져오기 - 누적 전송량 반환"""
        try:
            result = subprocess.run(['iostat', '-Id', disk],
                                  capture_output=True, text=True, check=True, timeout=2)

            lines = result.stdout.strip().split('\n')
            if len(lines) >= 3:
                stats_line = lines[-1].split()
                if len(stats_line) >= 3:
                    # MB 누적 전송량 (3번째 컬럼)
                    total_mb = float(stats_line[2])

                    return {
                        'total_mb': total_mb,
                        'timestamp': time.time()
                    }

            return None
        except Exception as e:
            return None

    def calculate_speed(self, disk, current_stats):
        """전송 속도 계산 - 누적 데이터 차이로 계산"""
        current_time = time.time()

        # 캐시가 있고 2초 이내면 캐시된 값 반환
        if disk in self.speed_cache and disk in self.last_speed_update:
            if current_time - self.last_speed_update[disk] < 2.0:
                return self.speed_cache[disk]

        try:
            # iostat으로 누적 통계만 빠르게 가져오기 (대기 없음)
            result = subprocess.run(['iostat', '-Id', disk],
                                  capture_output=True, text=True, check=True, timeout=1)

            lines = result.stdout.strip().split('\n')

            if len(lines) >= 3:
                last_line = lines[-1].strip()
                parts = last_line.split()

                if len(parts) >= 3:
                    try:
                        total_mb = float(parts[2])  # 누적 MB

                        # 이전 측정값이 있으면 차이 계산
                        if disk in self.previous_stats and self.previous_stats[disk]:
                            prev_mb = self.previous_stats[disk].get('total_mb', 0)
                            prev_time = self.previous_stats[disk].get('timestamp', current_time)

                            time_diff = current_time - prev_time
                            if time_diff > 0:
                                mb_diff = total_mb - prev_mb
                                mb_per_sec = mb_diff / time_diff

                                # 이전 데이터 업데이트
                                self.previous_stats[disk] = {
                                    'total_mb': total_mb,
                                    'timestamp': current_time
                                }

                                if mb_per_sec < 0.01:
                                    result_val = ("유휴", "")
                                else:
                                    result_val = (f"{mb_per_sec:.2f} MB/s", "")

                                self.speed_cache[disk] = result_val
                                self.last_speed_update[disk] = current_time
                                return result_val

                        # 첫 측정이면 데이터만 저장
                        self.previous_stats[disk] = {
                            'total_mb': total_mb,
                            'timestamp': current_time
                        }
                        result_val = ("측정 중...", "")
                        self.speed_cache[disk] = result_val
                        self.last_speed_update[disk] = current_time
                        return result_val

                    except (ValueError, IndexError):
                        pass

            result_val = ("0.00 MB/s", "")
            self.speed_cache[disk] = result_val
            self.last_speed_update[disk] = current_time
            return result_val

        except Exception as e:
            result_val = ("N/A", "")
            self.speed_cache[disk] = result_val
            self.last_speed_update[disk] = current_time
            return result_val


class RaidGroupWidget(QFrame):
    """RAID 그룹 위젯"""

    def __init__(self, raid_name, disk_list):
        super().__init__()
        self.raid_name = raid_name
        self.disk_list = disk_list
        self.disk_widgets = {}
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #ff9800;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout()

        # RAID 타이틀
        title = QLabel(f"🔗 RAID: {self.raid_name}")
        title.setFont(QFont("SF Pro", 14, QFont.Bold))
        title.setStyleSheet("color: #ff9800; border: none; padding: 0;")
        layout.addWidget(title)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #ff9800; border: none;")
        layout.addWidget(line)

        # 디스크 컨테이너
        self.disks_container = QVBoxLayout()
        self.disks_container.setSpacing(8)
        layout.addLayout(self.disks_container)

        self.setLayout(layout)

    def add_disk_info(self, disk, info, temp, read_speed, write_speed):
        """디스크 정보 추가/업데이트"""
        if disk not in self.disk_widgets:
            # 새 디스크 정보 레이블 생성
            disk_frame = QFrame()
            disk_frame.setStyleSheet("background-color: #252525; border-radius: 5px; padding: 8px;")

            disk_layout = QVBoxLayout()

            name_label = QLabel(f"• {info.get('name', disk)}")
            name_label.setFont(QFont("SF Pro", 11))
            name_label.setStyleSheet("color: #ffffff; border: none;")
            disk_layout.addWidget(name_label)

            info_layout = QHBoxLayout()

            temp_label = QLabel(f"온도: {temp}")
            temp_label.setFont(QFont("SF Pro", 10))
            temp_label.setStyleSheet("color: #aaaaaa; border: none;")
            info_layout.addWidget(temp_label)

            io_label = QLabel(f"I/O: {read_speed}")
            io_label.setFont(QFont("SF Pro", 10))
            io_label.setStyleSheet("color: #aaaaaa; border: none;")
            info_layout.addWidget(io_label)

            info_layout.addStretch()
            disk_layout.addLayout(info_layout)

            disk_frame.setLayout(disk_layout)

            self.disk_widgets[disk] = {
                'frame': disk_frame,
                'name': name_label,
                'temp': temp_label,
                'io': io_label
            }

            self.disks_container.addWidget(disk_frame)
        else:
            # 기존 디스크 정보 업데이트
            widgets = self.disk_widgets[disk]
            widgets['name'].setText(f"• {info.get('name', disk)}")
            widgets['temp'].setText(f"온도: {temp}")
            widgets['io'].setText(f"I/O: {read_speed}")


class CompactRaidWidget(QFrame):
    """최소화된 RAID 그룹 위젯"""

    def __init__(self, raid_name, disk_list):
        super().__init__()
        self.raid_name = raid_name
        self.disk_list = disk_list
        self.disk_labels = {}
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #ff9800;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(5)

        # RAID 타이틀
        title = QLabel(f"🔗 {self.raid_name}")
        title.setFont(QFont("SF Pro", 11, QFont.Bold))
        title.setStyleSheet("color: #ff9800; border: none;")
        layout.addWidget(title)

        # 디스크 정보 컨테이너
        self.disks_layout = QVBoxLayout()
        self.disks_layout.setSpacing(3)
        layout.addLayout(self.disks_layout)

        self.setLayout(layout)

    def add_disk_info(self, disk, info, temp, read_speed, write_speed):
        """디스크 정보 추가/업데이트"""
        if disk not in self.disk_labels:
            disk_layout = QHBoxLayout()

            # 디스크 이름
            name = info.get('name', disk)
            if len(name) > 12:
                name = name[:9] + "..."

            name_label = QLabel(f"• {name}")
            name_label.setFont(QFont("SF Pro", 10))
            name_label.setStyleSheet("color: #ffffff; border: none;")
            name_label.setMinimumWidth(120)
            disk_layout.addWidget(name_label)

            # 온도
            temp_label = QLabel(f"{temp}")
            temp_label.setFont(QFont("SF Pro", 9))
            temp_label.setStyleSheet("color: #aaaaaa; border: none;")
            temp_label.setFixedWidth(60)
            disk_layout.addWidget(temp_label)

            # I/O 속도
            io_label = QLabel(f"I/O: {read_speed}")
            io_label.setFont(QFont("SF Pro", 9))
            io_label.setStyleSheet("color: #aaaaaa; border: none;")
            disk_layout.addWidget(io_label)

            disk_layout.addStretch()

            self.disk_labels[disk] = {
                'name': name_label,
                'temp': temp_label,
                'io': io_label
            }

            self.disks_layout.addLayout(disk_layout)
        else:
            # 업데이트
            labels = self.disk_labels[disk]
            name = info.get('name', disk)
            if len(name) > 12:
                name = name[:9] + "..."
            labels['name'].setText(f"• {name}")
            labels['temp'].setText(f"{temp}")
            labels['io'].setText(f"I/O: {read_speed}")


class CompactDiskWidget(QFrame):
    """최소화된 디스크 정보 위젯"""

    def __init__(self, disk_name):
        super().__init__()
        self.disk_name = disk_name
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #404040;
                border-radius: 5px;
                padding: 8px;
            }
        """)

        layout = QHBoxLayout()

        # 디스크 이름 (실제 모델명으로 표시됨)
        self.name_label = QLabel(f"/dev/{self.disk_name}")
        self.name_label.setFont(QFont("SF Pro", 11, QFont.Bold))
        self.name_label.setStyleSheet("color: #4a9eff; border: none;")
        self.name_label.setMinimumWidth(200)
        layout.addWidget(self.name_label)

        # 온도
        self.temp_label = QLabel("온도: -")
        self.temp_label.setFont(QFont("SF Pro", 10))
        self.temp_label.setStyleSheet("color: #ffffff; border: none;")
        self.temp_label.setFixedWidth(100)
        layout.addWidget(self.temp_label)

        # I/O 속도
        self.io_label = QLabel("I/O: -")
        self.io_label.setFont(QFont("SF Pro", 10))
        self.io_label.setStyleSheet("color: #ffffff; border: none;")
        layout.addWidget(self.io_label)

        layout.addStretch()

        self.setLayout(layout)

    def update_info(self, info, temp, read_speed, write_speed):
        """정보 업데이트"""
        # 실제 디스크 모델명으로 표시
        disk_name = info.get('name', self.disk_name)
        if disk_name and disk_name != self.disk_name:
            self.name_label.setText(disk_name)

        self.temp_label.setText(f"온도: {temp}")
        self.io_label.setText(f"I/O: {read_speed}")


class DiskInfoWidget(QFrame):
    """개별 디스크 정보 표시 위젯"""

    def __init__(self, disk_name):
        super().__init__()
        self.disk_name = disk_name
        self.init_ui()

    def init_ui(self):
        """UI 초기화"""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        self.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #404040;
                border-radius: 10px;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout()

        # 타이틀
        title = QLabel(f"/dev/{self.disk_name}")
        title.setFont(QFont("SF Pro", 16, QFont.Bold))
        title.setStyleSheet("color: #4a9eff; border: none; padding: 0;")
        layout.addWidget(title)

        # 정보 레이블들
        self.name_label = self.create_info_label("이름: ")
        self.size_label = self.create_info_label("크기: ")
        self.temp_label = self.create_info_label("온도: ")
        self.io_label = self.create_info_label("I/O 속도: ")

        layout.addWidget(self.name_label)
        layout.addWidget(self.size_label)
        layout.addWidget(self.temp_label)
        layout.addWidget(self.io_label)

        self.setLayout(layout)

    def create_info_label(self, text):
        """정보 레이블 생성"""
        label = QLabel(text)
        label.setFont(QFont("SF Pro", 12))
        label.setStyleSheet("color: #ffffff; border: none; padding: 3px;")
        return label

    def update_info(self, info, temp, read_speed, write_speed):
        """정보 업데이트"""
        self.name_label.setText(f"이름: {info.get('name', 'Unknown')}")
        self.size_label.setText(f"크기: {info.get('size', 'Unknown')}")
        self.temp_label.setText(f"온도: {temp}")
        self.io_label.setText(f"I/O 속도: {read_speed}")


class WidgetWindow(QMainWindow):
    """상단 고정 위젯 창"""

    def __init__(self, monitor, parent=None):
        super().__init__()
        self.monitor = monitor
        self.parent_window = parent
        self.disk_labels = {}
        self.raid_groups = {}  # RAID 그룹 위젯 저장
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """위젯 UI 초기화"""
        # 창 설정 - 항상 최상위에 유지
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Window  # Tool 대신 Window로 변경하여 포커스 잃어도 표시 유지
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating)  # 활성화 없이 표시

        # 중앙 위젯
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #1e1e1e; border-radius: 10px;")
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # 타이틀
        title_layout = QHBoxLayout()
        title = QLabel("디스크 온도")
        title.setFont(QFont("SF Pro", 11, QFont.Bold))
        title.setStyleSheet("color: #4a9eff;")
        title_layout.addWidget(title)

        title_layout.addStretch()

        # 확장 버튼
        expand_btn = QPushButton("◰")
        expand_btn.setFixedSize(20, 20)
        expand_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2196f3;
            }
        """)
        expand_btn.clicked.connect(self.expand_window)
        title_layout.addWidget(expand_btn)

        # 닫기 버튼
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)

        layout.addLayout(title_layout)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #404040;")
        layout.addWidget(line)

        # 디스크 온도 컨테이너
        self.temp_container = QVBoxLayout()
        self.temp_container.setSpacing(3)
        layout.addLayout(self.temp_container)

        central_widget.setLayout(layout)

        # 화면 우측 상단에 위치
        self.position_top_right()

    def position_top_right(self):
        """화면 우측 상단에 위치"""
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() - 220, 50, 200, 150)

    def setup_timer(self):
        """업데이트 타이머"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_temps)
        self.timer.start(2000)
        self.update_temps()

    def update_temps(self):
        """온도 정보 업데이트"""
        # RAID별로 그룹화된 디스크 가져오기
        grouped_disks = self.monitor.group_disks_by_raid()

        # RAID 그룹 처리
        for raid_name, raid_disks in grouped_disks['raids'].items():
            raid_key = f"raid_{raid_name}"

            # RAID 그룹 위젯 생성
            if raid_key not in self.raid_groups:
                # RAID 타이틀
                title_label = QLabel(f"🔗 {raid_name}")
                title_label.setFont(QFont("SF Pro", 10, QFont.Bold))
                title_label.setStyleSheet("color: #ff9800;")
                self.temp_container.addWidget(title_label)

                # 구분선
                line = QFrame()
                line.setFrameShape(QFrame.HLine)
                line.setStyleSheet("background-color: #ff9800; max-height: 1px;")
                self.temp_container.addWidget(line)

                self.raid_groups[raid_key] = {
                    'title': title_label,
                    'line': line,
                    'disks': {}
                }

            # RAID 내 각 디스크 레이블 생성/업데이트
            for disk in raid_disks:
                if disk not in self.raid_groups[raid_key]['disks']:
                    label = QLabel()
                    label.setFont(QFont("SF Pro", 8))
                    label.setStyleSheet("color: #dddddd; padding-left: 10px;")
                    self.raid_groups[raid_key]['disks'][disk] = label
                    self.temp_container.addWidget(label)

                # 온도 및 속도 업데이트
                info = self.monitor.get_disk_info(disk)
                temp = self.monitor.get_disk_temperature(disk)
                io_stats = self.monitor.get_disk_io_stats(disk)
                read_speed, write_speed = self.monitor.calculate_speed(disk, io_stats)

                # 짧은 이름 생성
                name = info.get('name', disk)
                if len(name) > 10:
                    name = name[:7] + "..."

                # I/O 속도 표시 (빈 문자열이면 표시 안함)
                if read_speed:
                    self.raid_groups[raid_key]['disks'][disk].setText(
                        f"  • {name}: {temp} I/O: {read_speed}"
                    )
                else:
                    self.raid_groups[raid_key]['disks'][disk].setText(
                        f"  • {name}: {temp}"
                    )

        # 독립 디스크 처리
        for disk in grouped_disks['standalone']:
            if disk not in self.disk_labels:
                label = QLabel()
                label.setFont(QFont("SF Pro", 9))
                label.setStyleSheet("color: #ffffff;")
                self.disk_labels[disk] = label
                self.temp_container.addWidget(label)

            # 온도 및 속도 업데이트
            info = self.monitor.get_disk_info(disk)
            temp = self.monitor.get_disk_temperature(disk)
            io_stats = self.monitor.get_disk_io_stats(disk)
            read_speed, write_speed = self.monitor.calculate_speed(disk, io_stats)

            # 짧은 이름 생성
            name = info.get('name', disk)
            if len(name) > 10:
                name = name[:7] + "..."

            # I/O 속도 표시
            if read_speed:
                self.disk_labels[disk].setText(f"{name}: {temp} I/O: {read_speed}")
            else:
                self.disk_labels[disk].setText(f"{name}: {temp}")

        # 창 크기 조정 (첫 초기화 시에만)
        if not hasattr(self, '_initialized'):
            self.adjustSize()
            self._initialized = True

    def expand_window(self):
        """메인 창 복원"""
        if self.parent_window:
            self.parent_window.show()
            self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.monitor = DiskMonitor()
        self.disk_widgets = {}
        self.compact_mode = False  # 최소화 모드 플래그
        self.widget_window = None  # 위젯 창
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        """메인 UI 초기화"""
        self.setWindowTitle("외장 디스크 모니터")
        self.setGeometry(100, 100, 900, 700)

        # 다크 모드 설정
        self.set_dark_palette()

        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()

        # 타이틀
        title = QLabel("외장 디스크 모니터")
        title.setFont(QFont("SF Pro", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #ffffff; padding: 20px;")
        main_layout.addWidget(title)

        # 시간 표시
        self.time_label = QLabel()
        self.time_label.setFont(QFont("SF Pro", 11))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("color: #aaaaaa; padding: 5px;")
        main_layout.addWidget(self.time_label)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
        """)
        # 부드러운 업데이트를 위한 설정
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # 디스크 정보 컨테이너
        self.container = QWidget()
        self.container_layout = QVBoxLayout()
        self.container_layout.setSpacing(15)
        self.container.setLayout(self.container_layout)

        scroll.setWidget(self.container)
        main_layout.addWidget(scroll)

        # 버튼들
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 상단 위젯 버튼
        widget_button = QPushButton("상단 위젯")
        widget_button.setFont(QFont("SF Pro", 12))
        widget_button.setStyleSheet("""
            QPushButton {
                background-color: #388e3c;
                color: white;
                border-radius: 5px;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #4caf50;
            }
        """)
        widget_button.clicked.connect(self.toggle_widget)
        button_layout.addWidget(widget_button)

        button_layout.addSpacing(10)

        # 최소화 모드 토글 버튼
        self.compact_button = QPushButton("최소화 모드")
        self.compact_button.setFont(QFont("SF Pro", 12))
        self.compact_button.setStyleSheet("""
            QPushButton {
                background-color: #1976d2;
                color: white;
                border-radius: 5px;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #2196f3;
            }
        """)
        self.compact_button.clicked.connect(self.toggle_compact_mode)
        button_layout.addWidget(self.compact_button)

        button_layout.addSpacing(10)

        # 종료 버튼
        quit_button = QPushButton("종료")
        quit_button.setFont(QFont("SF Pro", 12))
        quit_button.setStyleSheet("""
            QPushButton {
                background-color: #d32f2f;
                color: white;
                border-radius: 5px;
                padding: 10px 30px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)
        quit_button.clicked.connect(self.close)
        button_layout.addWidget(quit_button)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        central_widget.setLayout(main_layout)

    def set_dark_palette(self):
        """다크 모드 팔레트 설정"""
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(45, 45, 45))
        palette.setColor(QPalette.AlternateBase, QColor(30, 30, 30))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(74, 158, 255))
        palette.setColor(QPalette.Highlight, QColor(74, 158, 255))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def setup_timer(self):
        """업데이트 타이머 설정"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_disk_info)
        self.timer.start(2000)  # 2초마다 업데이트
        self.update_disk_info()  # 즉시 한 번 업데이트

    def toggle_widget(self):
        """상단 위젯 토글"""
        if self.widget_window is None or not self.widget_window.isVisible():
            self.widget_window = WidgetWindow(self.monitor, parent=self)
            self.widget_window.show()
            self.hide()  # 메인 창 숨기기
        else:
            self.widget_window.close()
            self.widget_window = None

    def toggle_compact_mode(self):
        """최소화 모드 토글"""
        self.compact_mode = not self.compact_mode

        # 버튼 텍스트 변경
        if self.compact_mode:
            self.compact_button.setText("전체 모드")
            self.setGeometry(100, 100, 600, 400)  # 창 크기 축소
        else:
            self.compact_button.setText("최소화 모드")
            self.setGeometry(100, 100, 900, 700)  # 원래 크기

        # 기존 위젯 제거
        for disk in list(self.disk_widgets.keys()):
            widget = self.disk_widgets[disk]
            self.container_layout.removeWidget(widget)
            widget.deleteLater()

        self.disk_widgets.clear()

        # 즉시 업데이트
        self.update_disk_info()

    def update_disk_info(self):
        """디스크 정보 업데이트"""
        # 시간 업데이트
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_label.setText(f"마지막 업데이트: {current_time}")

        # RAID별로 그룹화된 디스크 가져오기
        grouped_disks = self.monitor.group_disks_by_raid()

        # RAID 그룹 처리
        for raid_name, raid_disks in grouped_disks['raids'].items():
            raid_key = f"raid_{raid_name}"

            # RAID 그룹 위젯 생성 또는 가져오기
            if raid_key not in self.disk_widgets:
                if not self.compact_mode:
                    widget = RaidGroupWidget(raid_name, raid_disks)
                    self.disk_widgets[raid_key] = widget
                    self.container_layout.addWidget(widget)

            # 최소화 모드에서는 CompactRaidWidget 사용
            if self.compact_mode and raid_key not in self.disk_widgets:
                widget = CompactRaidWidget(raid_name, raid_disks)
                self.disk_widgets[raid_key] = widget
                self.container_layout.addWidget(widget)

            # RAID 그룹 내 각 디스크 정보 업데이트
            if raid_key in self.disk_widgets:
                for disk in raid_disks:
                    info = self.monitor.get_disk_info(disk)
                    temp = self.monitor.get_disk_temperature(disk)
                    io_stats = self.monitor.get_disk_io_stats(disk)
                    read_speed, write_speed = self.monitor.calculate_speed(disk, io_stats)

                    self.disk_widgets[raid_key].add_disk_info(disk, info, temp, read_speed, write_speed)

        # 독립 디스크 처리
        for disk in grouped_disks['standalone']:
            if disk not in self.disk_widgets:
                if self.compact_mode:
                    widget = CompactDiskWidget(disk)
                else:
                    widget = DiskInfoWidget(disk)
                self.disk_widgets[disk] = widget
                self.container_layout.addWidget(widget)

            info = self.monitor.get_disk_info(disk)
            temp = self.monitor.get_disk_temperature(disk)
            io_stats = self.monitor.get_disk_io_stats(disk)
            read_speed, write_speed = self.monitor.calculate_speed(disk, io_stats)

            self.disk_widgets[disk].update_info(info, temp, read_speed, write_speed)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
