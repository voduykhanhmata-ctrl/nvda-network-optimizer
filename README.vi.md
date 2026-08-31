# NVDA Network Optimizer

[English](README.md) | [Tiếng Việt](README.vi.md)

NVDA Network Optimizer là add-on NVDA hỗ trợ tiếng Việt và tiếng Anh. Dự án được xây dựng từ các ý tưởng hữu ích trong `Toi_uu_mang_Nang_Cao_20_lenh.bat`, nhưng không chạy một chuỗi lệnh có thể làm gián đoạn cấu hình mạng đang hoạt động.

**Tác giả:** Võ Duy Khánh

## Điểm chính

- Kiểm tra nhanh, chỉ đọc thông tin mạng và đo độ phản hồi DNS.
- So sánh Cloudflare, Google Public DNS và Quad9, sau đó **chỉ đề xuất** DNS IPv4 có độ phản hồi tốt nhất.
- Người dùng tự chọn kết nối mạng, xem DNS hiện tại và xác nhận trước khi DNS thay đổi; báo cáo giữ kết quả đo trước/sau.
- Có thể sao chép kết quả đang hiển thị hoặc lưu thành tệp văn bản UTF-8 tại nơi tự chọn; báo cáo không bao giờ tự được tải lên.
- Các thao tác có thể gây ảnh hưởng như đặt lại Winsock, proxy hoặc xóa ARP cache được tách riêng, giải thích rõ, yêu cầu xác nhận và quyền quản trị Windows.
- Có trang **Tối ưu và chẩn đoán mạng** trong Cài đặt NVDA để bật/tắt từng nhóm tác vụ, chọn DNS công cộng được đo và ẩn/hiện lối tắt ở menu Công cụ.
- Không bao gồm thao tác đặt lại tường lửa, release/renew IP, đặt lại IPv4/IPv6 hàng loạt hoặc TCP Chimney từ batch gốc vì chúng có thể làm mất cấu hình đang hoạt động hoặc đã lỗi thời.
- Không có trường nhập lệnh tùy ý. Các thao tác cần quyền quản trị dùng một tập thao tác PowerShell cố định có sẵn trong Windows; add-on không chạy tệp script kèm theo ở quyền cao.

## Ngôn ngữ

Giao diện, thông tin add-on và Trợ giúp có tiếng Anh lẫn tiếng Việt. Tiếng Anh là ngôn ngữ dự phòng cho các ngôn ngữ giao diện NVDA khác.

## Đóng gói

Chạy `build_addon.ps1` trong thư mục dự án bằng PowerShell. Kết quả là `NetworkOptimizer-1.3.2.nvda-addon`.

## Cài đặt

Mở tệp `.nvda-addon`, chấp nhận cài đặt trong NVDA, rồi khởi động lại NVDA nếu được yêu cầu. Add-on hướng tới NVDA 2026.1.

## Cập nhật tự động

Sau khi Network Optimizer được phát hành trong NVDA Add-on Store chính thức, NVDA có thể quản lý cập nhật an toàn dựa trên định danh add-on ổn định `networkOptimizer`. Mở **NVDA → Tùy chọn → Cài đặt → Add-on Store**, rồi đặt **Cập nhật tự động** thành **Tự động cập nhật**. NVDA sẽ tải bản tương thích từ Store trong nền và yêu cầu khởi động lại khi bản cập nhật đã sẵn sàng.

Gói thử nghiệm được cài trực tiếp từ máy chỉ nhận được cập nhật do Store quản lý sau khi add-on và phiên bản mới hơn đã được phát hành trong Store. Network Optimizer không có bộ tải riêng và không tự âm thầm cài tệp từ GitHub.

## Tùy chỉnh và tìm add-on

Trong NVDA, mở **Tùy chọn → Cài đặt → Tối ưu và chẩn đoán mạng**. Tại đây có thể:

- Bật/tắt trợ lý DNS và chọn Cloudflare, Google Public DNS hoặc Quad9 để đo/đề xuất.
- Ẩn hoặc hiện các nhóm bảo trì, nâng cao và khắc phục mạnh để giao diện chỉ còn các mục phù hợp.
- Ẩn/hiện lối tắt trong **Công cụ**. Nếu đã ẩn mục này, vẫn mở được trang tùy chỉnh từ **Tùy chọn → Cài đặt** hoặc gán phím cho lệnh “Mở phần cài đặt Tối ưu và chẩn đoán mạng” trong Cử chỉ nhập liệu.

Từ cửa sổ add-on cũng có nút **Tùy chỉnh add-on** dẫn thẳng tới trang này.

## Lưu ý quan trọng

Đo độ phản hồi DNS không đồng nghĩa với tăng tốc tải xuống. Các hồ sơ DNS dùng địa chỉ IPv4; add-on không tắt IPv6 và Windows/VPN có thể vẫn dùng DNS khác. Không sử dụng các thao tác khắc phục mạnh nếu bạn đang kết nối qua RDP, VPN hoặc mạng công ty mà chưa biết cấu hình đang dùng.

## Tham gia dự án

- Hãy thử [bản phát hành mới nhất](https://github.com/voduykhanhmata-ctrl/nvda-network-optimizer/releases/latest) và báo lỗi có thể tái hiện bằng biểu mẫu Báo lỗi.
- Bắt đầu từ việc dễ làm có nhãn [good first issue](https://github.com/voduykhanhmata-ctrl/nvda-network-optimizer/labels/good%20first%20issue) hoặc [help wanted](https://github.com/voduykhanhmata-ctrl/nvda-network-optimizer/labels/help%20wanted).
- Dùng [Discussions](https://github.com/voduykhanhmata-ctrl/nvda-network-optimizer/discussions) để hỏi đáp, gửi kết quả thử nghiệm và thảo luận ý tưởng trước khi tạo Issue.
- Đóng góp về khả năng truy cập, tài liệu, dịch thuật và kiểm thử cũng quan trọng như thay đổi mã nguồn.

## Đóng góp

Mọi đóng góp đều được chào đón. Hãy đọc [CONTRIBUTING.vi.md](CONTRIBUTING.vi.md) trước khi mở Issue hoặc Pull Request. Hướng dẫn tiếng Anh nằm tại [CONTRIBUTING.md](CONTRIBUTING.md).

## Giấy phép

Dự án là phần mềm tự do được phát hành theo [GNU General Public License phiên bản 2 hoặc mới hơn](LICENSE) (`GPL-2.0-or-later`). Bản quyền © 2026 Võ Duy Khánh.
