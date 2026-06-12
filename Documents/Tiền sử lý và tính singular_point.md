## Các bước chuẩn hóa ảnh

### 1. (Preprocessing)
* **Mục tiêu:** Để xử lý các ảnh bị đường vân bị mờ, vùng quá sáng/tối, độ tương phản không đồng đều. Tạo điều kiện thuận lợi cho tính đạo hàm gradient 

* **Công thức chuẩn hóa:**  
 I_norm(x, y) = (I(x, y) - mean) / std

    Trong đó:
    - mean: giá trị trung bình của mức xám (mean cao --> ảnh có xu hướng sáng ngược lại là ảnh có xu hướng tối)
    - std: độ lệch chuẩn của mức xám
### 2. Phân đoạn vùng vân tay 
* **Mục tiêu:** Xử lý các vùng thừa như nền trắng xung quanh 
    - Phân đoạn thành 2 phần:
    Foreground và Background
* **Triển khai:** Nhân ảnh đã được xử lý với Mask --> giúp triệt tiêu hoàn toàn các điểm nhiễu ở vùng background --> Hỗ trợ tốt cho các bước tiếp theo như Tính hướng vân, tần số vân, gabor hoặc bước quan trọng nhất là Minuate các điểm ở nhòe ở biên của ảnh cũng có thể có xác suất nhận nhầm là các Termination, Bifurcation giả.

### 3. Tăng cường chất lượng ảnh (CLAHE)
* **Mục tiêu:** Xử lý tăng cường các vùng đường vân bị mờ/nhạt, độ tương phản giữa valley và ridge chưa đủ mạnh. 
* **Áp dụng thế nào ?** 

### 4. Phân đoạn vùng vân tay
* **Mục tiêu:** Loại bỏ vùng thông tin không có ích có trong ảnh 
* **Cách xử lý** Tách ảnh thành 2 vùng riêng biệt: 

    + Background: Vùng không chứa thông tin nhận dạng
    + Foreground: Vùng chứa vân tay 

### 5. Tăng cường chất lượng ảnh với CLAHE
* **Mục tiêu:** Làm rõ các phần ảnh đường vân 
* **Cách xử lý:** Chia ảnh thành các vùng ô nhỏ gọi là Tile --> Tính Historgram cho từng Tile --> Tính histogram cho từng Tile --> dùng 1 tham số Contrast Limit để giới hạn chiều cao của Histogram. 1 mức xám xuất hiện nhiều sẽ được cắt bớt phần vượt ngưỡng --> Phân phối lại cho các mức xám khác

* **Kết quả:** tăng độ tương phản giữa 2 phần valley và ridge 

6. Tính trường hướng vân - Orientation Field 
* **Mục tiêu:** Cho biết bản đồ mỗi vùng nhỏ của ảnh đang chạy theo hướng nào ?.  

* **Cách xử lý:** Tính hướng vân bằng Sobel Gradient.
    - **Gradient:** thường vuông góc với đường vân --> chia ảnh thành các block nhỏ 16x16 để tính hướng cho từng vùng nhỏ --> Tính cc đại lượng tích lũy gradient
        - Gxx = Tổng Gx^2
        - Gyy = Tổng Gy^2
        - Gxy = Tổng Gx x Gy
    - **Tính góc hướng vân:** Công thức thường dùng: 
        θ = 1/2 × atan2(2Gxy, Gxx - Gyy)
    - Làm trơn trường hướng --> kết quả đầu ra là 1 Orientation Map 

7. Chia ảnh thành các Block nhỏ \

**-->** Mỗi block đã được xác định với các trường orientation trước đó 

**-->** Hướng để đo khoảng cách của vân sẽ là θ + 90°.

**-->** Tần số vân sẽ được tính như sau: frequency = 1/ridge_spacing 

    Trong đó:
    ridge_spacing: khoảng cách trung bình.
    Ví dụ:
    vị trí ridge: 5,15,25,35
    => Khoảng cách giữa các ridge sẽ là: 15-5 =10, 25-15 = 10, 35-25=10

* **Tổng kết:** Sau khi tính được trường hướng sẽ dựa vào trường hướng đã có trên 1 block, hệ thống sẽ tiếp tục ước lượng tần số vân cục bộ. Tần số vân biểu thị cho mật độ lặp lại của các đường vân trong từng ảnh. Tính bằng cách lấy nghịch đảo của khoảng cách trung bình giữa 2 đường vân liên tiếp 

8. Lọc Gabor động 
* **Khái niệm Gabor tại sao lại chọn bộ lọc này ?:** Gabor Filter là bộ lọc ảnh chuyên dùng để phát hiện và tăng cường các cấu trúc dạng lặp lại theo chu kỳ, có hướng rõ ràng, có dạng sóng --> Thích hợp cho các ảnh vân tay vì ảnh có cấu trúc ridge, valley. 
    * Gabor động không dùng 1 hướng và 1 tần số cố định cho toàn bộ ảnh. Lấy 2 thông tin đã được xử lý ở phần trước là Orientation Field và FrequencyMap để xử lý
        + Vân chạy ngang: Gabor xoay ngang, vân chạy chéo Gabor xoay chéo
        + Vân dày: Gabor dùng tần số cao hơn, thấp dùng tần số thấp hơn
* **Quy trình lọc Gabor** 
- Với mỗi vùng hệ thống sẽ tạo 1 kernel Gabor dựa trên
\
θ: hướng vân
\
f: tần số vân
\
σx, σy: độ rộng của Gaussian
- Nhân tích chập kernel với ảnh: Sau khi có kernel, hệ thống thực hiện nhân tích chập giữa kernel Gabor với vùng ảnh 

9. Nhị phân hóa bằng ngưỡng
* **Quá trình thực hiện:** 
    - Ảnh sẽ được nhị phân hóa đưa ảnh về 2 giá trị 0 và 1. 
    - Ảnh sẽ được duyệt qua từng pixel lấy giá trị Gabor_result tại điểm pixel đó rồi so sánh với ngưỡng 0. nếu tại đó giá trị <= 0 thì đó là đường vân ngược lại là rãnh vân. 
10. Làm mảnh đường vân với thuật toán Zhang-Suen Thinning 

* **Zhang-Suen Thinning là gì ?:** Là thuật toán làm mảnh ảnh nhị phân.
* **Zhang-Suen Thinning hoạt động thế nào:** 
    - Tại mỗi pixel ở trung tâm thuật toán sẽ xét 8 pixel ở lân cận --> Nhằm xác định 2 đại lượng
    - 1. Số hàng xóm pixel mang giá trị 1 B(P1) (tức là giá trị pixel đại diện cho ridge - đường vân) điều kiện thường được đánh giá 2<=B(P1)<=6 
        + quá nhiều thì có thể nằm trong vùng giao không nên xóa 
        + nếu quá ít có thể là điểm cuối của đường vân
    - 2. Số lần chuyển từ 0 -> 1 A(P1) khi xét vòng quanh 8 điểm pixel lân cận  
        + Nếu A(P1) lớn hơn 1 pixel có thể đang nằm trong vùng rẽ nhánh 
        + Nếu A(P1) = 1 có thể là đang nằm trên 1 đoạn liên thông 

    * xét 2 lượt với mỗi pixel đen ta cần thoả mãn các điều kiện:
        + sub1: thỏa mãn các điều kiện sau
            + phải là 1 điểm đen (1)
            + Các điểm đen phải >=2 và <= 6
            + Các điểm số lần chuyển từ 0 -> 1 khi xét quay vòng quanh điểm pixel đen = 1
            + các điểm p2 * p4 * p6 = 0
            + các điểm p4 * p6 * p8 = 0
            
            => Có nghĩa là các điểm p2,p4,p6 không được cùng là điểm đen. điều kiện dưới tương tự 
        + sub2: thỏa mãn các điều kiện tương tự sub1 nhưng:
            + các điểm p2 * p4 * p6 = 0
            + các điểm p2 * p6 * p8 = 0 

        + Thuật toán dừng khi không còn pixel nào thỏa mãn các điều kiện trên thì ảnh sẽ là ảnh sekeleton


