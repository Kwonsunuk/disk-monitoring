# 외장 디스크 모니터

macOS에서 외장 디스크의 온도와 읽기/쓰기 속도를 실시간으로 모니터링하는 프로그램입니다.

## 기능

- 외장 디스크 자동 감지
- 실시간 온도 모니터링 (SMART 정보)
- 실시간 읽기/쓰기 속도 표시
- 깔끔한 다크 모드 GUI

## 설치

### 필수 요구사항

- Python 3.x
- macOS (diskutil, iostat 사용)
- PyQt5

### PyQt5 설치

```bash
pip3 install PyQt5 --break-system-packages
```

### 선택 사항

온도 정보를 보려면 smartmontools 설치가 필요합니다:

```bash
brew install smartmontools
```

## 사용법

### GUI 버전 (권장)

```bash
python3 disk_monitor_gui.py
```

### 콘솔 버전

```bash
python3 disk_monitor.py
```

### 종료

GUI: 종료 버튼 클릭 또는 창 닫기
콘솔: `Ctrl+C`

## 표시 정보

각 외장 디스크마다 다음 정보를 표시합니다:

- **이름**: 디스크 모델명
- **크기**: 디스크 용량
- **온도**: 현재 디스크 온도 (°C)
- **읽기 속도**: 현재 읽기 속도 (MB/s)
- **쓰기 속도**: 현재 쓰기 속도 (MB/s)

## 참고사항

- 온도 정보는 SMART를 지원하는 디스크에서만 사용 가능합니다
- 일부 외장 디스크나 RAID 구성의 경우 온도 정보를 가져올 수 없을 수 있습니다
- 읽기/쓰기 속도는 2초 간격으로 업데이트됩니다
- 초기 실행 시 속도 측정에 몇 초가 걸릴 수 있습니다

## 문제 해결

### "smartctl 필요" 메시지가 표시되는 경우

```bash
brew install smartmontools
```

### 권한 오류가 발생하는 경우

일부 디스크는 SMART 정보 접근에 sudo 권한이 필요할 수 있습니다:

```bash
sudo python3 disk_monitor.py
```

## 라이선스

MIT
