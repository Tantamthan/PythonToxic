# Toxic Comment Analysis

Dự án Python phân tích bình luận độc hại tiếng Việt từ ViHSD và dữ liệu tự thu thập từ YouTube/Reddit.

## Cấu trúc

```text
New folder/
├── .venv/                  # môi trường ảo Python, không chứa source code
├── toxic_analysis/         # source code chính
│   ├── main.py             # chạy pipeline
│   ├── collect/            # thu thập dữ liệu
│   ├── process/            # làm sạch và gán nhãn
│   ├── analyze/            # thống kê và biểu đồ
│   ├── data/collected/     # cache dữ liệu tự thu thập
│   └── output/             # kết quả phân tích
├── vihsd/                  # train/dev/test CSV của ViHSD
├── docs/DATA_SCHEMA.md     # chuẩn cột dữ liệu
├── .env.example            # mẫu cấu hình API key
└── requirements.txt
```

## Cài đặt

```powershell
cd "E:\PROJECT PYTHON\New folder"
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền API key vào `.env` nếu cần thu thập/gán nhãn bằng API.

## Chạy nhanh

Chạy chỉ với ViHSD, không cần API:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --no-youtube --no-label
```

Chạy YouTube + ViHSD + Gemini:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --max-per-video 200 --max-label-rows 100 --label-batch-size 5 --label-delay 8
```

Thêm Reddit:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --reddit --reddit-subs VietNam TroChuyenLinhTinh
```

## Kiểm soát chi phí API

- `--max-per-video`: giới hạn số bình luận YouTube mỗi video.
- `--max-label-rows`: giới hạn số dòng gửi Gemini. Dùng `0` để không giới hạn.
- `--label-batch-size`: số bình luận trong một batch Gemini.
- `--label-delay`: số giây nghỉ giữa các batch Gemini.
- `--label-retries`: số lần thử lại mỗi batch khi Gemini trả lỗi 429/503.
- `--gemini-model`: model Gemini dùng để gán nhãn, mặc định `gemini-2.5-flash`.
- `--refresh-label-cache`: bỏ cache nhãn cũ và gọi Gemini lại.
- Mặc định chương trình sẽ dừng sớm khi Gemini báo hết quota.

Nếu Gemini trả `503 Service Unavailable` hoặc `429 Too Many Requests`, hãy giảm batch và tăng delay:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --max-label-rows 50 --label-batch-size 3 --label-delay 15 --label-retries 8
```

Nếu log báo `limit: 20`, số request đã hết. Chờ quota hồi rồi chạy lại:

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --refresh-label-cache --max-label-rows 200 --label-batch-size 20 --label-delay 20
```

Khi API lỗi, pipeline đánh dấu dòng đó là `LABEL_ERROR` và không tính vào phân tích cuối. Không còn gán `CLEAN` mặc định cho batch lỗi.

## Đầu ra

- `toxic_analysis/output/results.csv`: dữ liệu đã xử lý và có nhãn.
- `toxic_analysis/output/charts/`: biểu đồ phân tích.
- `toxic_analysis/run.log`: log chạy pipeline.

## Ghi chú

File `.env`, dữ liệu cache, kết quả output và `.venv` không nên commit lên Git.
