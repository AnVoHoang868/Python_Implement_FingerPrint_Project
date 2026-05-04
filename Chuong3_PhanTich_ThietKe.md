# Chương 3: Phân tích và Thiết kế Hệ thống

## 3.1 Phân tích Yêu cầu Bài toán

### 3.1.1 Mô tả Bài toán

Xây dựng hệ thống cơ sở dữ liệu lưu trữ và tìm kiếm ảnh vân tay với các yêu cầu cụ thể:

- **Đầu vào (Input):** Một ảnh vân tay bất kỳ (định dạng BMP, kích thước 96 × 103 pixel). Ảnh có thể thuộc về người đã có hoặc chưa có trong cơ sở dữ liệu.
- **Đầu ra (Output):** 5 ảnh vân tay giống nhất trong cơ sở dữ liệu, được xếp thứ tự giảm dần theo độ tương đồng nội dung.
- **Quy mô dữ liệu:** Tối thiểu 500 ảnh vân tay, các ảnh có cùng kích thước, vân tay thuộc nhiều ngón khác nhau của nhiều người khác nhau.

### 3.1.2 Bộ dữ liệu SOCOFing

Hệ thống sử dụng bộ dữ liệu **SOCOFing (Sokoto Coventry Fingerprint Dataset)** — một bộ dữ liệu chuẩn trong nghiên cứu sinh trắc học:

| Thuộc tính | Giá trị |
|------------|---------|
| Tổng số ảnh gốc (Real) | 6.000 ảnh |
| Số người | 600 người |
| Số ngón / người | 10 ngón (5 ngón mỗi tay) |
| Ảnh biến dạng (Altered) | ~55.000 ảnh (3 mức: Easy, Medium, Hard) |
| Kích thước ảnh | 96 × 103 pixel |
| Định dạng | BMP (Bitmap), ảnh xám 8-bit |
| Quy ước tên file | `{ID}__{Giới tính}_{Tay}_{Ngón}_finger.BMP` |

Ví dụ tên file: `100__M_Left_index_finger.BMP` → Người số 100, Nam, Ngón trỏ tay trái.

### 3.1.3 Hướng tiếp cận: Minutiae-based

Dự án triển khai phương pháp nhận dạng dựa trên **Minutiae (Điểm đặc trưng cục bộ)** — phương pháp truyền thống và phổ biến nhất trong các hệ thống AFIS (Automated Fingerprint Identification System) thực tế. Phương pháp này trích xuất các điểm kỳ dị trên đường vân (điểm kết thúc và điểm rẽ nhánh), sau đó so khớp dựa trên tọa độ và góc hướng của các điểm này.

---

## 3.2 Sơ đồ Khối Tổng quan

Hệ thống hoạt động theo 2 pha chính: **Pha Đăng ký (Enrollment)** và **Pha Tìm kiếm (Search)**.

### 3.2.1 Pha Đăng ký (Enrollment Phase)

Mục tiêu: Quét toàn bộ ảnh vân tay trong bộ dữ liệu, trích xuất đặc trưng và nạp vào cơ sở dữ liệu.

```
┌──────────┐    ┌────────────┐    ┌─────────────┐    ┌──────────────┐
│ Thư mục  │───>│ Tiền xử lý │───>│ Trích xuất  │───>│    Lưu vào   │
│ ảnh Real │    │ & Nâng cao │    │  Đặc trưng  │    │  CSDL SQLite │
│ (N ảnh)  │    │   ảnh      │    │ Level 1 + 2 │    │              │
└──────────┘    └────────────┘    └─────────────┘    └──────────────┘
```

Quy trình chi tiết cho mỗi ảnh:
1. Đọc ảnh BMP (ảnh xám)
2. Chuẩn hóa & Nâng cao chất lượng (CLAHE, Segmentation)
3. Ước lượng trường hướng vân (Orientation Field)
4. Trích xuất Level 1: Poincare Index → Core, Delta → Pattern Class
5. Ước lượng tần số vân → Lọc Gabor
6. Nhị phân hóa → Làm mảnh (Thinning)
7. Trích xuất Level 2: Crossing Number → Minutiae
8. Chuyển đổi Minutiae thành JSON → INSERT vào CSDL

### 3.2.2 Pha Tìm kiếm (Search Phase)

Mục tiêu: Nhận 1 ảnh đầu vào, trích xuất đặc trưng, so khớp với CSDL và trả về Top 5 kết quả.

```
┌──────────┐    ┌────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│ Ảnh truy │───>│ Trích xuất │───>│ Lọc sơ bộ   │───>│  So khớp     │───>│  Top 5   │
│   vấn    │    │ Level 1+2  │    │ Pattern Class│    │ KD-Tree      │    │ kết quả  │
└──────────┘    └────────────┘    └──────────────┘    └──────────────┘    └──────────┘
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │  CSDL SQLite  │
                                  │ (Gallery)     │
                                  └──────────────┘
```

Quy trình chi tiết:
1. Trích xuất đặc trưng từ ảnh truy vấn (cùng pipeline như Enrollment)
2. **Lọc sơ bộ (Pre-filtering):** Dùng Pattern Class (Level 1) để chỉ lấy các template cùng chủng loại vân tay từ CSDL
3. **So khớp (Matching):** Tính điểm tương đồng (Similarity Score) giữa Minutiae của ảnh truy vấn và từng template đã lọc
4. **Xếp hạng (Ranking):** Sắp xếp điểm giảm dần, trả về Top 5 kết quả

---

## 3.3 Thiết kế Module Tiền xử lý & Nâng cao Ảnh

Module tiền xử lý có nhiệm vụ biến đổi ảnh vân tay thô thành ảnh sạch, rõ nét, sẵn sàng cho bước trích xuất đặc trưng. Pipeline gồm các bước tuần tự:

```
Ảnh gốc (Grayscale)
    │
    ▼
┌───────────────────────────────────────────────┐
│ Bước 1: Chuẩn hóa (Normalization)             │
│   • Đưa ảnh về cùng khoảng giá trị [0, 255]  │
│   • Loại bỏ sự khác biệt do điều kiện quét   │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│ Bước 2: Nâng cao tương phản (CLAHE)           │
│   • Contrast Limited Adaptive Histogram       │
│     Equalization                              │
│   • Tham số: clip_limit = 2.5, grid = (8, 8) │
└───────────────────┬───────────────────────────┘
                    ▼
┌───────────────────────────────────────────────┐
│ Bước 3: Phân đoạn (Segmentation)              │
│   • Chia ảnh thành block 16 × 16 pixel        │
│   • Tính phương sai (Variance) mỗi block      │
│   • Var > 0.005 → Vùng vân tay (Foreground)   │
│   • Var ≤ 0.005 → Nền (Background)            │
│   • Output: Mặt nạ nhị phân (Mask)            │
└───────────────────┬───────────────────────────┘
                    ▼
    Ảnh đã nâng cao + Mask vùng vân
```

**Ý nghĩa của Mask:** Mask là một ma trận nhị phân cùng kích thước ảnh, đánh dấu pixel nào thuộc vùng vân tay (giá trị 1) và pixel nào là nền trắng (giá trị 0). Mask được sử dụng xuyên suốt các bước tiếp theo để đảm bảo thuật toán chỉ xử lý trên vùng có vân tay thực sự.

---

## 3.4 Thiết kế Module Trích xuất Đặc trưng

Hệ thống trích xuất đặc trưng ở **2 cấp độ**, phù hợp với tiêu chuẩn AFIS quốc tế:

### 3.4.1 Trích xuất Trường hướng vân (Orientation Field)

Trường hướng vân là bước trung gian bắt buộc, cung cấp dữ liệu đầu vào cho cả Level 1 (Poincare Index) lẫn bước lọc Gabor.

- **Thuật toán:** Gradient-based Estimation
- **Nguyên lý:** Tại mỗi block 16 × 16 pixel, tính gradient theo 2 trục (Gx, Gy) bằng bộ lọc Sobel, sau đó sử dụng công thức:

$$\theta(i,j) = \frac{1}{2} \arctan\left(\frac{2 \sum G_x \cdot G_y}{\sum(G_x^2 - G_y^2)}\right)$$

- **Output:** Ma trận góc hướng (radian) tại mỗi pixel, cho biết hướng cục bộ của các đường vân tại vị trí đó.

### 3.4.2 Trích xuất Level 1 — Đặc trưng Toàn cục (Singular Points & Pattern Classification)

| Thành phần | Chi tiết |
|------------|----------|
| **Thuật toán** | Poincare Index |
| **Đầu vào** | Ma trận hướng vân (Orientation Field) + Mask |
| **Đầu ra** | Tọa độ Core (Tâm), tọa độ Delta (Tam giác), Pattern Class |

**Nguyên lý Poincare Index:**
Tại mỗi block (i, j) trên bản đồ hướng, lấy 8 block lân cận theo chiều kim đồng hồ, tính tổng chênh lệch góc giữa các block liên tiếp. Kết quả:
- Poincare Index ≈ +π (180°) → Đây là điểm **Core** (Tâm vân)
- Poincare Index ≈ −π (−180°) → Đây là điểm **Delta** (Tam giác vân)
- Poincare Index ≈ 0 → Pixel bình thường

**Phân loại Pattern Class (Hệ thống Henry):**

| Pattern | Số Core | Số Delta | Điều kiện bổ sung |
|---------|---------|----------|-------------------|
| Arch | 0 | 0 | Không có Core & Delta |
| Left Loop | 1 | 1 | Delta nằm bên phải Core |
| Right Loop | 1 | 1 | Delta nằm bên trái Core |
| Whorl | ≥ 2 | ≥ 2 | Nhiều Core và Delta |
| Unknown | Khác | Khác | Không đủ điều kiện phân loại |

**Tham số đã tối ưu cho bộ dữ liệu SOCOFing:**
- `block_size = 8` pixel (giảm từ 16 do ảnh SOCOFing chỉ 96 × 103 pixel)
- `core_threshold = 0.7` (70% giá trị π)
- `margin = 8 pixel` (1 block từ biên)

### 3.4.3 Nâng cao Ảnh bằng Bộ lọc Gabor

Trước khi trích xuất Minutiae, ảnh vân tay được lọc qua bộ lọc Gabor để nâng cao cấu trúc đường vân và loại bỏ nhiễu:

- **Đầu vào:** Ảnh đã nâng cao, Orientation Field, Frequency Map, Mask
- **Tham số:** `kx = 0.5`, `ky = 0.5`, `angle_inc = 3°`
- **Đầu ra:** Ảnh vân tay với các đường vân sắc nét, liên tục

### 3.4.4 Nhị phân hóa & Làm mảnh (Binarization & Thinning)

| Bước | Thuật toán | Mô tả |
|------|-----------|-------|
| Nhị phân hóa | Otsu Thresholding | Chuyển ảnh xám → ảnh đen trắng (0/1) |
| Làm mảnh | Zhang-Suen Thinning | Thu nhỏ đường vân từ nhiều pixel → đúng 1 pixel chiều rộng (Skeleton) |

Kết quả sau bước này là **ảnh Skeleton** — nền tảng để áp dụng thuật toán Crossing Number ở bước tiếp theo.

### 3.4.5 Trích xuất Level 2 — Minutiae (Điểm đặc trưng cục bộ)

| Thành phần | Chi tiết |
|------------|----------|
| **Thuật toán** | Crossing Number (CN) |
| **Đầu vào** | Ảnh Skeleton + Orientation Field + Mask |
| **Đầu ra** | Mảng Minutiae: `[x, y, type, angle]` |

**Nguyên lý Crossing Number:**
Với mỗi pixel trắng P trên ảnh Skeleton, đếm số lần chuyển đổi 0→1 trên vòng tròn 8 pixel lân cận:

$$CN(P) = \frac{1}{2} \sum_{i=1}^{8} |P_i - P_{i+1}|$$

- **CN = 1** → Điểm **Termination** (Kết thúc đường vân) — `type = 1`
- **CN = 3** → Điểm **Bifurcation** (Rẽ nhánh đường vân) — `type = 3`

**Hậu xử lý (Loại bỏ Minutiae giả):**
- Loại bỏ Minutiae nằm ngoài vùng Mask (nền)
- Loại bỏ Minutiae nằm quá sát biên ảnh
- Loại bỏ cặp Minutiae cách nhau dưới 10 pixel (nhiễu do đường vân bị đứt đoạn)

**Biểu diễn mỗi Minutiae:**

| Trường | Kiểu dữ liệu | Ý nghĩa |
|--------|-------------|---------|
| `x` | float | Tọa độ cột (pixel) |
| `y` | float | Tọa độ hàng (pixel) |
| `type` | int | Loại: 1 = Termination, 3 = Bifurcation |
| `angle` | float | Góc hướng tại vị trí đó (radian) |

---

## 3.5 Thiết kế Module So khớp (Matching Engine)

Module so khớp nhận 2 tập Minutiae và trả về điểm tương đồng (Similarity Score) trong khoảng [0, 1].

### 3.5.1 Thuật toán So khớp Minutiae

Thuật toán gồm 4 bước:

**Bước 1 — Biến đổi tọa độ (Transform):**
Chọn 1 Minutia làm điểm gốc tọa độ (Reference Point). Tịnh tiến và xoay tất cả Minutiae còn lại về hệ tọa độ tương đối:

$$x' = (x - x_{ref}) \cos\theta_{ref} + (y - y_{ref}) \sin\theta_{ref}$$
$$y' = -(x - x_{ref}) \sin\theta_{ref} + (y - y_{ref}) \cos\theta_{ref}$$
$$\theta' = \theta - \theta_{ref}$$

Mục đích: Loại bỏ sự khác biệt về vị trí và góc xoay giữa 2 lần quét vân tay khác nhau.

**Bước 2 — Xoay bổ sung (Transform2):**
Thử xoay thêm ±5° (tổng cộng 11 góc) để bù sai số nhỏ trong Orientation Field.

**Bước 3 — Tính điểm (Score):**
Đếm số cặp Minutiae "khớp nhau" thỏa mãn đồng thời 2 điều kiện:
- Khoảng cách Euclid < 15 pixel
- Chênh lệch góc < 14°

Công thức Similarity Score:
$$S = \sqrt{\frac{n^2}{N_1 \times N_2}}$$

Trong đó: n = số cặp khớp, N₁ và N₂ = tổng số Minutiae của mỗi ảnh.

**Bước 4 — Brute-force:**
Thử TẤT CẢ cặp (Minutia_i từ ảnh 1, Minutia_j từ ảnh 2) làm Reference Point, giữ lại cặp cho Score cao nhất.

### 3.5.2 Tìm kiếm lân cận bằng KD-Tree

Ở Bước 3, thay vì duyệt vòng lặp lồng nhau O(N²) để tìm cặp Minutiae gần nhau, hệ thống sử dụng cấu trúc dữ liệu **KD-Tree** (K-Dimensional Tree) từ thư viện `scipy.spatial.cKDTree`:

- **Xây dựng cây:** Chèn tất cả tọa độ (x, y) của tập Minutiae thứ 2 vào KD-Tree
- **Truy vấn:** Với mỗi Minutiae trong tập 1, sử dụng hàm `query_ball_point(radius=15)` để lấy ngay danh sách các điểm nằm trong bán kính 15 pixel
- **Độ phức tạp:** O(N log N) cho việc xây dựng cây, O(log N) cho mỗi truy vấn

### 3.5.3 Chiến lược Lọc sơ bộ bằng Level 1 (Pre-filtering)

Trước khi thực hiện so khớp Minutiae (tốn thời gian), hệ thống sử dụng Pattern Class từ Level 1 để thu hẹp tập ứng viên:

```
Ảnh truy vấn: Pattern Class = "Whorl"
    │
    ▼  SQL: WHERE pattern_class = 'Whorl' OR pattern_class = 'Unknown'
    │
CSDL (3000 templates) ──── Lọc ────> ~800 templates (chỉ nhóm Whorl)
    │
    ▼  So khớp Minutiae chỉ trên 800 templates
    │
    Top 5 kết quả
```

Hiệu quả: Giảm số lượng phép so khớp xuống còn khoảng 30–40% so với quét toàn bộ CSDL, tăng tốc độ tìm kiếm đáng kể.

---

## 3.6 Thiết kế Cơ sở Dữ liệu

### 3.6.1 Lựa chọn Công nghệ

Hệ thống sử dụng **SQLite** — hệ quản trị CSDL quan hệ nhúng (embedded), không cần cài đặt server. Toàn bộ dữ liệu được lưu trong một file duy nhất `fingerprint.db`.

### 3.6.2 Sơ đồ Quan hệ Thực thể (ER Diagram)

```
┌──────────────────────────┐          ┌──────────────────────────────────────┐
│         Users            │          │       Fingerprint_Templates          │
├──────────────────────────┤          ├──────────────────────────────────────┤
│ PK  user_id     INTEGER  │──── 1:N ─│ PK  template_id   INTEGER           │
│     name        TEXT     │          │ FK  user_id        INTEGER           │
│     role        TEXT     │          │     finger_index   TEXT              │
│     created_at  TIMESTAMP│          │     pattern_class  TEXT    ← Level 1 │
└──────────────────────────┘          │     core_x         INTEGER ← Level 1 │
                                      │     core_y         INTEGER ← Level 1 │
                                      │     delta_x        INTEGER ← Level 1 │
                                      │     delta_y        INTEGER ← Level 1 │
                                      │     minutiae_data  TEXT    ← Level 2 │
                                      │     minutiae_count INTEGER           │
                                      │     source_image   TEXT              │
                                      │     created_at     TIMESTAMP         │
                                      └──────────────────────────────────────┘
```

**Quan hệ:** Một người (Users) có thể đăng ký nhiều ngón tay (Fingerprint_Templates) — quan hệ **1:N** với ràng buộc FOREIGN KEY và ON DELETE CASCADE.

### 3.6.3 Cách lưu trữ Minutiae trong CSDL

Mỗi template lưu trữ toàn bộ Minutiae dưới dạng **chuỗi JSON** trong cột `minutiae_data`:

```json
[
  {"x": 75.0, "y": 59.0, "type": 3, "angle": 1.173},
  {"x": 42.0, "y": 64.0, "type": 1, "angle": 1.797},
  {"x": 29.0, "y": 69.0, "type": 3, "angle": 1.788}
]
```

Khi cần so khớp, hệ thống thực hiện 1 lệnh SELECT duy nhất để lấy toàn bộ template, sau đó parse JSON thành mảng NumPy để tính toán.

### 3.6.4 Quy ước giá trị đặc biệt

- Các trường `core_x`, `core_y`, `delta_x`, `delta_y` nhận giá trị **-1** khi thuật toán Poincare không phát hiện được điểm kỳ dị tương ứng (ví dụ: vân tay loại Arch không có Core và Delta).
- Trường `pattern_class` nhận giá trị **"Unknown"** khi ảnh bị nhiễu quá nặng, không đủ điều kiện phân loại.

---

## 3.7 Thiết kế Module Tìm kiếm Top 5

### 3.7.1 Luồng xử lý tổng thể

```
        Ảnh truy vấn
             │
             ▼
    ┌─────────────────┐
    │ extract_features │  ← Cùng pipeline với Enrollment
    │  (Level 1 + 2)  │
    └────────┬────────┘
             │
     ┌───────┴───────┐
     │               │
     ▼               ▼
 Level 1          Level 2
 pattern_class    minutiae[]
     │               │
     ▼               │
 ┌───────────┐       │
 │  Lọc DB   │       │
 │ theo class│       │
 └─────┬─────┘       │
       │              │
       ▼              ▼
 Templates đã lọc ───> So khớp KD-Tree
                           │
                           ▼
                    Sắp xếp theo Score ↓
                           │
                           ▼
                      ┌─────────┐
                      │  TOP 5  │
                      └─────────┘
```

### 3.7.2 Đầu ra của Hệ thống

Với mỗi kết quả trong Top 5, hệ thống trả về:

| Trường | Mô tả |
|--------|-------|
| `name` | Tên người dùng (VD: Person_100) |
| `finger_index` | Ngón tay (VD: Left_index) |
| `pattern_class` | Phân loại vân tay (VD: Whorl) |
| `score` | Điểm tương đồng (0.0 → 1.0) |
| `source_image` | Đường dẫn ảnh gốc trong CSDL |
| `minutiae_count` | Số lượng Minutiae của template |

### 3.7.3 Ngưỡng phân loại (Classification Threshold)

Hệ thống sử dụng ngưỡng **Score > 0.40** để đánh dấu kết quả là "MATCH" (Khớp). Ngưỡng này được chọn thấp hơn giá trị lý thuyết 0.48 (từ tham khảo FVC) để phù hợp với đặc điểm ảnh SOCOFing có kích thước nhỏ và số lượng Minutiae trên mỗi ảnh hạn chế (trung bình 4–8 điểm).
