# Chương 2: Cơ sở Lý thuyết (Phần 2)

## 2.8 Trích xuất Minutiae (Thuật toán Crossing Number)

### 2.8.1 Khái niệm Minutiae
Trong sinh trắc học vân tay, Minutiae là các điểm đặc trưng cục bộ (Local features) xuất hiện tại các vị trí bất thường trên đường vân. Mặc dù có nhiều loại Minutiae khác nhau, hai loại cơ bản và được sử dụng rộng rãi nhất trong các hệ thống AFIS là:
1. **Termination (Điểm kết thúc):** Điểm mà tại đó một đường vân đột ngột kết thúc.
2. **Bifurcation (Điểm rẽ nhánh):** Điểm mà tại đó một đường vân tách ra thành hai nhánh.

### 2.8.2 Thuật toán Crossing Number (CN)
Crossing Number (Số lần cắt) là phương pháp phổ biến nhất để phát hiện Minutiae trên ảnh vân tay đã được làm mảnh (Skeleton image), nơi các đường vân có độ dày chính xác bằng 1 pixel.

**Nguyên lý:**
Tại mỗi pixel đen (pixel thuộc đường vân, giả sử giá trị là 1) trên ảnh Skeleton, thuật toán sẽ kiểm tra 8 pixel lân cận của nó theo chiều kim đồng hồ (hoặc ngược chiều kim đồng hồ). Gọi pixel trung tâm là $P$ và 8 pixel lân cận là $P_1, P_2, ..., P_8$.

Công thức tính Crossing Number:
$$CN(P) = \frac{1}{2} \sum_{i=1}^{8} |P_i - P_{i+1}|$$
*(với quy ước $P_9 = P_1$ để khép kín vòng lặp)*

Ý nghĩa công thức: $CN(P)$ đếm số lần có sự thay đổi giá trị (từ 0 sang 1 hoặc từ 1 sang 0) khi duyệt vòng quanh pixel $P$. Nói cách khác, nó đếm số lượng đường vân kết nối trực tiếp với điểm $P$.

**Phân loại Minutiae dựa trên CN:**
- **$CN = 1$:** Điểm Termination. Đường vân chỉ có 1 nhánh đi ra từ $P$, nghĩa là nó kết thúc tại $P$.
- **$CN = 2$:** Điểm bình thường trên đường vân. Đường vân đi qua $P$ (1 nhánh đi vào, 1 nhánh đi ra).
- **$CN = 3$:** Điểm Bifurcation. Có 3 nhánh đường vân giao nhau tại $P$.
- **$CN > 3$:** Điểm giao nhau phức tạp (Crossings), thường là do nhiễu và ít được sử dụng trực tiếp làm đặc trưng.

### 2.8.3 Lọc Minutiae giả (False Minutiae Removal)
Sau bước tính CN, hệ thống thường phát hiện ra rất nhiều Minutiae. Tuy nhiên, một phần lớn trong số đó là Minutiae giả sinh ra do nhiễu trong quá trình tiền xử lý (đứt đoạn, mọc gai, cầu nối). Do đó, một bước hậu xử lý là bắt buộc:
1. **Xóa Minutiae ở biên:** Loại bỏ các Minutiae nằm quá sát mép của vùng có vân tay (ROI) vì đây thường là điểm kết thúc giả do ảnh bị cắt.
2. **Xóa cặp Minutiae gần nhau:** Nếu hai Minutiae (bất kể loại) nằm quá gần nhau (khoảng cách Euclid nhỏ hơn một ngưỡng nhất định, ví dụ 10 pixel), chúng có khả năng cao là nhiễu (như đường vân bị đứt tạo ra 2 điểm kết thúc gần nhau, hoặc gai tạo ra 1 rẽ nhánh và 1 kết thúc gần nhau) và sẽ bị loại bỏ.

---

## 2.9 Thuật toán So khớp Minutiae (Minutiae Matching)

So khớp Minutiae là quá trình tính toán mức độ tương đồng giữa hai tập hợp Minutiae: tập truy vấn (Query) và tập mẫu trong cơ sở dữ liệu (Template). Khó khăn lớn nhất là hai ảnh vân tay quét vào các thời điểm khác nhau sẽ bị lệch về vị trí (Translation) và góc xoay (Rotation).

### 2.9.1 Biến đổi tọa độ (Alignment / Transformation)
Để có thể so sánh, hai tập Minutiae phải được đưa về cùng một hệ quy chiếu. Phương pháp phổ biến là chọn một cặp Minutiae (một từ Query, một từ Template) làm điểm gốc (Reference Point) và dời/xoay tất cả các điểm khác theo điểm gốc này.

Giả sử điểm gốc có tọa độ $(x_{ref}, y_{ref})$ và góc hướng $\theta_{ref}$. Phép biến đổi cho bất kỳ điểm $(x, y, \theta)$ nào trong tập hợp sẽ là:

$$ \begin{bmatrix} x' \\ y' \end{bmatrix} = \begin{bmatrix} \cos(\theta_{ref}) & \sin(\theta_{ref}) \\ -\sin(\theta_{ref}) & \cos(\theta_{ref}) \end{bmatrix} \begin{bmatrix} x - x_{ref} \\ y - y_{ref} \end{bmatrix} $$

Và góc mới: $\theta' = \theta - \theta_{ref}$

Khi cả hai tập Minutiae đều được biến đổi theo điểm gốc tương ứng của chúng, chúng sẽ nằm trên cùng một hệ tọa độ tương đối, triệt tiêu sự sai lệch về vị trí và góc xoay khi lấy vân tay.

### 2.9.2 Đánh giá sự trùng khớp (Matching Criteria)
Sau khi đồng bộ tọa độ, hai Minutia (một từ Query, một từ Template) được coi là trùng khớp (Mated pair) nếu chúng thỏa mãn đồng thời hai điều kiện (Bounding Box):
1. Khoảng cách không gian (Spatial Distance) nhỏ hơn một ngưỡng $r_0$.
2. Độ lệch góc (Direction Difference) nhỏ hơn một ngưỡng $\theta_0$.

$$ SD(m_q, m_t) = \sqrt{(x_q - x_t)^2 + (y_q - y_t)^2} \le r_0 $$
$$ DD(m_q, m_t) = \min(|\theta_q - \theta_t|, 360^\circ - |\theta_q - \theta_t|) \le \theta_0 $$

### 2.9.3 Tính điểm tương đồng (Similarity Score)
Điểm số đánh giá mức độ giống nhau thường dựa trên số lượng cặp Minutiae trùng khớp ($n$) so với tổng số lượng Minutiae trên hai ảnh ($N_1, N_2$). Một công thức phổ biến là:

$$ Score = \frac{n^2}{N_1 \times N_2} \quad \text{hoặc} \quad Score = \sqrt{\frac{n^2}{N_1 \times N_2}} $$

Điểm $Score$ sẽ nằm trong khoảng $[0, 1]$. Hệ thống sẽ dùng một ngưỡng $Threshold$ (ví dụ: 0.40) để quyết định hai vân tay có phải là của cùng một người hay không.

---

## 2.10 KD-Tree (K-Dimensional Tree)

Trong bước đánh giá sự trùng khớp (2.9.2), việc tìm kiếm các điểm Minutiae thỏa mãn điều kiện khoảng cách $r_0$ nếu dùng phương pháp vét cạn (Brute-force) sẽ có độ phức tạp $O(N_1 \times N_2)$, gây tốn kém thời gian khi tập dữ liệu lớn. Để tối ưu hóa, cấu trúc dữ liệu KD-Tree được sử dụng.

### 2.10.1 Khái niệm KD-Tree
KD-Tree là một cây tìm kiếm nhị phân phân chia không gian (Space-partitioning data structure) dùng để tổ chức các điểm trong không gian K chiều. Trong bài toán vân tay, không gian thường là 2 chiều (tọa độ x, y).

Tại mỗi node của cây, không gian bị chia làm đôi bởi một mặt phẳng siêu phẳng (hyperplane) vuông góc với một trong các trục tọa độ. Việc chia cắt xen kẽ giữa trục X và trục Y ở mỗi tầng của cây giúp phân rã không gian tìm kiếm một cách hiệu quả.

### 2.10.2 Ứng dụng trong tìm kiếm lân cận
KD-Tree cực kỳ mạnh mẽ trong việc giải quyết bài toán "Tìm kiếm lân cận trong bán kính R" (Radius Neighborhood Search).
- Khi xây dựng cây cho tập Minutiae của Template, mất thời gian $O(N \log N)$.
- Khi lấy một điểm Minutiae từ Query để tìm xem có điểm Template nào nằm trong bán kính $r_0$ hay không, thuật toán chỉ cần duyệt qua các nhánh cây có khả năng chứa nghiệm, loại bỏ các nhánh không gian nằm ngoài bán kính. Thời gian tìm kiếm giảm xuống chỉ còn xấp xỉ $O(\log N)$.

Mặc dù đối với số lượng Minutiae trên một ảnh vân tay là tương đối nhỏ (20-80 điểm), KD-Tree có thể không thể hiện được sức mạnh vượt trội so với các phép toán ma trận véc-tơ hóa (như NumPy Broadcasting), nhưng về mặt lý thuyết thuật toán, đây là cấu trúc dữ liệu chuẩn mực để giải quyết bài toán so khớp tọa độ không gian.

---

## 2.11 Thiết kế CSDL Sinh trắc học

Hệ thống AFIS không chỉ gồm các thuật toán xử lý ảnh mà còn cần một hệ thống quản trị cơ sở dữ liệu (Database Management System) vững chắc để lưu trữ, truy xuất và quản lý hàng vạn mẫu vân tay.

### 2.11.1 Mô hình Dữ liệu Quan hệ
Dữ liệu sinh trắc thường được chia thành hai nhóm rõ rệt, do đó cần thiết kế CSDL quan hệ gồm tối thiểu hai bảng:
1. **Bảng định danh (Users):** Chứa thông tin nhân khẩu học (ID, Tên, Giới tính, Vai trò).
2. **Bảng mẫu sinh trắc (Templates):** Chứa dữ liệu vân tay đã trích xuất.

Mô hình này giúp đảm bảo chuẩn hóa dữ liệu: một người dùng (User) có thể có nhiều mẫu vân tay (nhiều ngón tay khác nhau, hoặc nhiều lần lấy mẫu khác nhau của cùng một ngón).

### 2.11.2 Lưu trữ Đặc trưng Đa cấp
Mỗi bản ghi trong bảng Templates không lưu trữ ảnh gốc (để tiết kiệm không gian và bảo mật), mà lưu các đặc trưng đã trích xuất:
- **Level 1 Features:** `pattern_class` (Whorl, Loop, Arch), `core_x`, `core_y`, `delta_x`, `delta_y`. Các trường này thường được đánh Index (Chỉ mục) để phục vụ cho thao tác "Lọc sơ bộ" (Pre-filtering). Khi tìm kiếm một vân tay loại Whorl, hệ thống dùng Index để truy vấn SQL cực nhanh, loại bỏ các mẫu Arch/Loop mà không cần phải thực hiện so khớp phức tạp.
- **Level 2 Features:** Tập hợp các điểm Minutiae. Vì số lượng Minutiae của mỗi vân tay là khác nhau, chúng không thể lưu thành các cột tĩnh trong CSDL quan hệ. Giải pháp phổ biến là tuần tự hóa (Serialization) danh sách Minutiae thành định dạng JSON hoặc lưu dưới dạng BLOB (Binary Large Object) trong một cột duy nhất (`minutiae_data`).

Cách tiếp cận kết hợp: Dùng CSDL SQL để lọc Level 1 siêu tốc, sau đó lấy JSON của các bản ghi đã lọc ra, giải mã và đẩy vào thuật toán tính toán Level 2 là cấu trúc chuẩn trong các hệ thống AFIS.
