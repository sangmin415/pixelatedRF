"""
ADS Python 콘솔용 2포트 필터 레이아웃 생성 스크립트 (ADS 2024)

사용법:
1. ADS 실행 및 워크스페이스 열기
2. Tools -> Command Line -> Python Console 열기
3. 이 스크립트 내용을 복사하여 붙여넣기
   또는: exec(open(r"경로\ads_python_2port_filter.py").read())
"""

import numpy as np
import random
from datetime import datetime
from keysight.ads import de
from keysight.ads.de.experimental.design_editor import DesignEditor
from keysight.ads.de.experimental_uu import db

# ===== 사용자 설정 =====
lib_name = "1112sangmin_lib"   # ADS 라이브러리 이름
cell_name = "TwoPortFilter"    # 생성할 셀 이름
layer_id = 1                   # 레이아웃 레이어 번호

# ===== 기판 파라미터 =====
fc = 5.0e9      # 중심 주파수 (Hz)
z0 = 50         # 특성 임피던스 (Ohms)
t = 2.8         # 도체 두께 (mils)
cond = 5.88e7   # 전도도 (S/m)
h = 30          # 기판 높이 (mils)
er = 4.5        # 비유전율

# ===== 레이아웃 파라미터 =====
pixelSize = 18      # 픽셀 크기 (mils)
x_pixels = 20       # X 방향 픽셀 수
y_pixels = 15       # Y 방향 픽셀 수
sym = 'y-axis'      # 대칭: 'x-axis', 'y-axis', 'xy-axis', 'none'
port_width = 50     # 포트 폭 (mils) - 대략적인 값, 실제로는 계산 필요

# 단위 변환 (mils to um)
mil_to_um = 25.4

# ===== 마이크로스트립 계산 함수 =====
def calc_microstrip_width(h, er, z0):
    """특성 임피던스에서 마이크로스트립 폭 계산 (근사식)"""
    A = z0/60 * np.sqrt((er+1)/2) + (er-1)/(er+1) * (0.23 + 0.11/er)
    w_h = 8*np.exp(A) / (np.exp(2*A) - 2)
    if w_h > 2:
        B = 377*np.pi / (2*z0*np.sqrt(er))
        w_h = 2/np.pi * (B - 1 - np.log(2*B - 1) + (er-1)/(2*er) * (np.log(B-1) + 0.39 - 0.61/er))
    return w_h * h

def synth_microstrip(h, er, z0, el_deg, freq):
    """포트 폭과 길이 계산"""
    w = calc_microstrip_width(h, er, z0)
    # 유효 유전율 계산
    u = w / h
    a = 1 + (1/49)*np.log((u**4 + (u/52)**2)/(u**4 + 0.432)) + (1/18.7)*np.log(1 + (u/18.1)**3)
    b = 0.564 * ((er - 0.9)/(er + 3))**0.053
    er_eff = (er + 1)/2 + (er - 1)/2 * (1 + 10/u)**(-a*b)
    # 파장 계산
    c = 3e8 * 1000 * 39.37  # mm/s to mil/s
    wavelength = c / (freq * np.sqrt(er_eff))
    length = wavelength * el_deg / 360
    return w, length

# 포트 치수 계산
port_w, port_l = synth_microstrip(h, er, z0, 30, fc)
launch_pixels = int(round(port_l / pixelSize))

print(f"포트 폭: {port_w:.2f} mil")
print(f"포트 길이: {port_l:.2f} mil ({launch_pixels} pixels)")

# ===== 랜덤 픽셀맵 생성 =====
def generate_random_pixelmap(rows, cols, symmetry='y-axis'):
    """랜덤 픽셀맵 생성"""
    if symmetry == 'y-axis':
        half_cols = (cols + 1) // 2
        half_map = np.random.randint(0, 2, (rows, half_cols))
        if cols % 2 == 0:
            pixmap = np.hstack([half_map, np.fliplr(half_map)])
        else:
            pixmap = np.hstack([half_map, np.fliplr(half_map[:, :-1])])
    elif symmetry == 'x-axis':
        half_rows = (rows + 1) // 2
        half_map = np.random.randint(0, 2, (half_rows, cols))
        if rows % 2 == 0:
            pixmap = np.vstack([half_map, np.flipud(half_map)])
        else:
            pixmap = np.vstack([half_map, np.flipud(half_map[:-1, :])])
    elif symmetry == 'xy-axis':
        half_rows = (rows + 1) // 2
        half_cols = (cols + 1) // 2
        quarter_map = np.random.randint(0, 2, (half_rows, half_cols))
        if cols % 2 == 0:
            half_map = np.hstack([quarter_map, np.fliplr(quarter_map)])
        else:
            half_map = np.hstack([quarter_map, np.fliplr(quarter_map[:, :-1])])
        if rows % 2 == 0:
            pixmap = np.vstack([half_map, np.flipud(half_map)])
        else:
            pixmap = np.vstack([half_map, np.flipud(half_map[:-1, :])])
    else:  # 'none' or asymmetric
        pixmap = np.random.randint(0, 2, (rows, cols))

    return pixmap

# 시드 설정
random.seed(datetime.now().microsecond)
np.random.seed(datetime.now().microsecond)

# 픽셀맵 생성
pixmap = generate_random_pixelmap(y_pixels, x_pixels, sym)

# 포트 연결을 위해 첫번째와 마지막 열의 중앙 픽셀 활성화
mid_row = y_pixels // 2
port_height = max(3, int(port_w / pixelSize))  # 포트 높이 (픽셀)

for i in range(max(0, mid_row - port_height//2), min(y_pixels, mid_row + port_height//2 + 1)):
    pixmap[i, 0] = 1  # 왼쪽 포트
    pixmap[i, -1] = 1  # 오른쪽 포트

# 런치 라인 추가
total_cols = x_pixels + 2 * launch_pixels
full_pixmap = np.zeros((y_pixels, total_cols), dtype=int)

# 중앙에 랜덤 픽셀맵 배치
full_pixmap[:, launch_pixels:launch_pixels+x_pixels] = pixmap

# 런치 라인 (포트 연결부) 추가
for i in range(max(0, mid_row - port_height//2), min(y_pixels, mid_row + port_height//2 + 1)):
    full_pixmap[i, :launch_pixels] = 1  # 왼쪽 런치
    full_pixmap[i, -launch_pixels:] = 1  # 오른쪽 런치

print(f"전체 픽셀맵 크기: {full_pixmap.shape[1]} x {full_pixmap.shape[0]} pixels")

# ===== ADS 레이아웃 생성 =====
print("\nADS 레이아웃 생성 중...")

# 라이브러리 확인
if not de.library_is_open(lib_name):
    print(f"라이브러리 '{lib_name}'가 열려있지 않습니다.")
    print("먼저 ADS에서 워크스페이스와 라이브러리를 열어주세요.")
    raise Exception(f"Library '{lib_name}' not open")

lib = de.get_open_library(lib_name)
print(f"라이브러리 '{lib_name}' 확인됨")

# 기존 셀이 있으면 확인
view_name = "layout"
if de.cellview_exists(lib_name, cell_name, view_name):
    print(f"기존 셀 '{cell_name}' 발견됨 - 덮어씁니다")

# 새 레이아웃 셀 생성
cell = lib.create_cell(cell_name)
layout_view = cell.create_cellview(view_name)
print(f"새 셀 '{cell_name}' 생성됨")

# DesignEditor로 레이아웃 편집
editor = DesignEditor(lib_name, cell_name)

# 픽셀을 사각형으로 변환
pixel_size_um = pixelSize * mil_to_um
rect_count = 0

for row in range(full_pixmap.shape[0]):
    for col in range(full_pixmap.shape[1]):
        if full_pixmap[row, col] == 1:
            # 좌표 계산 (um 단위)
            x1 = col * pixel_size_um
            y1 = row * pixel_size_um
            x2 = (col + 1) * pixel_size_um
            y2 = (row + 1) * pixel_size_um

            # 사각형 추가
            editor.add_rect(layer_id, 0, x1, y1, x2, y2)  # layer_id, datatype, x1, y1, x2, y2
            rect_count += 1

print(f"사각형 {rect_count}개 생성됨")

# 포트 추가
port_y = mid_row * pixel_size_um + pixel_size_um / 2
port_width_um = port_w * mil_to_um

# 포트 1 (왼쪽)
port1_x = 0
editor.add_pin("P1", layer_id, 0, port1_x, port_y - port_width_um/2,
               port1_x + pixel_size_um, port_y + port_width_um/2)

# 포트 2 (오른쪽)
port2_x = full_pixmap.shape[1] * pixel_size_um
editor.add_pin("P2", layer_id, 0, port2_x - pixel_size_um, port_y - port_width_um/2,
               port2_x, port_y + port_width_um/2)

print("포트 2개 추가됨")

# 변경사항 저장
lib.save()

# 셀 열기 (UI에서)
de.ui.open_design(lib_name, cell_name, view_name)

print(f"\n===== 완료 =====")
print(f"라이브러리: {lib_name}")
print(f"셀 이름: {cell_name}")
print(f"레이아웃이 자동으로 열렸습니다.")
