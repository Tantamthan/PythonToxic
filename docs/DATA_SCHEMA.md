# Data Schema

Pipeline chuẩn hóa dữ liệu về các cột sau.

## Cột bắt buộc

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `text` | string | Nội dung bình luận đã chuẩn hóa về dạng text. |
| `label` | string/null | Một trong `CLEAN`, `OFFENSIVE`, `HATE`; null với dữ liệu mới chưa gán nhãn. |
| `source` | string | Nguồn dữ liệu: `vihsd`, `youtube`, `reddit`. |
| `split` | string | `train`, `dev`, `test`, hoặc `collected`. |

## Cột khuyến nghị

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `comment_id` | string | ID bình luận từ nền tảng gốc nếu có. |
| `video_id` | string | ID video YouTube nếu có. |
| `post_id` | string | ID bài Reddit nếu có. |
| `author` | string | Tác giả đã thu thập được nếu có. |
| `published_at` | datetime/null | Thời gian đăng bình luận. |
| `labeled_by` | string | `ViHSD`, `Gemini_AI`, hoặc nguồn nhãn khác. |
| `record_key` | string | Khóa ổn định dùng cho cache gán nhãn, ưu tiên `source + comment_id`, fallback về `source + parent_id + text`. |

## Quy ước nhãn

| Nhãn | Ý nghĩa |
| --- | --- |
| `CLEAN` | Bình luận bình thường, không công kích. |
| `OFFENSIVE` | Thô tục, chửi thề, xúc phạm cá nhân. |
| `HATE` | Kỳ thị, thù địch, kích động bạo lực hoặc phân biệt đối xử. |

## Lưu ý chất lượng

- Nhãn do Gemini sinh ra chỉ nên xem là nhãn hỗ trợ, không thay thế đánh giá thủ công.
- Khi dùng cho báo cáo nghiêm túc, nên lấy mẫu ngẫu nhiên để kiểm tra lại nhãn.
- CSV đầu ra dùng encoding `utf-8-sig` để Excel trên Windows đọc tiếng Việt ổn định hơn.
- Khi xóa trùng hoặc di chuyển dữ liệu đã gán nhãn, ưu tiên dùng `record_key`/ID nền tảng để tránh gộp nhầm hai bình luận có cùng nội dung ở nguồn khác nhau.
