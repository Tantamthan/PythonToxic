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

### File CSV
- `toxic_analysis/output/results.csv`: dữ liệu đã xử lý và có nhãn (text, label, source).
- `toxic_analysis/output/results_advanced.csv`: dữ liệu với phân tích nâng cao (toxic_score, toxic_level).

### Biểu đồ cơ bản (6 biểu đồ)
- `01_phan_phoi_nhan.png`: Phân phối nhãn CLEAN/OFFENSIVE/HATE
- `02_ty_le_toxic.png`: Biểu đồ tròn tỷ lệ toxic vs clean
- `03_top_tu_toxic.png`: Top 20 từ toxic phổ biến
- `04_wordcloud_*.png`: WordCloud cho từng nhãn (3 file)
- `05_toxic_theo_gio.png`: Toxic theo giờ (nếu có dữ liệu thời gian)
- `06_so_sanh_nguon.png`: So sánh giữa YouTube và ViHSD

### Biểu đồ nâng cao (5 biểu đồ)
- `07_bigram_toxic.png`: Top 15 cụm 2 từ toxic phổ biến
- `08_trigram_toxic.png`: Top 15 cụm 3 từ toxic phổ biến
- `09_muc_do_toxic.png`: Phân phối mức độ toxic (nhẹ → nặng)
- `10_tuong_quan_dodai_toxic.png`: Tương quan độ dài comment vs điểm toxic
- `11_chu_de_theo_nhan.png`: Từ khóa đặc trưng cho từng nhãn

### Log
- `toxic_analysis/run.log`: log chi tiết quá trình chạy pipeline.

## Phân tích nâng cao

Dự án bao gồm 4 loại phân tích nâng cao:

### 1. N-gram Analysis (Phân tích cụm từ)
- **Bigram**: Phân tích cụm 2 từ toxic phổ biến (vd: "con mẹ", "đồ ngu")
- **Trigram**: Phân tích cụm 3 từ toxic phổ biến (vd: "địt con mẹ")
- Giúp hiểu ngữ cảnh và cách kết hợp từ toxic

### 2. Sentiment Intensity (Mức độ toxic)
- Tính điểm toxic cho mỗi comment (0-100)
- Phân loại thành 5 mức:
  - **KHÔNG TOXIC** (0 điểm)
  - **TOXIC NHẸ** (1-19 điểm)
  - **TOXIC TRUNG BÌNH** (20-49 điểm)
  - **TOXIC NẶNG** (50-79 điểm)
  - **CỰC KỲ TOXIC** (80-100 điểm)
- Dựa trên từ điển 100+ từ toxic với trọng số

### 3. Correlation Analysis (Phân tích tương quan)
- Mối liên hệ giữa độ dài comment và mức độ toxic
- Số từ toxic trung bình theo từng nhãn
- Scatter plot với đường xu hướng

### 4. Topic Modeling (Phân tích chủ đề)
- Tìm từ khóa đặc trưng cho từng nhãn
- So sánh chủ đề giữa HATE, OFFENSIVE, CLEAN
- Giúp hiểu nội dung chính của từng loại bình luận

## Ghi chú

File `.env`, dữ liệu cache, kết quả output và `.venv` không nên commit lên Git.

---

## Changelog

### [2026-05-03] - Thêm Phân Tích Nâng Cao

**Thêm mới:**
- `toxic_analysis/analyze/advanced_stats.py`: Module phân tích nâng cao (450+ dòng code)
  - **N-gram analysis**: Phân tích bigram (cụm 2 từ) và trigram (cụm 3 từ) toxic phổ biến
  - **Sentiment intensity**: Tính điểm toxic (0-100) cho mỗi comment dựa trên từ điển 100+ từ toxic
  - **Correlation analysis**: Phân tích tương quan độ dài comment vs mức độ toxic
  - **Topic modeling**: Tìm từ khóa đặc trưng cho từng nhãn (HATE, OFFENSIVE, CLEAN)
  
- `toxic_analysis/analyze/advanced_visualize.py`: Module visualization nâng cao (300+ dòng code)
  - Biểu đồ bigram/trigram (top 15 cụm từ toxic)
  - Biểu đồ phân phối 5 mức độ toxic (KHÔNG TOXIC → CỰC KỲ TOXIC)
  - Scatter plot tương quan với đường xu hướng
  - Biểu đồ so sánh từ khóa giữa 3 nhãn

**Cập nhật:**
- `toxic_analysis/main.py`: Tích hợp phân tích nâng cao vào pipeline
  - Thêm import: `advanced_stats`, `advanced_visualize`
  - Thêm **Bước 4.5**: Phân tích nâng cao (chạy sau thống kê cơ bản)
  - Cập nhật **Bước 5**: Vẽ thêm 5 biểu đồ nâng cao
  - Xuất file `results_advanced.csv` với cột `toxic_score` và `toxic_level`
  - Cập nhật banner kết quả hiển thị số biểu đồ cơ bản vs nâng cao

- `README.md`: Cập nhật tài liệu đầy đủ
  - Thêm mục "Phân tích nâng cao" giải thích 4 loại phân tích
  - Cập nhật mục "Đầu ra" với danh sách 11 biểu đồ chi tiết
  - Thêm mục "Changelog" ghi lại lịch sử thay đổi

**Kết quả:**
- ✅ Tổng **11 biểu đồ** (6 cơ bản + 5 nâng cao)
- ✅ **2 file CSV** output:
  - `results.csv`: Dữ liệu cơ bản (text, label, source)
  - `results_advanced.csv`: Dữ liệu nâng cao (+ toxic_score, toxic_level)
- ✅ Phân tích sâu hơn về:
  - Ngữ cảnh toxic (bigram/trigram)
  - Mức độ toxic (5 cấp độ từ nhẹ → nặng)
  - Tương quan độ dài vs toxic (correlation: 0.173 - yếu)
  - Chủ đề đặc trưng cho từng loại bình luận

**Thời gian chạy:**
- Pipeline đầy đủ: ~58 giây (với 29,533 mẫu ViHSD)
- Phân tích nâng cao: ~46 giây (trong đó tính điểm toxic ~13s)

**Test:**
- ✅ Chạy thành công với lệnh: `.\.venv\Scripts\python.exe .\toxic_analysis\main.py --no-youtube --no-label`
- ✅ Tạo đầy đủ 11 biểu đồ PNG
- ✅ Xuất 2 file CSV không lỗi
- ✅ Log chi tiết đầy đủ trong `run.log`
