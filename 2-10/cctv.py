# cctv.py
# 요구사항:
# - cctv.zip에서 이미지 파일만 추출하여 사전순으로 순회
# - OpenCV(HOG)로 사람 검출
# - 임의 각도(대각 포함) 회전 검출: 여러 각도에서 detect → 원본 좌표계로 역투영 → NMS로 통합
# - 사람을 찾은 사진만 화면에 표시(Enter 키로 다음 진행)
# - 마지막까지 끝나면 "검색이 끝났습니다." 출력 후 종료
# - 표준 라이브러리 + OpenCV만 사용, 불필요한 경고/에러 출력 없음

import os
import sys
import zipfile
import tempfile
import shutil

import cv2  # 사람 검출/표시용 (허용됨)
import numpy as np

def imread_unicode(path, flags=cv2.IMREAD_COLOR):
    try:
        data = np.fromfile(path, dtype=np.uint8)   # Windows 한글 경로 OK
        if data.size == 0:
            return None
        return cv2.imdecode(data, flags)
    except Exception:
        return None


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff'}

# 탐지 각도 설정(대각선 포함): -75°~75°(15° 간격) + 위/아래 반전(180° 오프셋)
_BASE_ANGLES = list(range(-75, 76, 15))  # -75, -60, ... , 60, 75
ANGLES = _BASE_ANGLES + [a + 180 for a in _BASE_ANGLES]  # 총 22개 각도

# ---------------------------
# 유틸: 이미지 파일 필터/추출
# ---------------------------
def is_image_file(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in IMAGE_EXTS

def extract_images_from_zip(zip_path: str, dest_dir: str):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        infos = [i for i in zf.infolist() if (not i.is_dir()) and is_image_file(i.filename)]
        infos.sort(key=lambda i: i.filename.lower())
        out = []
        for info in infos:
            try:
                out.append(zf.extract(info, path=dest_dir))
            except Exception:
                # 손상/권한 문제 파일은 조용히 스킵
                pass
        return out

# ---------------------------
# 전처리: 크기/밝기/대비 보정
# ---------------------------
def prepare_image(img):
    if img is None:
        return None
    h, w = img.shape[:2]

    # 속도/메모리 절약: 폭을 1400px로 제한
    max_w = 1400
    if w > max_w:
        scale = max_w / float(w)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    # 조명 개선: CLAHE (YCrCb의 Y채널)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    y, cr, cb = cv2.split(ycrcb)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    y = clahe.apply(y)
    img = cv2.cvtColor(cv2.merge([y, cr, cb]), cv2.COLOR_YCrCb2BGR)

    return img

# ---------------------------
# 임의 각도 회전(캔버스 보존) + 변환행렬
# ---------------------------
def rotate_bound_with_matrix(image, angle_deg):
    """
    이미지 중심 기준 angle_deg만큼 회전하되,
    잘림 없이 새 캔버스 크기를 맞춘 결과와 forward affine 행렬을 반환.
    반환: rotated_img, M(2x3), (newW, newH)
    """
    (h, w) = image.shape[:2]
    (cX, cY) = (w / 2.0, h / 2.0)

    M = cv2.getRotationMatrix2D((cX, cY), angle_deg, 1.0)
    cos = abs(M[0, 0])
    sin = abs(M[0, 1])

    # 새 경계 크기 계산
    nW = int((h * sin) + (w * cos) + 0.5)
    nH = int((h * cos) + (w * sin) + 0.5)

    # 이동 보정(새 캔버스 중앙 정렬)
    M[0, 2] += (nW / 2.0) - cX
    M[1, 2] += (nH / 2.0) - cY

    rotated = cv2.warpAffine(image, M, (nW, nH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return rotated, M, (nW, nH)

def map_rects_back_affine(rects, M, orig_w, orig_h):
    """
    회전된 좌표계의 박스 목록(rects: (x,y,w,h))을
    원본 좌표계로 되투영.
    M은 forward(원본→회전) 2x3, 여기서는 inverse를 사용.
    """
    invM = cv2.invertAffineTransform(M)
    mapped = []
    for (rx, ry, rw, rh) in rects:
        # 회전 좌표계에서 박스 코너 4점
        pts = np.array([
            [rx,         ry        , 1.0],
            [rx + rw,    ry        , 1.0],
            [rx,         ry + rh   , 1.0],
            [rx + rw,    ry + rh   , 1.0],
        ], dtype=np.float32)
        # 원본 좌표계로 역변환
        orig = (invM @ pts.T).T  # shape (4,2)
        xs = orig[:, 0]
        ys = orig[:, 1]
        x0 = max(0, int(np.floor(xs.min())))
        y0 = max(0, int(np.floor(ys.min())))
        x1 = min(orig_w - 1, int(np.ceil(xs.max())))
        y1 = min(orig_h - 1, int(np.ceil(ys.max())))
        w = max(0, x1 - x0)
        h = max(0, y1 - y0)
        if w > 0 and h > 0:
            mapped.append((x0, y0, w, h))
    return mapped

# ---------------------------
# HOG 사람 검출
# ---------------------------
def detect_people_hog(img, hog):
    # HOG 파라미터를 다소 민감하게 조정 (대각/원거리 대응)
    rects, weights = hog.detectMultiScale(
        img,
        winStride=(6, 6),   # 기본(8,8)보다 조밀
        padding=(8, 8),
        scale=1.03,         # 더 촘촘
        useMeanshiftGrouping=False
    )
    if weights is None or len(weights) != len(rects):
        weights = [1.0] * len(rects)
    # numpy 배열을 파이썬 튜플로 전환(이후 처리 용이)
    rects = [tuple(map(int, r)) for r in rects]
    weights = [float(w) for w in weights]
    return rects, weights

def nms_boxes(rects, scores, score_thr=0.2, nms_thr=0.35):
    """OpenCV NMS로 중복 박스 억제"""
    if not rects:
        return []
    boxes = [list(map(int, r)) for r in rects]
    idxs = cv2.dnn.NMSBoxes(boxes, scores, score_thr, nms_thr)
    if len(idxs) == 0:
        return []
    out = []
    for i in idxs:
        out.append(boxes[int(i if not isinstance(i, (list, tuple)) else i[0])])
    return out

# ---------------------------
# 표시
# ---------------------------
def show_with_boxes(img, rects, title: str):
    for (x, y, w, h) in rects:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imshow('CCTV', img)
    cv2.setWindowTitle('CCTV', title)
    while True:
        key = cv2.waitKey(0) & 0xFF
        if key in (13, 10):  # Enter
            break

# ---------------------------
# 메인
# ---------------------------
def main():
    default_zip = r"C:\Users\류은진\Desktop\류은진\codyssey\2-10\cctv.zip"

    # 실행할 때 인자를 주면 그걸 사용, 없으면 default_zip 사용
    zip_path = sys.argv[1] if len(sys.argv) > 1 else default_zip
    zip_path = os.path.abspath(zip_path)

    if not os.path.exists(zip_path):
        print(f'ZIP 파일을 찾을 수 없습니다: {zip_path}')
        return

    # HOG 사람 검출기 초기화(내장 SVM 가중치)
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    temp_dir = tempfile.mkdtemp(prefix='cctv_')
    try:
        image_files = extract_images_from_zip(zip_path, temp_dir)
        total = len(image_files)
        if total == 0:
            print('ZIP 안에 이미지 파일이 없습니다.')
            return

        for idx, path in enumerate(image_files, 1):
            img0 = imread_unicode(path)
            if img0 is None:
                continue

            img = prepare_image(img0)
            if img is None:
                continue

            H, W = img.shape[:2]

            # 여러 각도에서 검출 → 원본 좌표계로 되투영 → 통합
            all_rects = []
            all_scores = []

            for angle in ANGLES:
                rot, M, _ = rotate_bound_with_matrix(img, angle)
                rects, weights = detect_people_hog(rot, hog)
                if len(rects) == 0:
                    continue
                mapped = map_rects_back_affine(rects, M, W, H)
                if not mapped:
                    continue
                all_rects.extend(mapped)
                # detect weights를 점수로 그대로 사용
                all_scores.extend(weights if len(weights) == len(rects) else [1.0] * len(mapped))

            # NMS로 중복 제거
            final_rects = nms_boxes(all_rects, all_scores, score_thr=0.18, nms_thr=0.35)

            if len(final_rects) > 0:
                title = f'People: {len(final_rects)} | {os.path.basename(path)} [{idx}/{total}]  (Enter=다음)'
                show_with_boxes(img.copy(), final_rects, title)
                cv2.destroyWindow('CCTV')

        print('검색이 끝났습니다.')
    finally:
        cv2.destroyAllWindows()
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    main()
