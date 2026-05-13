# Toxic Analysis Module

Thư mục này chứa source code chính của pipeline phân tích bình luận độc hại tiếng Việt.

## Chạy từ thư mục gốc dự án

```powershell
cd "E:\PROJECT PYTHON\New folder"
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --no-collected --no-label
```

## Crawl từng mạng xã hội

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\collect\youtube_scraper.py
.\.venv\Scripts\python.exe .\toxic_analysis\collect\reddit_scraper.py
.\.venv\Scripts\python.exe .\toxic_analysis\collect\facebook_scraper.py --group-id 263510030791508
```

## Tổng hợp và gán nhãn Gemini

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --max-label-rows 100 --label-batch-size 5 --label-delay 8
```

Lọc bình luận gần giống nhau:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --sources facebook --similarity-threshold 95
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --sources facebook --similarity-threshold 0
```

Nếu Gemini báo `503` hoặc `429`, giảm tải API:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --max-label-rows 50 --label-batch-size 3 --label-delay 15 --label-retries 8
```

Nếu log có `limit: 20`, bạn đã hết quota request. Chờ quota hồi rồi chạy lại và bỏ cache lỗi:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --refresh-label-cache --max-label-rows 200 --label-batch-size 20 --label-delay 20
```

Batch lỗi sẽ được đánh dấu `LABEL_ERROR`, không bị gán nhầm thành `CLEAN`.

## Thư mục liên quan

- `..\vihsd\`: chứa `train.csv`, `dev.csv`, `test.csv` hoặc các file dạng `._train.csv`, `._dev.csv`, `._test.csv`.
- `data\collected\`: cache dữ liệu YouTube/Reddit/Facebook và nhãn Gemini.
- `output\`: kết quả CSV và biểu đồ.
- `output\summary.json`: báo cáo tóm tắt để dùng lại cho dashboard hoặc báo cáo HTML/PDF.

## Tinh chỉnh dữ liệu

- Dữ liệu YouTube/Reddit/Facebook lưu thêm `comment_id` và `author` nếu nền tảng trả về.
- Cache gán nhãn dùng `record_key` để di chuyển/xóa đúng bình luận đã xử lý, tránh xóa nhầm các dòng có cùng nội dung ở nguồn khác.
- Bước làm sạch xóa trùng theo `text + source`, không còn gộp toàn bộ chỉ theo nội dung bình luận.
- Bước làm sạch có thêm lọc trùng gần giống trong cùng `source` bằng `--similarity-threshold`.
- `main.py` không gọi crawler nữa; muốn có dữ liệu mạng xã hội nào thì chạy file scraper của mạng đó trước.

## File cấu hình

Nên đặt API key ở file `.env` tại thư mục gốc dự án:

```text
YOUTUBE_API_KEY=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=toxic-analysis/1.0
FACEBOOK_GROUP_ID=
FACEBOOK_COOKIE=
FACEBOOK_CHROMEDRIVER_PATH=
FACEBOOK_BROWSER_BINARY=
```

Xem thêm `..\README.md` và `..\docs\DATA_SCHEMA.md`.

## Manual labeling khi Gemini hết quota

Xuất 100 comment Reddit chưa gắn nhãn ra file để điền tay:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py export --limit 100
```

Mở `toxic_analysis\data\collected\manual_review.csv`, điền cột `label` bằng một trong:

```text
CLEAN
OFFENSIVE
HATE
```

Nhập lại các dòng đã điền nhãn:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py import
```

Script sẽ thêm dòng đã gắn nhãn vào `labeled_collected.csv` và xóa các dòng đó khỏi `reddit_comments.csv`.
Kiểm tra trạng thái hiện tại:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py status
```
