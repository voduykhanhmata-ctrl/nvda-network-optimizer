# Đóng góp cho NVDA Network Optimizer

[English](CONTRIBUTING.md) | [Tiếng Việt](CONTRIBUTING.vi.md)

Cảm ơn bạn đã giúp cải thiện NVDA Network Optimizer. Dự án do Võ Duy Khánh phát triển và luôn chào đón đóng góp tôn trọng từ cộng đồng.

## Trước khi đóng góp

- Hãy tìm trong các Issue có sẵn trước khi báo lỗi hoặc đề xuất tính năng.
- Khi báo lỗi, mô tả phiên bản NVDA, phiên bản Windows, loại kết nối mạng và các bước tái hiện. Không đăng mật khẩu, mã truy cập, địa chỉ IP công cộng hoặc thông tin nhạy cảm khác.
- Hãy kiểm tra khả năng truy cập bằng NVDA. Thông báo cho người dùng cần rõ ràng, ngắn gọn và dùng được với giọng nói lẫn chữ nổi.

## Mã nguồn và tài liệu

- Giữ mọi chuỗi hiển thị cho người dùng trong `_()` để có thể dịch.
- Tiếng Anh là ngôn ngữ nguồn. Khi đổi chuỗi hiển thị, hãy cập nhật `locale/vi/LC_MESSAGES/nvda.po`, sau đó chạy `python compile_translations.py` để tạo lại `nvda.mo`.
- Giữ cả tài liệu Anh và Việt chính xác: `README.md`, `README.vi.md`, `doc/en/readme.html` và `doc/vi/readme.html`.
- Không thêm ô nhập lệnh tự do hoặc chạy lệnh do người dùng cung cấp. Tác vụ thay đổi mạng phải cố định, được giải thích, yêu cầu xác nhận và chỉ nâng quyền an toàn khi cần.

## Pull Request

1. Fork kho và tạo một nhánh chỉ phục vụ cho thay đổi của bạn.
2. Thực hiện và kiểm tra thay đổi.
3. Giải thích thay đổi là gì, vì sao hữu ích và cách bạn đã kiểm tra.
4. Giữ Pull Request tập trung; dùng Pull Request khác cho các thay đổi không liên quan.

Khi đóng góp, bạn đồng ý rằng phần đóng góp của mình có thể được phát hành theo [GNU General Public License phiên bản 2 hoặc mới hơn](LICENSE) (`GPL-2.0-or-later`) của dự án.
