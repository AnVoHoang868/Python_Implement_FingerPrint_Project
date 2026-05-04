"""
Bước 4B: Trích xuất Đặc trưng Level 1 - Singular Points & Pattern Classification
==================================================================================
Mục tiêu:
  Tìm các điểm kỳ dị (Singular Points) trên ảnh vân tay:
    - Core  (Tâm vân)     : Nơi các đường vân quay vòng lại
    - Delta (Tam giác vân) : Nơi 3 hệ đường vân giao nhau

  Sau đó phân loại vân tay (Pattern Classification) dựa trên số lượng Core/Delta:
    - Arch       : 0 Core, 0 Delta  (đường vân chạy ngang, không cuộn)
    - Left_Loop  : 1 Core, 1 Delta  (Delta nằm bên PHẢI Core)
    - Right_Loop : 1 Core, 1 Delta  (Delta nằm bên TRÁI Core)
    - Whorl      : 2 Core, 2 Delta  (đường vân xoáy tròn)
    - Unknown    : Các trường hợp khác (ảnh nhiễu, mất viền...)

Phương pháp: Poincare Index
  ┌───────────────────────────────────────────────────────────────────────┐
  │ Với mỗi pixel (x, y) trên bản đồ hướng (Orientation Field):        │
  │                                                                       │
  │ 1. Lấy các giá trị góc xung quanh pixel đó theo vòng tròn kín       │
  │    (8 pixel lân cận hoặc vòng tròn bán kính r)                      │
  │                                                                       │
  │ 2. Tính TỔNG chênh lệch góc δ giữa các pixel liên tiếp trên vòng   │
  │    → Chuẩn hóa δ về [-π/2, π/2] (vì hướng vân có chu kỳ π)        │
  │                                                                       │
  │ 3. Kết quả (Poincare Index):                                         │
  │    → PI =  π  (180°) → Đây là CORE                                  │
  │    → PI = -π (-180°) → Đây là DELTA                                 │
  │    → PI =  0  (  0°) → Pixel bình thường                            │
  └───────────────────────────────────────────────────────────────────────┘

Tham khảo:
  Maltoni, D., Maio, D., Jain, A. K., & Prabhakar, S. (2009).
  "Handbook of Fingerprint Recognition" (2nd ed.), Chapter 3.
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# ============================================================================
# CẤU HÌNH
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# BƯỚC 4B-1: TÍNH POINCARE INDEX
# ============================================================================
def compute_poincare_index(orient_img, mask, block_size=8):
    """
    Tính chỉ số Poincare tại mỗi block trên bản đồ hướng (Orientation Field).

    Thuật toán:
      1. Chia ảnh thành các block (block_size x block_size pixel).
      2. Tại mỗi block, lấy 8 block lân cận theo chiều kim đồng hồ.
      3. Tính tổng chênh lệch góc giữa các block liên tiếp.
      4. Chuẩn hóa chênh lệch về [-π/2, π/2].
      5. Poincare Index = tổng các chênh lệch đã chuẩn hóa.

    Tham số:
      orient_img: Bản đồ hướng vân (radian, từ bước 04)
      mask:       Mặt nạ vùng vân tay (1 = vân, 0 = nền)
      block_size: Kích thước block (mặc định 8 pixel, phù hợp ảnh nhỏ SOCOFing)

    Returns:
      poincare_map: Ma trận chỉ số Poincare (dạng radian)
                    Core  ≈ +π (≈ 3.14)
                    Delta ≈ -π (≈ -3.14)
                    Bình thường ≈ 0
    """
    rows, cols = orient_img.shape
    # Số block theo chiều dọc và ngang
    blk_rows = rows // block_size
    blk_cols = cols // block_size

    # Tính giá trị hướng trung bình tại mỗi block
    orient_blocks = np.zeros((blk_rows, blk_cols))
    mask_blocks = np.zeros((blk_rows, blk_cols))

    for i in range(blk_rows):
        for j in range(blk_cols):
            r_start = i * block_size
            c_start = j * block_size
            block_orient = orient_img[r_start:r_start + block_size,
                                      c_start:c_start + block_size]
            block_mask = mask[r_start:r_start + block_size,
                              c_start:c_start + block_size]

            # Chỉ tính nếu block nằm trong vùng vân tay (>50% pixel là vân)
            if np.mean(block_mask) > 0.5:
                orient_blocks[i, j] = np.mean(block_orient)
                mask_blocks[i, j] = 1

    # Ma trận kết quả Poincare
    poincare_map = np.zeros((blk_rows, blk_cols))

    # 8 hướng lân cận theo chiều kim đồng hồ (bắt đầu từ trên-trái)
    # Thứ tự: ↖ ↑ ↗ → ↘ ↓ ↙ ←
    neighbors = [(-1, -1), (-1, 0), (-1, 1), (0, 1),
                 (1, 1), (1, 0), (1, -1), (0, -1)]

    for i in range(1, blk_rows - 1):
        for j in range(1, blk_cols - 1):
            if mask_blocks[i, j] == 0:
                continue

            # Kiểm tra tất cả 8 lân cận đều nằm trong vùng vân
            all_valid = True
            for di, dj in neighbors:
                if mask_blocks[i + di, j + dj] == 0:
                    all_valid = False
                    break
            if not all_valid:
                continue

            # Lấy chuỗi 8 giá trị hướng xung quanh + lặp lại pixel đầu (tạo vòng kín)
            angles = []
            for di, dj in neighbors:
                angles.append(orient_blocks[i + di, j + dj])
            angles.append(angles[0])  # Đóng vòng

            # Tính tổng chênh lệch góc
            poincare_sum = 0.0
            for k in range(len(angles) - 1):
                delta = angles[k + 1] - angles[k]

                # Chuẩn hóa delta về [-π/2, π/2]
                # (Vì orientation field có chu kỳ π, không phải 2π)
                while delta > np.pi / 2:
                    delta -= np.pi
                while delta < -np.pi / 2:
                    delta += np.pi

                poincare_sum += delta

            poincare_map[i, j] = poincare_sum

    return poincare_map, orient_blocks, mask_blocks


# ============================================================================
# BƯỚC 4B-2: TÌM CORE VÀ DELTA
# ============================================================================
def find_singularities(poincare_map, mask_blocks, block_size=8,
                       core_threshold=0.7, delta_threshold=0.7):
    """
    Tìm vị trí các điểm Core và Delta từ bản đồ Poincare.

    Thuật toán:
      - Core:  Poincare Index ≈ +π → Tìm các block có PI > core_threshold * π
      - Delta: Poincare Index ≈ -π → Tìm các block có PI < -delta_threshold * π

    Hậu xử lý:
      - Gom cụm (clustering) các block gần nhau thành 1 điểm kỳ dị
      - Lọc bỏ điểm nằm quá sát biên ảnh

    Tham số:
      poincare_map:    Ma trận Poincare Index
      mask_blocks:     Mặt nạ vùng vân (dạng block)
      block_size:      Kích thước 1 block (pixel)
      core_threshold:  Ngưỡng phát hiện Core (0.7 = 70% của π, nới lỏng cho ảnh nhỏ)
      delta_threshold: Ngưỡng phát hiện Delta

    Returns:
      cores:  list of (x, y) — Tọa độ pixel các điểm Core
      deltas: list of (x, y) — Tọa độ pixel các điểm Delta
    """
    blk_rows, blk_cols = poincare_map.shape

    core_blocks = []
    delta_blocks = []

    for i in range(blk_rows):
        for j in range(blk_cols):
            if mask_blocks[i, j] == 0:
                continue

            pi_val = poincare_map[i, j]

            # Kiểm tra Core (PI ≈ +π)
            if pi_val > core_threshold * np.pi:
                core_blocks.append((j, i))  # (col, row) → (x, y)

            # Kiểm tra Delta (PI ≈ -π)
            elif pi_val < -delta_threshold * np.pi:
                delta_blocks.append((j, i))

    # Gom cụm: Nếu 2 điểm Core cách nhau < 3 block → gộp thành 1
    cores = _cluster_points(core_blocks, min_dist=3)
    deltas = _cluster_points(delta_blocks, min_dist=3)

    # Chuyển từ tọa độ block → tọa độ pixel (tâm block)
    cores_px = [(int(x * block_size + block_size // 2),
                 int(y * block_size + block_size // 2)) for x, y in cores]
    deltas_px = [(int(x * block_size + block_size // 2),
                  int(y * block_size + block_size // 2)) for x, y in deltas]

    # Lọc bỏ điểm nằm quá sát biên (< 1 block từ biên)
    # Giảm margin cho ảnh nhỏ SOCOFing (96×103 pixel)
    img_h = blk_rows * block_size
    img_w = blk_cols * block_size
    margin = block_size * 1

    cores_px = [(x, y) for x, y in cores_px
                if margin < x < img_w - margin and margin < y < img_h - margin]
    deltas_px = [(x, y) for x, y in deltas_px
                 if margin < x < img_w - margin and margin < y < img_h - margin]

    return cores_px, deltas_px


def _cluster_points(points, min_dist=2):
    """
    Gom các điểm gần nhau thành 1 cụm (lấy trung bình tọa độ).
    Tránh việc 1 Core/Delta bị phát hiện thành nhiều điểm sát nhau.
    """
    if len(points) == 0:
        return []

    points = list(points)
    clusters = []
    used = [False] * len(points)

    for i in range(len(points)):
        if used[i]:
            continue

        cluster = [points[i]]
        used[i] = True

        for j in range(i + 1, len(points)):
            if used[j]:
                continue

            dist = np.sqrt((points[i][0] - points[j][0]) ** 2 +
                           (points[i][1] - points[j][1]) ** 2)
            if dist < min_dist:
                cluster.append(points[j])
                used[j] = True

        # Tâm cụm = trung bình tọa độ
        cx = np.mean([p[0] for p in cluster])
        cy = np.mean([p[1] for p in cluster])
        clusters.append((cx, cy))

    return clusters


# ============================================================================
# BƯỚC 4B-3: PHÂN LOẠI VÂN TAY (PATTERN CLASSIFICATION)
# ============================================================================
def classify_fingerprint(cores, deltas):
    """
    Phân loại vân tay dựa trên số lượng và vị trí Core/Delta.

    Quy tắc phân loại (theo Henry Classification System):
      ┌──────────────┬────────┬────────┬──────────────────────────┐
      │ Pattern      │ Cores  │ Deltas │ Điều kiện                │
      ├──────────────┼────────┼────────┼──────────────────────────┤
      │ Arch         │   0    │   0    │ Không có Core & Delta    │
      │ Left_Loop    │   1    │   1    │ Delta nằm PHẢI Core      │
      │ Right_Loop   │   1    │   1    │ Delta nằm TRÁI Core      │
      │ Whorl        │  ≥2    │  ≥2    │ Nhiều Core và Delta      │
      │ Unknown      │  khác  │  khác  │ Không đủ điều kiện       │
      └──────────────┴────────┴────────┴──────────────────────────┘

    Returns:
      pattern_class: str — 'Arch', 'Left_Loop', 'Right_Loop', 'Whorl', 'Unknown'
    """
    n_cores = len(cores)
    n_deltas = len(deltas)

    # Trường hợp 1: Arch — Không có Core/Delta
    if n_cores == 0 and n_deltas == 0:
        return "Arch"

    # Trường hợp 2: Whorl — 2+ Core, 2+ Delta
    if n_cores >= 2 and n_deltas >= 2:
        return "Whorl"

    # Trường hợp 3: Loop — 1 Core, 1 Delta
    if n_cores == 1 and n_deltas == 1:
        core_x = cores[0][0]
        delta_x = deltas[0][0]

        if delta_x > core_x:
            # Delta nằm bên PHẢI Core → Left Loop
            return "Left_Loop"
        else:
            # Delta nằm bên TRÁI Core → Right Loop
            return "Right_Loop"

    # Trường hợp 4: Chỉ có Core mà không có Delta (hoặc ngược lại)
    # → Có thể là Loop nhưng ảnh bị cắt mất phần Delta
    if n_cores == 1 and n_deltas == 0:
        return "Arch"  # Coi như Arch (thiếu Delta → không đủ bằng chứng)

    if n_cores >= 2 and n_deltas <= 1:
        return "Whorl"  # Có 2+ Core → khả năng cao là Whorl

    # Mặc định
    return "Unknown"


# ============================================================================
# BƯỚC 4B-4: HÀM TỔNG HỢP (Entry Point)
# ============================================================================
def extract_level1_features(orient_img, mask, block_size=8):
    """
    Hàm chính: Trích xuất toàn bộ đặc trưng Level 1 từ Orientation Field.

    Pipeline:
      orient_img → Poincare Index → Core/Delta → Pattern Classification

    Tham số:
      orient_img: Bản đồ hướng vân (từ bước 04)
      mask:       Mặt nạ vùng vân tay
      block_size: Kích thước block cho Poincare (mặc định 8, phù hợp ảnh nhỏ SOCOFing)

    Returns:
      level1: dict chứa:
        - 'pattern_class': str ('Arch', 'Left_Loop', 'Right_Loop', 'Whorl', 'Unknown')
        - 'cores':  list of (x, y) — Tọa độ pixel các điểm Core
        - 'deltas': list of (x, y) — Tọa độ pixel các điểm Delta
        - 'n_cores': int
        - 'n_deltas': int
    """
    # 1. Tính Poincare Index
    poincare_map, orient_blocks, mask_blocks = compute_poincare_index(
        orient_img, mask, block_size
    )

    # 2. Tìm Core & Delta
    cores, deltas = find_singularities(
        poincare_map, mask_blocks, block_size,
        core_threshold=0.7, delta_threshold=0.7
    )

    # 3. Phân loại
    pattern_class = classify_fingerprint(cores, deltas)

    level1 = {
        "pattern_class": pattern_class,
        "cores": cores,
        "deltas": deltas,
        "n_cores": len(cores),
        "n_deltas": len(deltas),
    }

    return level1


# ============================================================================
# TRỰC QUAN HÓA
# ============================================================================
def visualize_singular_points(img, orient_img, mask, level1, save_path=None):
    """
    Vẽ ảnh vân tay với Core (đỏ) và Delta (xanh lá) được đánh dấu.
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f"Level 1 Features — Pattern: {level1['pattern_class']}",
                 fontsize=14, fontweight='bold')

    # Hình 1: Ảnh gốc
    axes[0].imshow(img, cmap='gray')
    axes[0].set_title("Ảnh Gốc")
    axes[0].axis('off')

    # Hình 2: Orientation + Singular Points
    axes[1].imshow(img, cmap='gray')
    # Vẽ Core (màu đỏ, hình tròn)
    for cx, cy in level1["cores"]:
        circle = plt.Circle((cx, cy), 6, color='red', fill=False, linewidth=2)
        axes[1].add_patch(circle)
        axes[1].plot(cx, cy, 'r+', markersize=10, markeredgewidth=2)
    # Vẽ Delta (màu xanh lá, hình tam giác)
    for dx, dy in level1["deltas"]:
        triangle = plt.Polygon(
            [(dx, dy - 8), (dx - 7, dy + 5), (dx + 7, dy + 5)],
            fill=False, edgecolor='lime', linewidth=2
        )
        axes[1].add_patch(triangle)
        axes[1].plot(dx, dy, 'g+', markersize=10, markeredgewidth=2)

    axes[1].set_title(f"Core (Đỏ ●) & Delta (Xanh △)\n"
                      f"Cores={level1['n_cores']}, Deltas={level1['n_deltas']}")
    axes[1].axis('off')

    # Hình 3: Thông tin chi tiết
    info_text = (
        f"PATTERN CLASS: {level1['pattern_class']}\n\n"
        f"Số Core  : {level1['n_cores']}\n"
        f"Số Delta : {level1['n_deltas']}\n\n"
    )
    if level1["cores"]:
        info_text += "Core positions:\n"
        for i, (cx, cy) in enumerate(level1["cores"]):
            info_text += f"  Core {i+1}: ({cx}, {cy})\n"
    if level1["deltas"]:
        info_text += "\nDelta positions:\n"
        for i, (dx, dy) in enumerate(level1["deltas"]):
            info_text += f"  Delta {i+1}: ({dx}, {dy})\n"

    axes[2].text(0.1, 0.5, info_text, fontsize=12, family='monospace',
                 verticalalignment='center', transform=axes[2].transAxes,
                 bbox=dict(boxstyle='round', facecolor='lightyellow'))
    axes[2].set_title("Thông tin Level 1")
    axes[2].axis('off')

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"  Đã lưu hình: {save_path}")
    # plt.show()


# ============================================================================
# CHƯƠNG TRÌNH CHÍNH (Demo độc lập)
# ============================================================================
if __name__ == "__main__":
    from importlib.util import spec_from_file_location, module_from_spec

    def _import_module(name, filepath):
        spec = spec_from_file_location(name, filepath)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    step03 = _import_module("s03", os.path.join(BASE_DIR, "03_enhancement.py"))
    step04 = _import_module("s04", os.path.join(BASE_DIR, "04_orientation_field.py"))

    # Thử với 1 ảnh mẫu
    DATASET_PATH = os.path.join(BASE_DIR, "DataFingerPrint", "fingerPrint",
                                "SOCOFing", "Real")
    sample = os.path.join(DATASET_PATH, "1__M_Left_index_finger.BMP")

    if not os.path.exists(sample):
        print(f"Lỗi: Không tìm thấy ảnh mẫu tại {sample}")
    else:
        img = cv2.imread(sample, cv2.IMREAD_GRAYSCALE)
        enhanced, mask, _ = step03.full_enhancement_pipeline(
            img, clip_limit=2.5, grid_size=(8, 8),
            block_size=16, var_threshold=0.005
        )
        orient_img, reliability = step04.estimate_orientation(enhanced)

        level1 = extract_level1_features(orient_img, mask, block_size=8)

        print(f"Pattern Class : {level1['pattern_class']}")
        print(f"Cores  ({level1['n_cores']}): {level1['cores']}")
        print(f"Deltas ({level1['n_deltas']}): {level1['deltas']}")

        save_path = os.path.join(OUTPUT_DIR, "04b_singular_points.png")
        visualize_singular_points(img, orient_img, mask, level1, save_path)
