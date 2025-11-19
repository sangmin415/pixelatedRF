"""
간단한 2포트 필터 GDS 생성 스크립트
ADS에서 Import하여 레이아웃을 확인할 수 있습니다.

사용법:
1. 아래 '사용자 설정' 섹션의 경로를 본인 PC에 맞게 수정
2. 스크립트 실행: python simple_2port_filter.py
3. 생성된 GDS 파일을 ADS에서 Import
"""

import os
import sys
from datetime import datetime

# 상위 디렉토리의 vt_rrfc 모듈 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vt_rrfc import MicrostripSub, MicrostripCalc, RandomComponent

# ===== 사용자 설정 (본인 환경에 맞게 수정하세요) =====

# ADS 2024 경로
simulatorPath = r"C:\Program Files\Keysight\ADS2024\bin"

# 작업 경로 (GDS 파일이 저장될 위치)
pathName = r"C:\Users\YourName\Documents\pixelatedRF_output"  # <<< 수정 필요

# ADS Workspace 이름
libName = "MyFirstWorkspace"

# ===== 기판 파라미터 =====
fc = 5.0e9      # 중심 주파수 (Hz)
z0 = 50         # 특성 임피던스 (Ohms)
t = 2.8         # 도체 두께 (mils)
cond = 5.88e7   # 전도도 (S/m)
h = 30          # 기판 높이 (mils)
er = 4.5        # 비유전율

# ===== 레이아웃 파라미터 =====
ports = 2           # 포트 개수
sides = 2           # 포트 위치 (양쪽)
pixelSize = 18      # 픽셀 크기 (mils) - PCB 제조사 제약에 따름
layoutUnit = 25.4e-6  # 레이아웃 단위 (mils)
layoutRes = 1       # 레이아웃 해상도
scale = 1           # 스케일 팩터
minPixel = 6        # 최소 픽셀 크기
shape = 1           # 형태 (1=사각형)
corner = 'normal'   # 코너 타입
sym = 'y-axis'      # 대칭: 'x-axis', 'y-axis', 'xy-axis', 'none'
el_ports = 30       # 포트 전기 길이 (degrees)

# DC 연결 맵: [1-2, 1-3, 1-4, 2-3, 2-4, 3-4]
# 1 = 연결 강제, 0 = 연결 불필요
connectMap = [1, 0, 0, 0, 0, 0]  # 포트 1-2 DC 연결

# 픽셀 그리드 크기
x_pixels = 20  # X 방향 픽셀 수
y_pixels = 15  # Y 방향 픽셀 수

# ===== 출력 폴더 생성 =====
if not os.path.exists(pathName):
    os.makedirs(pathName)
data_path = os.path.join(pathName, 'data')
if not os.path.exists(data_path):
    os.makedirs(data_path)

print("=" * 50)
print("2포트 필터 GDS 생성")
print("=" * 50)

# ===== 기판 정의 =====
sub1 = MicrostripSub(t, cond, h, er, fc)

# 포트 폭/길이 계산
w_l, l_l = MicrostripCalc.synth_microstrip(sub1, z0, el_ports)
print(f"포트 폭: {w_l:.2f} mil")
print(f"포트 길이: {l_l:.2f} mil")

# 프로토타입 치수 계산
launch_pixels = round(l_l / pixelSize)
launch_l_pixels = int(launch_pixels * pixelSize / pixelSize)
xProto = x_pixels
yProto = y_pixels

print(f"디자인 영역: {xProto} x {yProto} pixels ({xProto*pixelSize} x {yProto*pixelSize} mils)")

# ===== 랜덤 2포트 필터 생성 =====
seed = datetime.now()  # 현재 시간을 시드로 사용 (매번 다른 디자인)
# seed = 12345  # 고정 시드를 원하면 이 줄 사용

base_name = f"{ports}Port_{x_pixels}x{y_pixels}_ps{pixelSize}"
outFile = os.path.join(pathName, base_name)

# RandomComponent 객체 생성
rrfc1 = RandomComponent(
    unit=layoutUnit,
    ports=ports,
    sides=sides,
    corner=corner,
    connect=connectMap,
    minPix=minPixel,
    pixelSize=pixelSize,
    layoutRes=layoutRes,
    scale=scale,
    launchLen=el_ports,
    seed=seed,
    sim='ADS',
    view=False,
    write=True,
    outF=outFile,
    sym=sym,
    shape=shape,
    portPosition=''
)

# GDS 파일 생성 시도
max_attempts = 100
attempt = 0

while attempt < max_attempts:
    portPosition, xBoard, yBoard, csv_file, gds_file, cell, _ = rrfc1.random_gds_dim(
        sub1, xProto * pixelSize, yProto * pixelSize, z0
    )

    # 파일이 생성되었는지 확인
    if csv_file and os.path.isfile(csv_file) and os.path.getsize(csv_file) > 0:
        break

    attempt += 1
    # 새로운 시드로 재시도
    seed = datetime.now()
    rrfc1 = RandomComponent(
        unit=layoutUnit,
        ports=ports,
        sides=sides,
        corner=corner,
        connect=connectMap,
        minPix=minPixel,
        pixelSize=pixelSize,
        layoutRes=layoutRes,
        scale=scale,
        launchLen=el_ports,
        seed=seed,
        sim='ADS',
        view=False,
        write=True,
        outF=outFile,
        sym=sym,
        shape=shape,
        portPosition=''
    )

if csv_file and gds_file and os.path.isfile(gds_file):
    print(f"\n{'=' * 50}")
    print("생성 완료!")
    print(f"{'=' * 50}")
    print(f"GDS 파일: {gds_file}")
    print(f"CSV 파일: {csv_file}")
    print(f"셀 이름: {cell}")
    print(f"\n[ADS에서 레이아웃 확인 방법]")
    print(f"1. ADS 실행")
    print(f"2. File -> Import -> GDSII...")
    print(f"3. GDS 파일 선택: {gds_file}")
    print(f"4. Library 선택 후 OK")
    print(f"5. Cell 목록에서 '{cell}' 선택하여 Layout 열기")
else:
    print(f"\n디자인 생성 실패 ({attempt}회 시도)")
    print("가능한 원인:")
    print("- DC 연결 조건을 만족하는 디자인을 찾지 못함")
    print("해결 방법:")
    print("- connectMap을 [0,0,0,0,0,0]으로 변경 (DC 연결 강제 해제)")
    print("- 픽셀 그리드 크기 증가")
