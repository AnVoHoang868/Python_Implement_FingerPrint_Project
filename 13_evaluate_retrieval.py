"""
Bước 13: Đánh giá Hệ thống Nhận dạng (Identification 1:N)
=========================================================
Mục tiêu:
  1. Lấy N ảnh truy vấn (Probe) bị biến dạng từ Altered-Easy.
  2. Với mỗi ảnh, tìm kiếm trong cơ sở dữ liệu (Gallery) để lấy danh sách xếp hạng.
  3. Tính toán Rank-1 Accuracy (Tỷ lệ đúng top 1) và Rank-5 Accuracy.
  4. Vẽ đường cong CMC (Cumulative Match Characteristic).
  5. Xuất báo cáo đánh giá hệ thống 1:N.
"""

import os
import re
import glob
import time
import random
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

# ============================================================================
# CẤU HÌNH
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_ALTERED_DIR = os.path.join(BASE_DIR, "DataFingerPrint", "fingerPrint", "SOCOFing", "Altered", "Altered-Easy")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Số lượng ảnh truy vấn dùng để test
NUM_PROBES = 100
MAX_RANK_TO_PLOT = 10

# Các ID có kích thước ảnh lỗi (bỏ qua)
ABNORMAL_IDS = {"53", "226", "270", "297", "303", "349", "354", "361", "363", "376", "560", "585", "590"}

# ============================================================================
# IMPORT MODULE
# ============================================================================
from importlib.util import spec_from_file_location, module_from_spec

def _import_module(name, filepath):
    spec = spec_from_file_location(name, filepath)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

step09 = _import_module("s09", os.path.join(BASE_DIR, "09_matching.py"))
step10 = _import_module("s10", os.path.join(BASE_DIR, "10_database_system.py"))

extract_features = step09.extract_features
match_fingerprints_kdtree = step09.match_fingerprints_kdtree
FingerprintDatabase = step10.FingerprintDatabase

def parse_filename(filename):
    """Parse SOCOFing filename → person_id"""
    m = re.match(r"(\d+)__([MF])", filename)
    if m:
        return m.group(1)
    return None

# ============================================================================
# CHƯƠNG TRÌNH ĐÁNH GIÁ
# ============================================================================
def evaluate_retrieval(db, probe_files):
    all_templates = db.get_all_templates()
    if not all_templates:
        print("Lỗi: Cơ sở dữ liệu trống! Hãy chạy 11_search_system.py để enroll trước.")
        return None

    # Tạo từ điển map template_id sang person_id (trong CSDL name lưu dạng 'Person_100')
    db_person_ids = {}
    for t in all_templates:
        # name = "Person_100" -> extract "100"
        pid = t["name"].split("_")[1]
        db_person_ids[t["template_id"]] = pid

    ranks_found = []
    errors = 0

    print(f"Đang đánh giá {len(probe_files)} ảnh truy vấn trên CSDL có {len(all_templates)} templates...")
    
    for probe_path in tqdm(probe_files, desc="Retrieval Testing"):
        true_pid = parse_filename(os.path.basename(probe_path))
        if not true_pid:
            errors += 1
            continue

        try:
            # 1. Trích xuất đặc trưng
            query_minutiae, query_level1, _ = extract_features(probe_path)
            if query_minutiae is None or len(query_minutiae) == 0:
                errors += 1
                continue
            
            query_pattern = query_level1["pattern_class"] if query_level1 else "Unknown"

            # 2. Lọc Level 1
            if query_pattern != "Unknown":
                filtered = [t for t in all_templates if t["pattern_class"] in (query_pattern, "Unknown")]
            else:
                filtered = all_templates

            # 3. Tính điểm (Matching)
            results = []
            for tmpl in filtered:
                score, _, _, _ = match_fingerprints_kdtree(query_minutiae, tmpl["minutiae"], alpha_range=5)
                results.append({
                    "template_id": tmpl["template_id"],
                    "person_id": db_person_ids[tmpl["template_id"]],
                    "score": score
                })

            # 4. Sắp xếp Ranking
            results.sort(key=lambda x: x["score"], reverse=True)

            # 5. Tìm hạng (rank) của kết quả đúng ĐẦU TIÊN
            # (Vì 1 người có nhiều ngón trong DB, chỉ cần ngón của người đó lọt Top K là tính đúng)
            hit_rank = -1
            for rank, res in enumerate(results):
                if res["person_id"] == true_pid:
                    hit_rank = rank + 1 # Rank bắt đầu từ 1
                    break
            
            ranks_found.append(hit_rank)
            
        except Exception:
            errors += 1

    return ranks_found, errors


# ============================================================================
# VẼ BIỂU ĐỒ & XUẤT BÁO CÁO
# ============================================================================
def generate_cmc_report(ranks_found, total_queries):
    """Tính và vẽ biểu đồ Cumulative Match Characteristic (CMC)"""
    
    # Những trường hợp hit_rank = -1 (tức là lọc Level 1 sai làm mất luôn đáp án) coi như không tìm thấy (Rank vô cùng)
    valid_ranks = [r for r in ranks_found if r > 0]
    
    cmc_curve = []
    # Tính tỷ lệ nhận diện đúng trong Top K (từ K=1 đến MAX_RANK_TO_PLOT)
    for k in range(1, MAX_RANK_TO_PLOT + 1):
        hits = sum(1 for r in valid_ranks if r <= k)
        cmc_curve.append(hits / total_queries)

    rank1_acc = cmc_curve[0] * 100
    rank5_acc = cmc_curve[4] * 100 if len(cmc_curve) >= 5 else 0

    # In ra console
    print("\n" + "="*40)
    print(" KẾT QUẢ ĐÁNH GIÁ RETRIEVAL 1:N")
    print("="*40)
    print(f"Tổng số ảnh truy vấn : {total_queries}")
    print(f"Rank-1 Accuracy      : {rank1_acc:.2f}% (Tỷ lệ tìm trúng đích ngay kết quả số 1)")
    print(f"Rank-5 Accuracy      : {rank5_acc:.2f}% (Tỷ lệ chủ nhân nằm trong Top 5)")
    print("="*40)

    # Vẽ biểu đồ CMC
    plt.figure(figsize=(8, 6))
    ranks = list(range(1, MAX_RANK_TO_PLOT + 1))
    plt.plot(ranks, [c * 100 for c in cmc_curve], marker='o', linestyle='-', color='b', linewidth=2, markersize=8)
    
    # Highlight Rank 1 và Rank 5
    plt.plot(1, rank1_acc, 'ro', markersize=10, label=f'Rank-1: {rank1_acc:.1f}%')
    if len(cmc_curve) >= 5:
        plt.plot(5, rank5_acc, 'go', markersize=10, label=f'Rank-5: {rank5_acc:.1f}%')
    
    plt.title('Cumulative Match Characteristic (CMC) Curve', fontsize=14, fontweight='bold')
    plt.xlabel('Rank', fontsize=12)
    plt.ylabel('Identification Rate (%)', fontsize=12)
    plt.xticks(ranks)
    plt.ylim(0, 105)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(fontsize=12)
    
    
    # Lưu file đồ thị
    save_path = os.path.join(OUTPUT_DIR, "13_cmc_curve.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Đã lưu biểu đồ: {save_path}")
    plt.close()

    # Xuất file báo cáo dạng text
    report_path = os.path.join(OUTPUT_DIR, "13_retrieval_results.txt")
    from datetime import datetime
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("  FINGERPRINT SYSTEM - IDENTIFICATION REPORT (1:N)\n")
        f.write(f"  Ngày: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        f.write("1. CẤU HÌNH ĐÁNH GIÁ\n")
        f.write(f"   Gallery     : Dữ liệu đã Enroll vào CSDL (Real)\n")
        f.write(f"   Probe       : {total_queries} ảnh từ tập Altered-Easy\n")
        f.write(f"   Matching    : KD-Tree + Poincare Level 1 Pre-filtering\n\n")

        f.write("2. KẾT QUẢ RANKING (ĐỘ CHÍNH XÁC)\n")
        f.write(f"   Rank-1 Accuracy : {rank1_acc:.2f}%\n")
        f.write(f"   Rank-5 Accuracy : {rank5_acc:.2f}%\n\n")

        f.write("3. CHI TIẾT ĐƯỜNG CONG CMC\n")
        f.write(f"   {'Rank':<10} {'Accuracy (%)':<15}\n")
        f.write(f"   {'-'*25}\n")
        for k in range(1, MAX_RANK_TO_PLOT + 1):
            if k-1 < len(cmc_curve):
                f.write(f"   {k:<10} {cmc_curve[k-1]*100:<15.2f}\n")
    print(f"Đã lưu báo cáo: {report_path}")

if __name__ == "__main__":
    # 1. Kết nối DB
    DB_PATH = os.path.join(BASE_DIR, "fingerprint.db")
    db = FingerprintDatabase(DB_PATH)
    db.connect()

    # 2. Chuẩn bị Probe Set
    altered_files = glob.glob(os.path.join(DATASET_ALTERED_DIR, "*_CR.BMP"))
    probe_list = []
    
    for fp in altered_files:
        pid = parse_filename(os.path.basename(fp))
        if pid and pid not in ABNORMAL_IDS:
            probe_list.append(fp)

    random.seed(42)
    random.shuffle(probe_list)
    probe_list = probe_list[:NUM_PROBES]  # Lấy 100 ảnh để test

    if not probe_list:
        print("Lỗi: Không tìm thấy ảnh Probe!")
        exit()

    # 3. Chạy đánh giá
    t0 = time.time()
    ranks_found, errors = evaluate_retrieval(db, probe_list)
    t_total = time.time() - t0
    
    # 4. Xuất kết quả
    total_queries = len(probe_list) - errors
    if total_queries > 0:
        generate_cmc_report(ranks_found, total_queries)
        print(f"\nThời gian chạy: {t_total:.1f}s (Trung bình {t_total/total_queries:.1f}s / ảnh)")
    else:
        print("Đánh giá thất bại, không có truy vấn nào thành công.")
    
    db.close()
