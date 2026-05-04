#### **b) Tìm kiếm lân cận và Đánh giá trùng khớp (Neighborhood Search & Bounding Box)**

Sau khi hai tập điểm Minutiae đã được đồng bộ hóa về cùng một hệ tọa độ không gian, hệ thống tiến hành tìm kiếm các cặp điểm trùng khớp (Mated pairs). Một trong những đóng góp cải tiến quan trọng của nghiên cứu này là việc áp dụng **Ràng buộc kiểm tra đồng nhất loại đặc trưng (Type Matching)** trong không gian lân cận, thay vì chỉ dựa vào các yếu tố khoảng cách hình học thông thường.

Cụ thể, hai điểm Minutiae (một từ ảnh truy vấn $m_q$ và một từ ảnh mẫu $m_t$) được công nhận là trùng khớp hoàn toàn nếu và chỉ nếu thỏa mãn đồng thời cả ba điều kiện sau:

1. **Khoảng cách không gian (Spatial Distance):** Nằm trong bán kính dung sai cho phép $r_0$ (thường là 15 pixel) để bù trừ cho sự co giãn da tay.
2. **Độ lệch góc hướng (Direction Difference):** Chênh lệch góc nhỏ hơn ngưỡng $\theta_0$ (thường là $14^\circ$).
3. **Đồng nhất loại đặc trưng (Type matching):** Cả hai điểm phải cùng là điểm Kết thúc (Termination) hoặc cùng là điểm Rẽ nhánh (Bifurcation).

Công thức toán học và logic ràng buộc được biểu diễn như sau:

$$ SD(m_q, m_t) = \sqrt{(x_q - x_t)^2 + (y_q - y_t)^2} \le r_0 $$
$$ DD(m_q, m_t) = \min(|\theta_q - \theta_t|, 360^\circ - |\theta_q - \theta_t|) \le \theta_0 $$
$$ Type(m_q) = Type(m_t) $$

Trong các nghiên cứu truyền thống hoặc các cài đặt cơ bản, điều kiện thứ 3 thường bị bỏ qua hoặc chỉ áp dụng cho điểm gốc (Reference Point). Điều này dẫn đến một **lỗ hổng sinh trắc học nghiêm trọng**: một điểm Kết thúc của ảnh truy vấn nếu vô tình nằm trong vùng lân cận của một điểm Rẽ nhánh của ảnh mẫu vẫn sẽ được tính là một cặp khớp. Việc ghép cặp sai lệch bản chất sinh học này làm tăng số lượng điểm khớp ảo, đẩy điểm tương đồng (Similarity Score) lên cao một cách bất thường, từ đó làm tăng tỷ lệ nhận diện sai **FAR (False Acceptance Rate)**.

Bằng cách áp dụng chặt chẽ cả 3 điều kiện trên, hệ thống không chỉ triệt tiêu các cặp điểm khớp lỗi do nhiễu sinh ra mà còn tăng tính nghiêm ngặt của thuật toán so khớp. Để giải quyết bài toán tìm kiếm xấp xỉ trên không gian đa chiều kèm theo ràng buộc phân loại này một cách tối ưu, hệ thống đã tích hợp cấu trúc dữ liệu **KD-Tree (K-Dimensional Tree)**. KD-Tree giúp khoanh vùng các điểm lân cận trong bán kính $r_0$ với độ phức tạp $O(N_1 \log N_2)$, sau đó bộ lọc phân loại sẽ loại bỏ các điểm không cùng nhóm `Type`, mang lại tốc độ xử lý vượt trội và độ chính xác sinh trắc học cao.
