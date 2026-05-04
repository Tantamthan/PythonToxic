# Toxic Comment Analysis — Phân tích bình luận độc hại tiếng Việt

Pipeline Python phân tích hành vi toxic trong bình luận mạng xã hội tiếng Việt.  
Dữ liệu kết hợp từ **ViHSD** (dataset học thuật) và bình luận tự thu thập từ **YouTube** / **Reddit**, gán nhãn tự động bằng **Gemini AI**.

---

## Tính năng chính

| Tính năng | Mô tả |
| --- | --- |
| Thu thập đa nguồn | YouTube Data API, Reddit (PRAW), dataset ViHSD |
| Gán nhãn tự động | Gemini API phân loại `CLEAN` / `OFFENSIVE` / `HATE` |
| Gán nhãn thủ công | Export → Excel → Import khi Gemini hết quota |
| Phân loại tăng dần | Comment đã gán nhãn chuyển vào `labeled_collected.csv`, xóa khỏi CSV nền tảng |
| Làm sạch dữ liệu | Chuẩn hóa tiếng Việt (underthesea), xóa trùng, lọc độ dài tối thiểu |
| Thống kê mô tả | Phân phối nhãn, top từ toxic, tỷ lệ theo giờ, so sánh nguồn |
| Trực quan hóa | 6 loại biểu đồ + WordCloud, dark theme |

---

## Cấu trúc dự án

```text
New folder/
├── toxic_analysis/              # Source code chính
│   ├── main.py                  # Pipeline 5 bước
│   ├── collect/                 # Thu thập dữ liệu
│   │   ├── youtube_scraper.py   # Scraper YouTube Data API
│   │   ├── reddit_scraper.py    # Scraper Reddit (PRAW) + lọc tiếng Việt
│   │   └── vihsd_loader.py      # Loader dataset ViHSD
│   ├── process/                 # Xử lý dữ liệu
│   │   ├── clean_data.py        # Làm sạch, chuẩn hóa, xóa trùng
│   │   ├── label_data.py        # Gán nhãn tự động bằng Gemini (incremental)
│   │   └── manual_label.py      # Gán nhãn thủ công qua CSV
│   ├── analyze/                 # Phân tích & trực quan
│   │   ├── statistics.py        # Thống kê mô tả
│   │   └── visualize.py         # Biểu đồ (matplotlib, seaborn, wordcloud)
│   ├── data/collected/          # Cache dữ liệu tự thu thập
│   │   ├── youtube_comments.csv # Bình luận YouTube chưa gán nhãn
│   │   ├── reddit_comments.csv  # Bình luận Reddit chưa gán nhãn
│   │   └── labeled_collected.csv# Tổng hợp tất cả comment đã gán nhãn
│   └── output/                  # Kết quả phân tích
│       ├── results.csv          # Dữ liệu cuối cùng (text, label, source)
│       ├── summary.json         # Báo cáo tóm tắt (JSON)
│       └── charts/              # 8 biểu đồ PNG
├── vihsd/                       # Dataset ViHSD (train/dev/test CSV)
├── docs/
│   ├── DATA_SCHEMA.md           # Chuẩn cột dữ liệu
│   └── PROJECT_REQUEST.txt      # Yêu cầu ban đầu của dự án
├── .env.example                 # Mẫu cấu hình API key
├── .gitignore
└── requirements.txt
```

---

## Pipeline thực thi

```
BƯỚC 1 → Thu thập dữ liệu (YouTube + Reddit + ViHSD)
BƯỚC 2 → Làm sạch dữ liệu (chuẩn hóa, xóa trùng, lọc ngắn)
BƯỚC 3 → Gán nhãn tự động bằng Gemini (incremental labeling)
BƯỚC 4 → Phân tích & thống kê mô tả
BƯỚC 5 → Trực quan hóa & xuất kết quả
```

### Quy trình gán nhãn tăng dần (Incremental Labeling)

1. Đọc comment chưa phân loại từ CSV của từng nền tảng (`youtube_comments.csv`, `reddit_comments.csv`)
2. Gọi Gemini API gán nhãn theo batch
3. Comment phân loại thành công → chuyển vào `labeled_collected.csv`
4. Comment phân loại thành công → xóa khỏi CSV nền tảng gốc
5. Comment lỗi (`LABEL_ERROR`) → giữ nguyên trong CSV nền tảng để retry lần sau
6. ViHSD đã có nhãn sẵn → bỏ qua

---

## Cài đặt

```powershell
cd "E:\PROJECT PYTHON\New folder"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền API key vào `.env`:

```text
YOUTUBE_API_KEY=<your_key>
GEMINI_API_KEY=<your_key>
GEMINI_MODEL=gemini-2.5-flash

# Chỉ cần nếu thu thập Reddit
REDDIT_CLIENT_ID=<your_id>
REDDIT_CLIENT_SECRET=<your_secret>
REDDIT_USER_AGENT=toxic-analysis/1.0
```

### Thư viện sử dụng

| Thư viện | Mục đích |
| --- | --- |
| `pandas`, `numpy` | Xử lý dữ liệu |
| `google-api-python-client` | YouTube Data API |
| `google-genai` | Gemini API gán nhãn |
| `praw` | Reddit API |
| `underthesea` | NLP tiếng Việt (tách từ) |
| `matplotlib`, `seaborn` | Biểu đồ |
| `wordcloud` | Đám mây từ |
| `tenacity` | Retry mechanism cho API |
| `tqdm` | Progress bar |
| `python-dotenv` | Đọc file `.env` |
| `lxml`, `lxml_html_clean` | Parse HTML |

---

## Cách sử dụng

### Chạy chỉ với ViHSD (không cần API)

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --no-youtube --no-label
```

### Chạy YouTube + ViHSD + Gemini

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --max-per-video 200 --max-label-rows 100 --label-batch-size 5 --label-delay 8
```

### Thêm Reddit

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --reddit --reddit-subs VietNam TroChuyenLinhTinh
```

### Reddit cho phép bình luận không phải tiếng Việt

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --reddit --reddit-allow-non-vi
```

### Chỉ định video YouTube cụ thể

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --video-ids abc123 def456
```

---

## Tham số CLI đầy đủ

### Nguồn dữ liệu

| Tham số | Mặc định | Mô tả |
| --- | --- | --- |
| `--no-youtube` | `False` | Bỏ qua thu thập YouTube |
| `--reddit` | `False` | Bật thu thập Reddit |
| `--max-per-video` | `500` | Số bình luận tối đa mỗi video YouTube |
| `--video-ids` | — | Danh sách YouTube video ID tùy chỉnh |
| `--reddit-subs` | Vietnam, VietNam, TroChuyenLinhTinh | Danh sách subreddit tùy chỉnh |
| `--reddit-sort` | `hot` | Sắp xếp bài Reddit (`hot`/`new`/`top`/`controversial`) |
| `--reddit-max-posts` | `50` | Số bài viết tối đa mỗi subreddit |
| `--reddit-allow-non-vi` | `False` | Tắt bộ lọc tiếng Việt cho Reddit |

### Gán nhãn Gemini

| Tham số | Mặc định | Mô tả |
| --- | --- | --- |
| `--no-label` | `False` | Bỏ qua gán nhãn Gemini |
| `--label-batch-size` | `25` | Số bình luận mỗi batch gửi Gemini |
| `--label-delay` | `1.5` | Giây nghỉ giữa các batch |
| `--max-label-rows` | `0` | Giới hạn số dòng gọi Gemini (`0` = không giới hạn) |
| `--gemini-model` | `gemini-2.5-flash` | Model Gemini sử dụng |
| `--label-retries` | `6` | Số lần retry mỗi batch khi lỗi 429/503 |
| `--continue-on-quota` | `False` | Tiếp tục chạy dù Gemini báo hết quota |
| `--refresh-label-cache` | `False` | Bỏ cache nhãn cũ, gọi Gemini lại |

---

## Xử lý lỗi Gemini API

Khi Gemini trả `503 Service Unavailable` hoặc `429 Too Many Requests`, giảm batch và tăng delay:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --max-label-rows 50 --label-batch-size 3 --label-delay 15 --label-retries 8
```

Nếu log báo `limit: 20` (hết quota), chờ quota hồi rồi chạy lại:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --refresh-label-cache --max-label-rows 200 --label-batch-size 20 --label-delay 20
```

**Lưu ý:** Batch lỗi được đánh dấu `LABEL_ERROR`, không bị gán nhầm thành `CLEAN`. Các dòng `LABEL_ERROR` không được tính vào phân tích cuối.

---

## Gán nhãn thủ công (Manual Labeling)

Khi Gemini hết quota, có thể gán nhãn bằng tay qua `manual_label.py`:

### 1. Xuất comment chưa gán nhãn ra file review

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py export --limit 100
```

### 2. Mở file và điền nhãn

Mở `toxic_analysis\data\collected\manual_review.csv` bằng Excel, điền cột `label`:

| Nhãn | Ý nghĩa |
| --- | --- |
| `CLEAN` | Bình thường, không công kích |
| `OFFENSIVE` | Thô tục, chửi thề, xúc phạm cá nhân |
| `HATE` | Kỳ thị, thù địch, kích động bạo lực |

### 3. Import nhãn đã điền

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py import
```

### 4. Kiểm tra trạng thái

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\process\manual_label.py status
```

Script sẽ tự động thêm dòng đã gắn nhãn vào `labeled_collected.csv` và xóa khỏi CSV nền tảng gốc.

---

## Đầu ra (Output)

| File | Mô tả |
| --- | --- |
| `output/results.csv` | Dữ liệu cuối cùng (cột: `text`, `label`, `source`) |
| `output/summary.json` | Báo cáo tóm tắt: tổng mẫu, phân phối nhãn, tỷ lệ toxic theo nguồn, danh sách biểu đồ |
| `output/charts/` | Thư mục chứa 8 biểu đồ phân tích |
| `run.log` | Log chi tiết toàn bộ pipeline |

### Biểu đồ được tạo

| # | File | Nội dung |
| --- | --- | --- |
| 1 | `01_phan_phoi_nhan.png` | Biểu đồ cột phân phối CLEAN / OFFENSIVE / HATE |
| 2 | `02_ty_le_toxic.png` | Biểu đồ tròn: toxic vs clean + chi tiết 3 nhãn |
| 3 | `03_top_tu_toxic.png` | Top 20 từ phổ biến nhất trong bình luận toxic |
| 4 | `04_wordcloud_hate.png` | WordCloud nhãn HATE |
| 5 | `04_wordcloud_offensive.png` | WordCloud nhãn OFFENSIVE |
| 6 | `04_wordcloud_clean.png` | WordCloud nhãn CLEAN |
| 7 | `05_toxic_theo_gio.png` | Tỷ lệ toxic theo giờ trong ngày |
| 8 | `06_so_sanh_nguon.png` | So sánh tỷ lệ toxic giữa các nguồn dữ liệu |

---

## Data Schema

Chi tiết tại [`docs/DATA_SCHEMA.md`](docs/DATA_SCHEMA.md).

### Cột chính

| Cột | Kiểu | Mô tả |
| --- | --- | --- |
| `text` | string | Nội dung bình luận đã chuẩn hóa |
| `label` | string | `CLEAN` / `OFFENSIVE` / `HATE` |
| `source` | string | `vihsd`, `youtube`, `reddit` |
| `split` | string | `train`, `dev`, `test`, `collected` |

### Cột bổ sung

| Cột | Mô tả |
| --- | --- |
| `comment_id` | ID bình luận từ nền tảng gốc |
| `video_id` / `post_id` | ID video YouTube / bài Reddit |
| `author` | Tác giả bình luận |
| `published_at` | Thời gian đăng |
| `labeled_by` | Nguồn nhãn (`ViHSD`, `Gemini_AI`, `Manual`) |
| `record_key` | Khóa ổn định cho cache gán nhãn |

---

## Ghi chú

- File `.env`, dữ liệu cache (`data/collected/`), kết quả (`output/`) và `.venv` đã được thêm vào `.gitignore`.
- Dataset ViHSD dùng file có prefix `._` (`._train.csv`, `._dev.csv`, `._test.csv`).
- Nhãn do Gemini sinh ra chỉ nên xem là nhãn hỗ trợ, nên lấy mẫu kiểm tra lại khi dùng cho báo cáo nghiêm túc.
- CSV đầu ra dùng encoding `utf-8-sig` để Excel trên Windows đọc tiếng Việt đúng.
- Bước làm sạch xóa trùng theo `text + source`, không gộp toàn bộ chỉ theo nội dung.
- Cache gán nhãn dùng `record_key` (ưu tiên `source + comment_id`) để tránh xóa nhầm comment cùng nội dung từ nguồn khác.
