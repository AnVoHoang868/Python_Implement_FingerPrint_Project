"""
Bước 11: Hệ Thống CSDL Thực Tế (Batch Enrollment) & Tìm kiếm Top 5
===================================================================
Mục tiêu:
  1. Enrollment: Quét thư mục chứa 500+ ảnh vân tay SOCOFing (Real).
                 Trích xuất đặc trưng và nạp toàn bộ vào CSDL (SQLite).
                 Tự động loại bỏ các ảnh không hợp lệ (sai kích thước).
  2. Query:      Dùng KD-Tree Matching (từ 09_matching.py) để tìm ra
                 5 ảnh giống nhất với một ảnh truy vấn đầu vào.
"""

import os
import glob
import time
import re
from tqdm import tqdm
import matplotlib.pyplot as plt
import cv2

# ============================================================================
# CẤU HÌNH ĐƯỜNG DẪN
# ============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Đường dẫn tới thư mục chứa bộ ảnh Real của SOCOFing
DATASET_REAL_DIR = os.path.join(BASE_DIR, "DataFingerPrint", "fingerPrint", "SOCOFing", "Real")
# Đường dẫn test với Altered
DATASET_ALTERED_DIR = os.path.join(BASE_DIR, "DataFingerPrint", "fingerPrint", "SOCOFing", "Altered")

DB_PATH = os.path.join(BASE_DIR, "fingerprint.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Giới hạn số lượng người dùng nạp vào CSDL (3000 ảnh = 300 người x 10 ngón)
MAX_PERSONS = 300

# Các ID người có kích thước ảnh không chuẩn trong SOCOFing (cần bỏ qua)
ABNORMAL_IDS = {"53", "226", "270", "297", "303", "349", "354", "361", "363", "376", "560", "585", "590"}

# ============================================================================
# IMPORT TỪ CÁC MODULE TRƯỚC
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

# ============================================================================
# PHA 1: BATCH ENROLLMENT
# ============================================================================
def parse_socofing_filename(filename):
    """
    Phân tích tên file SOCOFing để lấy thông tin.
    Ví dụ: 100__M_Left_index_finger.BMP
    Returns: person_id, gender, hand, finger
    """
    match = re.match(r"(\d+)__([M|F])_([A-Za-z]+)_([A-Za-z]+)_finger", filename)
    if match:
        return match.group(1), match.group(2), match.group(3), match.group(4)
    return None, None, None, None

def batch_enroll(db):
    """
    Quét ảnh Real, lọc ảnh lỗi, gom nhóm theo PersonID và nạp vào DB.
    """
    print(f"Đang quét thư mục: {DATASET_REAL_DIR}")
    if not os.path.exists(DATASET_REAL_DIR):
        print(f"Lỗi: Không tìm thấy thư mục dữ liệu {DATASET_REAL_DIR}!")
        return

    # Lấy danh sách tất cả file BMP
    all_files = glob.glob(os.path.join(DATASET_REAL_DIR, "*.BMP"))
    print(f"Tìm thấy tổng cộng {len(all_files)} file ảnh.")

    # Gom nhóm ảnh theo PersonID
    persons_data = {}
    for filepath in all_files:
        filename = os.path.basename(filepath)
        person_id, gender, hand, finger = parse_socofing_filename(filename)
        
        if person_id is None:
            continue

        # Bỏ qua các ID có ảnh khác kích thước
        if person_id in ABNORMAL_IDS:
            continue
            
        if person_id not in persons_data:
            persons_data[person_id] = {
                "name": f"Person_{person_id}",
                "gender": gender,
                "images": []
            }
        
        persons_data[person_id]["images"].append({
            "filepath": filepath,
            "filename": filename,
            "finger_index": f"{hand}_{finger}"
        })

    # Lấy MAX_PERSONS người đầu tiên
    valid_person_ids = sorted(list(persons_data.keys()))[:MAX_PERSONS]
    print(f"Sẽ tiến hành Enrollment cho {len(valid_person_ids)} người "
          f"({len(valid_person_ids) * 10} ảnh vân tay).")

    total_images = len(valid_person_ids) * 10
    success_count = 0

    with tqdm(total=total_images, desc="Enrolling", unit="img") as pbar:
        for p_id in valid_person_ids:
            person = persons_data[p_id]
            # Tạo User trong DB
            db_user_id = db.add_user(name=person["name"], role=f"Gender: {person['gender']}")

            for img_info in person["images"]:
                filepath = img_info["filepath"]
                
                # Trích xuất minutiae + Level 1 features
                minutiae, level1_features, _ = extract_features(filepath)
                
                if minutiae is not None and len(minutiae) > 0:
                    # Lưu vào DB (bao gồm cả Level 1)
                    db.enroll_fingerprint(
                        user_id=db_user_id,
                        minutiae=minutiae,
                        finger_index=img_info["finger_index"],
                        source_image=filepath,
                        level1_features=level1_features
                    )
                    success_count += 1
                
                pbar.update(1)

    print(f"\n[HOÀN TẤT] Đã nạp thành công {success_count}/{total_images} mẫu vân tay vào CSDL.")

# ============================================================================
# PHA 2: TÌM KIẾM TOP 5 (QUERY)
# ============================================================================
def search_top5(db, query_path):
    """
    Hệ thống lấy 1 ảnh đầu vào, trích xuất đặc trưng và so khớp với CSDL.
    Sử dụng Level 1 để lọc trước, sau đó dùng Numpy fast matching.
    Trả về Top 5 người có score cao nhất.
    """
    print(f"\n{'='*60}")
    print(f"BẮT ĐẦU TÌM KIẾM CHO ẢNH: {os.path.basename(query_path)}")
    print(f"{'='*60}")

    if not os.path.exists(query_path):
        print("Lỗi: Không tìm thấy ảnh truy vấn!")
        return None

    # 1. Trích xuất đặc trưng từ ảnh query (Level 1 + Level 2)
    print("1. Đang trích xuất đặc trưng từ ảnh truy vấn...")
    t0 = time.time()
    query_minutiae, query_level1, query_img = extract_features(query_path)
    t_ext = time.time() - t0

    if query_minutiae is None or len(query_minutiae) == 0:
        print("Lỗi: Không trích xuất được minutiae từ ảnh này.")
        return None
    
    query_pattern = query_level1["pattern_class"] if query_level1 else "Unknown"
    print(f"   -> Tìm thấy {len(query_minutiae)} minutiae (Mất {t_ext:.2f}s)")
    print(f"   -> Pattern Class (Level 1): {query_pattern}")
    if query_level1 and query_level1["cores"]:
        print(f"   -> Core: {query_level1['cores'][0]}")
    if query_level1 and query_level1["deltas"]:
        print(f"   -> Delta: {query_level1['deltas'][0]}")

    # 2. Lấy toàn bộ template từ CSDL
    all_templates = db.get_all_templates()
    if not all_templates:
        print("CSDL trống!")
        return None

    # 3. LỌC LEVEL 1: Chỉ giữ các template cùng pattern_class
    if query_pattern != "Unknown":
        filtered = [t for t in all_templates
                    if t["pattern_class"] == query_pattern
                    or t["pattern_class"] == "Unknown"]
        print(f"3. Level 1 Filter: {query_pattern} -> Còn {len(filtered)}/{len(all_templates)} templates")
    else:
        filtered = all_templates
        print(f"3. Level 1 Filter: Unknown -> Quét toàn bộ {len(filtered)} templates")

    # 4. So khớp Level 2 (Minutiae) trên tập đã lọc
    print(f"4. Đang so khớp Numpy Fast với {len(filtered)} templates...")
    t1 = time.time()
    
    results = []
    for tmpl in tqdm(filtered, desc="Matching", unit="tmpl", leave=False):
        score, _, _, _ = match_fingerprints_kdtree(query_minutiae, tmpl["minutiae"], alpha_range=5)
        
        results.append({
            "name": tmpl["name"],
            "finger_index": tmpl["finger_index"],
            "pattern_class": tmpl["pattern_class"],
            "score": score,
            "source_image": tmpl["source_image"],
            "minutiae_count": tmpl["minutiae_count"]
        })

    t_match = time.time() - t1
    print(f"   -> So khớp xong trong {t_match:.2f}s "
          f"(Tốc độ trung bình: {len(filtered)/max(t_match,0.001):.1f} templates/s)")

    # 3. Sắp xếp theo Score giảm dần và lấy Top 5
    results.sort(key=lambda x: x["score"], reverse=True)
    top5 = results[:5]

    print("\nKẾT QUẢ TOP 5:")
    print("-" * 65)
    print(f"{'Rank':<5} | {'Person Name':<15} | {'Finger':<15} | {'Score':<10} | {'Status'}")
    print("-" * 65)
    
    # In kết quả
    for i, res in enumerate(top5):
        # Chọn ngưỡng linh hoạt, VD 0.40 là match vì DB lớn có thể sai số nhỏ
        status = "★ MATCH" if res["score"] > 0.40 else "NON-MATCH"
        print(f"#{i+1:<4} | {res['name']:<15} | {res['finger_index']:<15} | {res['score']:.4f}     | {status}")
    print("-" * 65)

    return top5, query_img

# ============================================================================
# TRỰC QUAN HÓA KẾT QUẢ TOP 5
# ============================================================================
def visualize_top5(query_img, query_filename, top5_results):
    fig, axes = plt.subplots(1, 6, figsize=(18, 4))
    fig.suptitle(f"Fingerprint Retrieval Top 5 Results\nQuery: {query_filename}", fontsize=14, fontweight='bold')

    # Vẽ ảnh Query
    axes[0].imshow(query_img, cmap='gray')
    axes[0].set_title("QUERY IMAGE\n(Input)", color='blue')
    axes[0].axis('off')

    # Vẽ Top 5
    for i in range(5):
        ax = axes[i+1]
        if i < len(top5_results):
            res = top5_results[i]
            # Đọc ảnh kết quả
            res_img = cv2.imread(res["source_image"], cv2.IMREAD_GRAYSCALE)
            ax.imshow(res_img, cmap='gray')
            
            color = 'green' if res["score"] > 0.40 else 'red'
            title = f"Top {i+1}: {res['name']}\n{res['finger_index']}\nScore: {res['score']:.4f}"
            ax.set_title(title, color=color, fontsize=10)
        ax.axis('off')

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, f"11_search_result_{query_filename.replace('.BMP', '')}.png")
    plt.savefig(out_path, dpi=150)
    print(f"\nĐã lưu ảnh trực quan hóa kết quả tại: {out_path}")
    # plt.show() # Tắt để không chặn CLI

# ============================================================================
# CHƯƠNG TRÌNH CHÍNH
# ============================================================================
def main():
    print("=" * 70)
    print("  HỆ THỐNG CSDL 500 VÂN TAY & TÌM KIẾM KD-TREE")
    print("=" * 70)

    # Khởi tạo DB (XÓA CŨ TẠO MỚI)
    if os.path.exists(DB_PATH):
        print(f"[XÓA] Đang xóa file CSDL cũ tại: {DB_PATH}")
        # Workaround đóng kết nối trước nếu sqlite3 đang khóa file
        try:
            os.remove(DB_PATH)
        except PermissionError:
            print("Lỗi: Không thể xóa DB vì file đang mở. Sẽ dùng lại DB cũ.")

    db = FingerprintDatabase(DB_PATH)
    db.connect()
    
    # Tạo bảng
    db.create_tables()

    # Kiểm tra xem CSDL có rỗng không
    db.cursor.execute("SELECT COUNT(*) FROM Users")
    user_count = db.cursor.fetchone()[0]

    # Nếu DB rỗng, tiến hành Enrollment 500 ảnh
    if user_count == 0:
        print("\n>>> BẮT ĐẦU PHA ENROLLMENT <<<")
        batch_enroll(db)
    else:
        print(f"\n>>> BỎ QUA ENROLLMENT (CSDL đã có sẵn {user_count} Users) <<<")

    # =============================================
    # THỬ NGHIỆM TÌM KIẾM
    # =============================================
    print("\n>>> BẮT ĐẦU PHA TÌM KIẾM (QUERY) <<<")
    
    # KỊCH BẢN 1: Ảnh Real (Chắc chắn nằm trong DB, phải lên Top 1)
    # Lấy 1 ảnh ngẫu nhiên của người 100
    query1 = os.path.join(DATASET_REAL_DIR, "100__M_Left_index_finger.BMP")
    top5_1, q_img1 = search_top5(db, query1)
    if top5_1:
        visualize_top5(q_img1, "100__M_Left_index_finger.BMP", top5_1)

    # KỊCH BẢN 2: Ảnh Altered (Người 100 bị sửa đổi mức Hard)
    # Kỳ vọng: Vẫn tìm ra người 100 ở Top 5
    query2 = os.path.join(DATASET_ALTERED_DIR, "Altered-Hard", "100__M_Left_index_finger_CR.BMP")
    if os.path.exists(query2):
        top5_2, q_img2 = search_top5(db, query2)
        if top5_2:
            visualize_top5(q_img2, "100_Altered_Hard.BMP", top5_2)

    db.close()
    print("\n[HOÀN TẤT] Chương trình đã kết thúc thành công.")

if __name__ == "__main__":
    main()
