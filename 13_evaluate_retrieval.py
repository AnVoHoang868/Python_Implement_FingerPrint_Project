"""
Bước 13: Đánh giá Hệ thống Nhận dạng (Identification 1:N)
=========================================================
Mục tiêu:
  1. Lấy N ảnh truy vấn (Probe) bị biến dạng từ Altered-Easy (50 người đầu).
  2. Với mỗi ảnh, tìm kiếm trong cơ sở dữ liệu (Gallery) để lấy danh sách xếp hạng.
  3. Tính toán Top-1 / Top-5 Accuracy, Macro Precision, Macro Recall.
  4. Xuất báo cáo đánh giá ra JSON, CSV, TXT.

Workflow: Minutiae + KD-Tree + SQLite (Level 1 Pre-filtering)
"""

import os
import sys
import re
import glob
import json
import csv
import time
import numpy as np
from tqdm import tqdm
from sklearn.metrics import precision_score, recall_score, accuracy_score

# Fix encoding cho Windows console (tiếng Việt)
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CẤU HÌNH
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_ALTERED_DIR = os.path.join(BASE_DIR, "DataFingerPrint", "fingerPrint", "SOCOFing", "Altered", "Altered-Easy")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Giới hạn đánh giá trên 5 người đầu tiên (để test tốc độ)
MAX_USER_ID_EVAL = 5

# ============================================================================
# IMPORT MODULE (Minutiae workflow)
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
def evaluate_system():
    t_start = time.time()

    # 1. Kết nối DB SQLite (Gallery)
    DB_PATH = os.path.join(BASE_DIR, "fingerprint.db")
    db = FingerprintDatabase(DB_PATH)
    db.connect()

    all_templates = db.get_all_templates()
    if not all_templates:
        print("Lỗi: Cơ sở dữ liệu trống! Hãy chạy 11_search_system.py để enroll trước.")
        db.close()
        return

    # Map template_id → person_id (trong CSDL name lưu dạng 'Person_100')
    db_person_ids = {}
    for t in all_templates:
        pid = t["name"].split("_")[1]
        db_person_ids[t["template_id"]] = pid

    # 2. Chuẩn bị Probe Set: lấy tất cả ảnh của 5 người đầu (CR, Obl, Zcut)
    all_altered_files = sorted(glob.glob(os.path.join(DATASET_ALTERED_DIR, "*.BMP")))
    test_files = []
    for fp in all_altered_files:
        parts = os.path.basename(fp).split('__')
        if len(parts) >= 2:
            try:
                if 1 <= int(parts[0]) <= MAX_USER_ID_EVAL:
                    test_files.append(fp)
            except ValueError:
                pass

    print(f"Bắt đầu đánh giá trên {len(test_files)} ảnh (user_id 1-{MAX_USER_ID_EVAL}) từ Altered-Easy...")
    print(f"Gallery: {len(all_templates)} templates trong CSDL SQLite")

    y_true = []
    y_pred_top1 = []
    correct_top5_count = 0
    total_queries = 0
    results_details = []

    for i, file_path in enumerate(tqdm(test_files, desc="Retrieval Testing")):
        filename = os.path.basename(file_path)
        true_id = filename.split('__')[0]

        try:
            # 1. Trích xuất đặc trưng Minutiae + Level 1
            query_minutiae, query_level1, _ = extract_features(file_path)

            if query_minutiae is None or len(query_minutiae) == 0:
                y_true.append(true_id)
                y_pred_top1.append("Unknown")
                total_queries += 1
                results_details.append({
                    "file_name": filename,
                    "true_id": true_id,
                    "pred_top1_id": "Unknown",
                    "top_5_ids": [],
                    "is_top1_correct": False,
                    "is_top5_correct": False
                })
                continue

            # 2. Level 1 Pre-filtering (lọc theo Pattern Class)
            query_pattern = query_level1["pattern_class"] if query_level1 else "Unknown"
            if query_pattern != "Unknown":
                filtered = [t for t in all_templates if t["pattern_class"] in (query_pattern, "Unknown")]
            else:
                filtered = all_templates

            # 3. So khớp Level 2 (Minutiae KD-Tree) trên tập đã lọc
            results = []
            for tmpl in filtered:
                score, _, _, _ = match_fingerprints_kdtree(query_minutiae, tmpl["minutiae"], alpha_range=5)
                results.append({
                    "template_id": tmpl["template_id"],
                    "person_id": db_person_ids[tmpl["template_id"]],
                    "score": score
                })

            # 4. Sắp xếp theo Score giảm dần, lấy Top 5
            results.sort(key=lambda x: x["score"], reverse=True)
            top_k_results = [r["person_id"] for r in results[:5]]

            if not top_k_results:
                y_true.append(true_id)
                y_pred_top1.append("Unknown")
                total_queries += 1
                results_details.append({
                    "file_name": filename,
                    "true_id": true_id,
                    "pred_top1_id": "Unknown",
                    "top_5_ids": [],
                    "is_top1_correct": False,
                    "is_top5_correct": False
                })
                continue

            pred_top1_id = top_k_results[0]
            y_true.append(true_id)
            y_pred_top1.append(pred_top1_id)

            is_top1_correct = (str(pred_top1_id) == str(true_id))
            is_top5_correct = (str(true_id) in [str(res) for res in top_k_results])

            if is_top5_correct:
                correct_top5_count += 1

            total_queries += 1

            results_details.append({
                "file_name": filename,
                "true_id": true_id,
                "pred_top1_id": pred_top1_id,
                "top_5_ids": top_k_results,
                "is_top1_correct": is_top1_correct,
                "is_top5_correct": is_top5_correct
            })

        except Exception as e:
            y_true.append(true_id)
            y_pred_top1.append("Unknown")
            total_queries += 1
            results_details.append({
                "file_name": filename,
                "true_id": true_id,
                "pred_top1_id": "Unknown",
                "top_5_ids": [],
                "is_top1_correct": False,
                "is_top5_correct": False
            })

    # Đóng kết nối database
    db.close()

    # 5. Tính toán các chỉ số
    elapsed = time.time() - t_start
    eval_labels = sorted(set(y_true))
    acc_top1 = accuracy_score(y_true, y_pred_top1)
    precision = precision_score(y_true, y_pred_top1, average='macro', labels=eval_labels, zero_division=0)
    recall = recall_score(y_true, y_pred_top1, average='macro', labels=eval_labels, zero_division=0)
    acc_top5 = correct_top5_count / total_queries if total_queries > 0 else 0
    avg_time = elapsed / total_queries if total_queries > 0 else 0

    metrics = {
        "Total_Images": total_queries,
        "Top-1_Accuracy": round(acc_top1, 4),
        "Top-5_Accuracy": round(acc_top5, 4),
        "Macro_Precision": round(precision, 4),
        "Macro_Recall": round(recall, 4),
        "Total_Time_Seconds": round(elapsed, 2),
        "Avg_Time_Per_Query_ms": round(avg_time * 1000, 2)
    }

    print("\n=== KẾT QUẢ ĐÁNH GIÁ HỆ THỐNG (Minutiae + KD-Tree) ===")
    print(f"Tổng số ảnh đánh giá: {total_queries}")
    print(f"Top-1 Accuracy : {acc_top1:.4f}")
    print(f"Top-5 Accuracy : {acc_top5:.4f}")
    print(f"Macro Precision: {precision:.4f}")
    print(f"Macro Recall   : {recall:.4f}")
    print(f"Tổng thời gian : {elapsed:.1f}s")
    print(f"TB mỗi query   : {avg_time*1000:.1f}ms")

    # --- LƯU KẾT QUẢ ---
    
    # 1. Lưu dưới dạng JSON
    json_path = os.path.join(OUTPUT_DIR, "13_evaluation_results.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            "metrics": metrics,
            "details": results_details
        }, f, indent=4, ensure_ascii=False)
        
    # 2. Lưu dưới dạng CSV
    csv_path = os.path.join(OUTPUT_DIR, "13_evaluation_results.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        for k, v in metrics.items():
            writer.writerow([k, v])
        
        writer.writerow([])
        writer.writerow(["file_name", "true_id", "pred_top1_id", "top_5_ids", "is_top1_correct", "is_top5_correct"])
        for item in results_details:
            writer.writerow([
                item["file_name"], 
                item["true_id"], 
                item["pred_top1_id"], 
                ", ".join(map(str, item["top_5_ids"])), 
                item["is_top1_correct"], 
                item["is_top5_correct"]
            ])
            
    # 3. Lưu dưới dạng TXT
    txt_path = os.path.join(OUTPUT_DIR, "13_evaluation_results.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=== KẾT QUẢ ĐÁNH GIÁ HỆ THỐNG (Minutiae + KD-Tree) ===\n")
        f.write(f"Tổng số ảnh đánh giá: {total_queries}\n")
        f.write(f"Top-1 Accuracy : {acc_top1:.4f}\n")
        f.write(f"Top-5 Accuracy : {acc_top5:.4f}\n")
        f.write(f"Macro Precision: {precision:.4f}\n")
        f.write(f"Macro Recall   : {recall:.4f}\n")
        f.write(f"Tổng thời gian : {elapsed:.1f}s\n")
        f.write(f"TB mỗi query   : {avg_time*1000:.1f}ms\n")
        f.write("\n=== CHI TIẾT ===\n")
        for item in results_details:
            top_5_str = ", ".join(map(str, item['top_5_ids']))
            f.write(f"File: {item['file_name']} | True ID: {item['true_id']} | Top 1: {item['pred_top1_id']} | Top 5: [{top_5_str}] | Top-1 Đúng: {item['is_top1_correct']} | Top-5 Đúng: {item['is_top5_correct']}\n")

    print(f"\nĐã lưu kết quả đánh giá vào thư mục: {OUTPUT_DIR}/")
    print(f"  -> 13_evaluation_results.json")
    print(f"  -> 13_evaluation_results.csv")
    print(f"  -> 13_evaluation_results.txt")


if __name__ == "__main__":
    evaluate_system()