# External Disk Monitor

macOS용 외장 디스크 모니터링 프로그램 - 온도와 읽기/쓰기 속도를 실시간으로 모니터링합니다.

## 주요 기능

- **외장 디스크 자동 감지** - 연결된 모든 외장 디스크를 자동으로 감지
- **RAID 그룹 지원** - Apple RAID로 묶인 디스크를 그룹으로 표시
- **실시간 온도 모니터링** - SMART 정보를 통한 디스크 온도 측정
- **읽기/쓰기 속도 분리 표시** - 읽기(녹색 ↓)와 쓰기(주황색 ↑) 속도를 별도로 표시
- **3가지 보기 모드**
  - **일반 모드**: 상세 정보 전체 표시
  - **최소화 모드**: 간단한 정보만 표시
  - **위젯 모드**: 항상 위에 표시되는 작은 위젯 (드래그 가능)
- **다크 모드 UI** - 눈에 편안한 다크 테마

## 시스템 요구사항

- macOS (10.13 High Sierra 이상 권장)
- Python 3.8 이상
- PyQt5
- psutil

## 설치 방법

### 자동 설치 (권장)

```bash
cd "/Volumes/ERAID/Personnel/디스크 모니터링"
./install.sh
```

### 수동 설치

```bash
# 의존성 설치
pip3 install -r requirements.txt

# (선택) 온도 모니터링을 위한 smartmontools 설치
brew install smartmontools
```

## 사용 방법

### Python 스크립트로 실행

```bash
python3 disk_monitor_gui.py
```

### macOS 앱 번들 빌드 (선택)

```bash
./build_app.sh
```

빌드가 완료되면 `/Applications`로 복사:

```bash
cp -r "dist/Disk Monitor.app" /Applications/
```

## 보기 모드

### 1. 일반 모드
- 모든 디스크의 상세 정보 표시
- 이름, 크기, 온도, 읽기/쓰기 속도 모두 표시

### 2. 최소화 모드
- "최소화" 버튼 클릭
- 간단한 정보만 표시 (이름, 온도, 속도)
- 화면 공간 절약

### 3. 위젯 모드
- "위젯" 버튼 클릭
- 항상 위에 표시되는 작은 창
- 우측 상단에 고정 (드래그로 위치 변경 가능)
- "확장" 버튼으로 일반 모드 복귀
- 다른 창 작업 중에도 항상 표시

## 기능 상세

### RAID 디스크 그룹핑
- Apple RAID로 구성된 디스크는 자동으로 그룹화
- 예: "ExFATRAID (disk4, disk5)"
- 모든 보기 모드에서 지원

### 실시간 속도 측정
- 읽기 속도: 녹색 ↓ 아이콘
- 쓰기 속도: 주황색 ↑ 아이콘
- psutil 기반으로 즉각 반응
- 1.5-2초 캐싱으로 시스템 부하 최소화

### 온도 모니터링
- SMART 지원 디스크에서만 사용 가능
- smartmontools 설치 필요
- 일부 외장 디스크나 RAID는 온도 정보 미제공

## 표시 정보

각 디스크마다 다음 정보를 표시:

| 항목 | 설명 | 예시 |
|------|------|------|
| 이름 | 디스크 모델명 또는 RAID 이름 | Samsung T7, ExFATRAID |
| 크기 | 총 용량 | 1.0 TB |
| 온도 | 현재 온도 (SMART) | 35°C |
| 읽기 | 현재 읽기 속도 | ↓ 2.5 MB/s |
| 쓰기 | 현재 쓰기 속도 | ↑ 1.2 MB/s |

## 문제 해결

### smartctl 관련 에러
온도 정보가 "N/A"로 표시되면:

```bash
brew install smartmontools
```

### 권한 오류
일부 디스크는 SMART 정보 접근에 sudo 권한 필요:

```bash
sudo python3 disk_monitor_gui.py
```

### 디스크가 표시되지 않음
외장 디스크만 표시됩니다. 내장 디스크는 제외됩니다.

### 속도가 0으로 표시됨
- 초기 실행 시 2-3초 정도 측정 시간 필요
- 디스크 활동이 없으면 0 MB/s 표시

## 기술 스택

- **GUI**: PyQt5
- **디스크 I/O**: psutil
- **디스크 정보**: diskutil (macOS)
- **온도 정보**: smartctl (smartmontools)
- **RAID 감지**: diskutil appleRAID list

## 파일 구조

```
디스크 모니터링/
├── disk_monitor_gui.py    # 메인 GUI 프로그램
├── disk_monitor.py         # 콘솔 버전
├── requirements.txt        # Python 의존성
├── install.sh              # 자동 설치 스크립트
├── setup.py                # py2app 설정
├── build_app.sh            # 앱 번들 빌드 스크립트
└── README.md               # 이 파일
```

## 버전 히스토리

### v1.0.0
- 외장 디스크 감지 및 모니터링
- 온도, 읽기/쓰기 속도 표시
- 3가지 보기 모드 (일반/최소화/위젯)
- RAID 그룹핑
- 드래그 가능한 위젯
- psutil 기반 실시간 속도 측정

## 라이선스

MIT License

## 피드백 및 기여

문제 발생 시 이슈를 등록하거나 풀 리퀘스트를 보내주세요.
