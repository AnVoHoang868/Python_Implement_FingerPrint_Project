# 🔐 Hệ thống CSDL Lưu trữ và Tìm kiếm Ảnh Vân tay

> **Đồ án môn học:** Xây dựng hệ thống CSDL lưu trữ và tìm kiếm ảnh vân tay  
> **Ngôn ngữ:** Python 3.11  
> **Bộ dữ liệu:** SOCOFing (Sokoto Coventry Fingerprint Dataset)

---

## 📋 Mô tả Dự án

Hệ thống nhận dạng vân tay tự động (AFIS - Automated Fingerprint Identification System) được xây dựng hoàn toàn bằng **Python thuần túy**, sử dụng các thuật toán **Xử lý ảnh số (Digital Image Processing)** và **Nhận dạng mẫu (Pattern Recognition)** — không sử dụng AI/Deep Learning.

### Chức năng chính
- **Đầu vào:** 1 ảnh vân tay bất kỳ (BMP)
- **Đầu ra:** 5 ảnh vân tay giống nhất trong CSDL, xếp hạng theo điểm tương đồng giảm dần
- **Quy mô CSDL:** Hỗ trợ lưu trữ và tìm kiếm trên 3000+ mẫu vân tay

---

## 🏗️ Kiến trúc Hệ thống

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SƠ ĐỒ KHỐI HỆ THỐNG                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │ Ảnh đầu  │───>│  Tiền xử lý  │───>│  Trích xuất  │              │
│  │   vào    │    │ Enhancement  │    │  Đặc trưng   │              │
│  └──────────┘    └──────────────┘    └──────┬───────┘              │
│                                             │                       │
│                          ┌──────────────────┼──────────────────┐   │
│                          │                  │                  │   │
│                          ▼                  ▼                  │   │
│                  ┌──────────────┐   ┌──────────────┐          │   │
│                  │   Level 1    │   │   Level 2    │          │   │
│                  │ Core / Delta │   │  Minutiae    │          │   │
│                  │ Pattern Type │   │ (x, y, θ)   │          │   │
│                  └──────┬───────┘   └──────┬───────┘          │   │
│                         │                  │                  │   │
│                         ▼                  ▼                  │   │
│                  ┌─────────────────────────────────┐          │   │
│                  │     CSDL SQLite (fingerprint.db) │          │   │
│                  │  Users ──── Fingerprint_Templates│          │   │
│                  └──────────────┬──────────────────┘          │   │
│                                │                              │   │
│                                ▼                              │   │
│                  ┌─────────────────────────────────┐          │   │
│                  │     So khớp (KD-Tree Matching)   │          │   │
│                  │ 1. Lọc sơ bộ bằng Pattern Class  │          │   │
│                  │ 2. So khớp Minutiae (Score 0→1)  │          │   │
│                  └──────────────┬──────────────────┘          │   │
│                                │                              │   │
│                                ▼                              │   │
│                  ┌─────────────────────────────────┐          │   │
│                  │       Kết quả TOP 5              │          │   │
│                  │   (Xếp hạng theo Score giảm dần) │          │   │
│                  └─────────────────────────────────┘          │   │
│                                                               │   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 📂 Cấu trúc Dự án

```
Python_Implement_FingerPrint_Project/
│
├── 01_visualize_fingerprint.py     # Bước 1: Hiển thị & phân tích ảnh vân tay
├── 02_preprocessing.py             # Bước 2: Tiền xử lý (Normalization)
├── 03_enhancement.py               # Bước 3: Nâng cao chất lượng (CLAHE, Segmentation)
├── 04_orientation_field.py         # Bước 4: Ước lượng trường hướng vân (Orientation Field)
├── 04b_singular_points.py          # Bước 4B: Trích xuất Level 1 (Core, Delta, Pattern Class)
├── 05_frequency_estimation.py      # Bước 5: Ước lượng tần số vân (Ridge Frequency)
├── 06_gabor_filter.py              # Bước 6: Lọc Gabor (Gabor Filter Enhancement)
├── 07_binarize_thin.py             # Bước 7: Nhị phân hóa & Làm mảnh (Binarize + Thinning)
├── 08_minutiae_extraction.py       # Bước 8: Trích xuất điểm đặc trưng (Minutiae Extraction)
├── 09_matching.py                  # Bước 9: So khớp vân tay (Matching + KD-Tree + NumPy Fast)
├── 10_database_system.py           # Bước 10: Hệ thống CSDL SQLite (Enrollment + Identify)
├── 11_search_system.py             # Bước 11: Batch Enrollment & Tìm kiếm Top 5
├── 12_evaluation.py                # Bước 12: Đánh giá 1:1 (ROC, FAR/FRR, EER)
├── 13_evaluate_retrieval.py        # Bước 13: Đánh giá 1:N (CMC Curve, Rank-1/5 Accuracy)
│
├── DataFingerPrint/                # Bộ dữ liệu SOCOFing (không đưa lên Git)
│   └── fingerPrint/SOCOFing/
│       ├── Real/                   
│       └── Altered/                #   Ảnh biến dạng (Easy / Medium / Hard)
│
├── output/                         # Thư mục chứa biểu đồ và kết quả đánh giá
├── fingerprint.db                  # CSDL SQLite (tự sinh khi chạy Enrollment)
├── requirements.txt                # Danh sách thư viện cần cài đặt
├── .gitignore                      # Danh sách file/thư mục Git bỏ qua
└── README.md                       # File tài liệu này
```

---

## 🔬 Chi tiết Kỹ thuật

### Trích xuất Đặc trưng Đa cấp độ

| Cấp độ | Đặc trưng | Thuật toán | File |
|--------|-----------|------------|------|
| **Level 1** (Toàn cục) | Core, Delta, Pattern Class (Arch / Loop / Whorl) | Poincare Index trên Orientation Field | `04b_singular_points.py` |
| **Level 2** (Cục bộ) | Minutiae: Termination (Điểm kết thúc) & Bifurcation (Điểm rẽ nhánh) | Crossing Number trên ảnh Skeleton | `08_minutiae_extraction.py` |

### Thuật toán So khớp (Matching)

1. **Lọc sơ bộ (Pre-filtering):** Sử dụng Pattern Class từ Level 1 để thu hẹp phạm vi tìm kiếm trong CSDL. Chỉ so khớp các vân tay cùng chủng loại (VD: chỉ so Whorl với Whorl).
2. **So khớp Minutiae:** Với mỗi cặp vân tay:
   - Biến đổi tọa độ (Translation + Rotation) về cùng hệ quy chiếu
   - Xoay thêm ±5° để bù sai số
   - Tính Score = √(n² / (N₁ × N₂)), với n = số cặp Minutiae khớp nhau
3. **Tìm kiếm lân cận:** Sử dụng **KD-Tree** (`scipy.spatial.cKDTree`) để tìm kiếm điểm lân cận trong không gian 2D với độ phức tạp O(N log N).

### Cơ sở Dữ liệu (Database)

- **Engine:** SQLite (không cần cài đặt server)
- **Bảng `Users`:** Lưu thông tin người dùng (ID, tên, giới tính)
- **Bảng `Fingerprint_Templates`:** Lưu đặc trưng Level 1 (`pattern_class`, `core_x`, `core_y`, `delta_x`, `delta_y`) và Level 2 (`minutiae_data` dạng JSON, `minutiae_count`)
- **Quan hệ:** 1 User → N Templates (1 người có thể đăng ký nhiều ngón tay)

---

## 🚀 Hướng dẫn Cài đặt & Chạy

### Yêu cầu
- Python 3.11+
- Bộ dữ liệu SOCOFing (đặt trong thư mục `DataFingerPrint/`)

### Cài đặt

```bash
# Clone dự án
git clone https://github.com/AnVoHoang868/Python_Implement_FingerPrint_Project.git
cd Python_Implement_FingerPrint_Project

# Cài đặt thư viện
pip install -r requirements.txt
```

### Chạy hệ thống

```bash
# Bước 1: Nạp ảnh vào CSDL (Enrollment 3000 ảnh)
python 11_search_system.py

# Bước 2: Đánh giá 1:1 (ROC, FAR/FRR, EER)
python 12_evaluation.py

# Bước 3: Đánh giá 1:N (CMC Curve, Rank-1/5 Accuracy)
python 13_evaluate_retrieval.py
```

> **Lưu ý:** File `11_search_system.py` sẽ tự động thực hiện cả 2 việc: Enrollment (nạp dữ liệu) và Search (tìm kiếm thử 1 ảnh mẫu).

---

## 📊 Chỉ số Đánh giá

### Đánh giá Verification 1:1 (`12_evaluation.py`)

| Chỉ số | Ý nghĩa |
|--------|---------|
| **FAR** (False Acceptance Rate) | Tỷ lệ nhận nhầm người lạ thành người quen |
| **FRR** (False Rejection Rate) | Tỷ lệ từ chối nhầm người hợp lệ |
| **EER** (Equal Error Rate) | Điểm cân bằng FAR = FRR (càng thấp càng tốt) |
| **AUC** (Area Under ROC Curve) | Diện tích dưới đường cong ROC (càng gần 1.0 càng tốt) |

### Đánh giá Identification 1:N (`13_evaluate_retrieval.py`)

| Chỉ số | Ý nghĩa |
|--------|---------|
| **Rank-1 Accuracy** | Tỷ lệ tìm đúng người ở vị trí xếp hạng số 1 |
| **Rank-5 Accuracy** | Tỷ lệ người đúng lọt vào Top 5 kết quả |
| **CMC Curve** | Biểu đồ tích lũy tỷ lệ nhận diện từ Top 1 đến Top 10 |

---

## 📁 Bộ dữ liệu SOCOFing

- **Nguồn:** [Kaggle - SOCOFing Dataset](https://www.kaggle.com/datasets/ruizgara/socofing)
- **Quy mô:** 6.000 ảnh vân tay gốc (Real) + 55.000+ ảnh biến dạng (Altered)
- **Kích thước ảnh:** 96 × 103 pixel (BMP)
- **Cấu trúc tên file:** `{PersonID}__{Gender}_{Hand}_{Finger}_finger.BMP`
  - Ví dụ: `100__M_Left_index_finger.BMP` → Người 100, Nam, Ngón trỏ tay trái

---

## 🛠️ Công nghệ Sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| Xử lý ảnh | OpenCV, NumPy |
| Cơ sở dữ liệu | SQLite3 |
| Tìm kiếm lân cận | SciPy KD-Tree |
| Trực quan hóa | Matplotlib |
| Thanh tiến trình | tqdm |

---

## 📝 Tham khảo

1. Maltoni, D., Maio, D., Jain, A. K., & Prabhakar, S. (2009). *"Handbook of Fingerprint Recognition"* (2nd ed.), Springer.
2. Shehu, Y. I., Ruiz-Garcia, A., et al. (2018). *"SOCOFing: Sokoto Coventry Fingerprint Dataset"*, arXiv:1807.10609.
3. Hong, L., Wan, Y., & Jain, A. K. (1998). *"Fingerprint Image Enhancement: Algorithm and Performance Evaluation"*, IEEE TPAMI.
