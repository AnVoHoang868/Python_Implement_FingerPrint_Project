### 2.4 Các kỹ thuật so khớp và tìm kiếm xấp xỉ không gian nhiều chiều

#### 2.4.1 So khớp mô hình điểm bằng phép biến đổi không gian (Alignment-based Point Pattern Matching)

Trái ngược với việc so sánh các vector có kích thước cố định, dữ liệu đầu ra của quá trình trích xuất Minutiae là một đám mây điểm (Point Cloud) với số lượng phần tử biến thiên. Mỗi điểm mang 3 giá trị không gian (tọa độ $x$, $y$ và góc hướng $\theta$). Do đó, để so khớp hai vân tay, hệ thống sử dụng thuật toán **So khớp mô hình điểm (Point Pattern Matching)**.

Khó khăn lớn nhất của mô hình này là hai bức ảnh vân tay quét tại các thời điểm khác nhau sẽ luôn bị lệch vị trí (Translation) và góc xoay (Rotation). Để giải quyết bài toán này, quy trình so khớp được thực hiện qua ba giai đoạn chính: Biến đổi không gian, Tìm kiếm xấp xỉ, và Tính điểm tương đồng.

**a) Biến đổi hệ tọa độ không gian (Spatial Alignment)**

Để có thể so sánh, toàn bộ các điểm Minutiae của hai bức ảnh phải được đồng bộ về chung một hệ quy chiếu. Thuật toán chọn một cặp điểm đặc trưng bất kỳ (một từ ảnh truy vấn, một từ cơ sở dữ liệu) làm gốc tọa độ tương đối (Reference Point). Gọi tọa độ của điểm gốc này là $(x_{ref}, y_{ref})$ với góc hướng $\theta_{ref}$. 

Áp dụng ma trận xoay 2D (2D Rotation Matrix) và phép tịnh tiến, mọi điểm $(x, y, \theta)$ trong tập hợp sẽ được chuyển đổi sang hệ tọa độ không gian mới:

$$ \begin{bmatrix} x' \\ y' \end{bmatrix} = \begin{bmatrix} \cos(\theta_{ref}) & \sin(\theta_{ref}) \\ -\sin(\theta_{ref}) & \cos(\theta_{ref}) \end{bmatrix} \begin{bmatrix} x - x_{ref} \\ y - y_{ref} \end{bmatrix} $$

Và góc hướng mới được điều chỉnh: $\theta' = \theta - \theta_{ref}$

Việc áp dụng phép biến đổi này giúp hệ thống triệt tiêu hoàn toàn sự sai lệch về thao tác đặt ngón tay của người dùng trên thiết bị quét.

**b) Tìm kiếm lân cận và Đánh giá trùng khớp (Neighborhood Search & Bounding Box)**

Sau khi hai tập điểm đã đồng bộ không gian, hệ thống tiến hành tìm các cặp điểm trùng khớp (Mated pairs). Một cặp được coi là trùng khớp nếu khoảng cách không gian (Spatial Distance) giữa chúng nhỏ hơn ngưỡng $r_0$ và độ lệch góc (Direction Difference) nhỏ hơn ngưỡng $\theta_0$:

$$ SD(m_q, m_t) = \sqrt{(x_q - x_t)^2 + (y_q - y_t)^2} \le r_0 $$
$$ DD(m_q, m_t) = \min(|\theta_q - \theta_t|, 360^\circ - |\theta_q - \theta_t|) \le \theta_0 $$

Để giải quyết bài toán "Tìm kiếm lân cận trong bán kính $r_0$" một cách tối ưu trên không gian đa chiều, hệ thống sử dụng cấu trúc dữ liệu **KD-Tree (K-Dimensional Tree)**. KD-Tree phân chia không gian thành các nhánh nhị phân (bằng các siêu mặt phẳng vuông góc với trục X và Y). Nhờ đó, thay vì phải quét vét cạn (Brute-force) để đo khoảng cách Euclid giữa mọi cặp điểm với độ phức tạp $O(N_1 \times N_2)$, thuật toán chỉ cần truy vấn trên KD-Tree với độ phức tạp xấp xỉ $O(N_1 \log N_2)$, tăng tốc độ tìm kiếm một cách vượt trội trên các cơ sở dữ liệu lớn.

**c) Tính điểm tương đồng (Similarity Scoring)**

Sau khi tìm được tất cả các cặp điểm trùng khớp ($n$) từ hai không gian tọa độ, điểm số đánh giá mức độ giống nhau (Similarity Score) sẽ được tính toán dựa trên tỷ lệ giữa số điểm khớp và tổng khối lượng Minutiae ban đầu ($N_1, N_2$) của cả hai vân tay:

$$ Score = \sqrt{\frac{n^2}{N_1 \times N_2}} $$

Giá trị Score nhận được nằm trong khoảng $[0, 1]$. Hệ thống thiết lập một ngưỡng dung sai (Threshold) nhất định; nếu Score vượt qua ngưỡng này, hệ thống kết luận hai mẫu vân tay thuộc về cùng một người. Thuật toán sẽ thử lặp lại quá trình này bằng cách chọn các cặp điểm gốc khác nhau và lấy giá trị Score cao nhất làm kết quả cuối cùng.
