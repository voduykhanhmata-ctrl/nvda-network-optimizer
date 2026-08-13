# NVDA Network Optimizer

Add-on NVDA tiếng Việt, được xây dựng từ các ý tưởng hữu ích trong `Toi_uu_mang_Nang_Cao_20_lenh.bat` nhưng không chạy một chuỗi lệnh phá cấu hình mạng.

**Tác giả:** Võ Duy Khánh

## Điểm chính

- Kiểm tra nhanh, chỉ đọc thông tin mạng và đo độ phản hồi DNS.
- So sánh Cloudflare, Google Public DNS và Quad9, sau đó **chỉ đề xuất** DNS IPv4 có độ phản hồi tốt nhất.
- Người dùng phải chọn kết nối mạng, thấy DNS hiện tại và xác nhận trước khi DNS thay đổi; báo cáo giữ kết quả đo trước/sau.
- Các thao tác có rủi ro (Winsock, proxy, ARP) được tách riêng, giải thích rõ và yêu cầu UAC.
- Có trang **Tối ưu và chẩn đoán mạng** trong Cài đặt NVDA để bật/tắt từng nhóm tác vụ, chọn DNS công cộng được đo và ẩn/hiện lối tắt ở menu Công cụ.
- Không bao gồm thao tác đặt lại tường lửa, release/renew IP, reset IPv4/IPv6 hàng loạt hoặc TCP Chimney từ batch gốc vì dễ làm mất cấu hình hoặc đã lỗi thời.
- Không có trường nhập lệnh tùy ý. Các thao tác cần quyền quản trị gọi PowerShell có sẵn của Windows với mã lệnh nằm trong bộ thao tác cố định, không chạy tệp script kèm add-on ở quyền cao.

## Đóng gói

Chạy `build_addon.ps1` trong thư mục dự án bằng PowerShell. Kết quả là `NetworkOptimizer-1.1.1.nvda-addon`.

## Cài đặt

Mở tệp `.nvda-addon`, chấp nhận cài đặt trong NVDA, rồi khởi động lại NVDA nếu được yêu cầu. Add-on hướng tới NVDA 2026.1.

## Tùy chỉnh và tìm add-on

Trong NVDA, mở **Preferences → Settings → Tối ưu và chẩn đoán mạng**. Tại đây có thể:

- Bật/tắt trợ lý DNS và chọn Cloudflare, Google Public DNS hoặc Quad9 để đo/đề xuất.
- Ẩn hoặc hiện các nhóm bảo trì, nâng cao và khắc phục mạnh để giao diện chỉ còn các mục phù hợp.
- Ẩn/hiện lối tắt trong **Tools**. Nếu đã ẩn mục này, vẫn mở được trang tùy chỉnh từ **Preferences → Settings** hoặc gán phím cho lệnh “Mở phần cài đặt Tối ưu và chẩn đoán mạng” trong Input Gestures.

Từ cửa sổ add-on cũng có nút **Tùy chỉnh add-on** dẫn thẳng tới trang này.

## Lưu ý

Đo DNS không đồng nghĩa với tăng tốc tải xuống. Các hồ sơ DNS dùng địa chỉ IPv4; add-on không tắt IPv6 và Windows/VPN có thể vẫn dùng DNS khác. Không sử dụng các thao tác khắc phục mạnh nếu bạn đang kết nối qua RDP/VPN hoặc mạng công ty mà chưa biết cấu hình đang dùng.

## Giấy phép

Dự án được phát hành theo [MIT License](LICENSE). Bản quyền © 2026 Võ Duy Khánh.
