# 📋 TÓM TẮT CẬP NHẬT DỰ ÁN

**Ngày cập nhật:** 03/05/2026  
**Người thực hiện:** AI Assistant  
**Mục đích:** Thêm phân tích nâng cao cho dự án phân tích bình luận toxic tiếng Việt

---

## 🎯 TỔNG QUAN

Dự án ban đầu chỉ có **phân tích cơ bản** (đếm số lượng CLEAN/OFFENSIVE/HATE, top từ toxic).  
Bây giờ đã được **nâng cấp** với 4 loại phân tích sâu hơn để hiểu rõ hơn về bình luận toxic.

---

## ✨ NHỮNG GÌ ĐÃ THÊM MỚI

### 1️⃣ **File Mới: `advanced_stats.py`** (450+ dòng code)

**Vị trí:** `toxic_analysis/analyze/advanced_stats.py`

**Chức năng:** Phân tích nâng cao dữ liệu bình luận

#### 📊 **4 Loại Phân Tích:**

**A. N-gram Analysis (Phân tích cụm từ)**
- **Là gì?** Tìm các cụm từ toxic xuất hiện cùng nhau
- **Ví dụ:** 
  - Bigram (2 từ): "địt mẹ", "con cặc", "con mẹ"
  - Trigram (3 từ): "địt con mẹ", "laugh out loud"
- **Tại sao quan trọng?** Hiểu ngữ cảnh, không chỉ từ đơn lẻ

**B. Sentiment Intensity (Mức độ toxic)**
- **Là gì?** Cho điểm từ 0-100 cho mỗi bình luận
- **Phân loại:**
  - 0 điểm = KHÔNG TOXIC
  - 1-19 điểm = TOXIC NHẸ
  - 20-49 điểm = TOXIC TRUNG BÌNH
  - 50-79 điểm = TOXIC NẶNG
  - 80-100 điểm = CỰC KỲ TOXIC
- **Ví dụ:** "đồ ngu" = 20 điểm, "địt con mẹ" = 85 điểm
- **Tại sao quan trọng?** Phân biệt mức độ nghiêm trọng

**C. Correlation Analysis (Phân tích tương quan)**
- **Là gì?** Xem mối liên hệ giữa độ dài comment và mức độ toxic
- **Kết quả:** Tương quan yếu (0.173) → Comment dài không nhất thiết toxic hơn
- **Tại sao quan trọng?** Hiểu yếu tố ảnh hưởng đến toxic

**D. Topic Modeling (Phân tích chủ đề)**
- **Là gì?** Tìm từ khóa đặc trưng cho từng loại bình luận
- **Ví dụ:**
  - HATE thường có: "con", "nó", "cái" (kỳ thị)
  - OFFENSIVE thường có: "mẹ", "đm", "vl" (chửi thề)
  - CLEAN thường có: "anh", "em", "người" (bình thường)
- **Tại sao quan trọng?** Hiểu nội dung chính của từng loại

---

### 2️⃣ **File Mới: `advanced_visualize.py`** (300+ dòng code)

**Vị trí:** `toxic_analysis/analyze/advanced_visualize.py`

**Chức năng:** Vẽ biểu đồ cho phân tích nâng cao

#### 📈 **5 Biểu Đồ Mới:**

1. **`07_bigram_toxic.png`** - Top 15 cụm 2 từ toxic
2. **`08_trigram_toxic.png`** - Top 15 cụm 3 từ toxic
3. **`09_muc_do_toxic.png`** - Phân phối 5 mức độ toxic
4. **`10_tuong_quan_dodai_toxic.png`** - Scatter plot độ dài vs điểm toxic
5. **`11_chu_de_theo_nhan.png`** - So sánh từ khóa giữa 3 nhãn

---

### 3️⃣ **File Cập Nhật: `main.py`**

**Những thay đổi:**

✅ **Thêm import:**
```python
from analyze.advanced_stats import chay_phan_tich_nang_cao
from analyze.advanced_visualize import ve_tat_ca_bieu_do_nang_cao
```

✅ **Thêm Bước 4.5:** Phân tích nâng cao (chạy sau thống kê cơ bản)

✅ **Cập nhật Bước 5:** Vẽ thêm 5 biểu đồ nâng cao

✅ **Xuất file mới:** `results_advanced.csv` với cột:
- `text`: Nội dung bình luận
- `label`: Nhãn (CLEAN/OFFENSIVE/HATE)
- `source`: Nguồn (vihsd/youtube/reddit)
- `toxic_score`: Điểm toxic (0-100) ⭐ MỚI
- `toxic_level`: Mức độ toxic (5 cấp) ⭐ MỚI

---

### 4️⃣ **File Cập Nhật: `README.md`**

**Những thay đổi:**

✅ Thêm mục **"Phân tích nâng cao"** giải thích 4 loại phân tích

✅ Cập nhật mục **"Đầu ra"** với:
- Danh sách 11 biểu đồ chi tiết (6 cơ bản + 5 nâng cao)
- 2 file CSV (results.csv + results_advanced.csv)

✅ Thêm mục **"Changelog"** ghi lại lịch sử thay đổi

---

## 📊 KẾT QUẢ SAU KHI CẬP NHẬT

### Trước khi cập nhật:
- ❌ 6 biểu đồ cơ bản
- ❌ 1 file CSV
- ❌ Chỉ biết số lượng CLEAN/OFFENSIVE/HATE

### Sau khi cập nhật:
- ✅ **11 biểu đồ** (6 cơ bản + 5 nâng cao)
- ✅ **2 file CSV** (cơ bản + nâng cao)
- ✅ Biết thêm:
  - Cụm từ toxic phổ biến (bigram/trigram)
  - Mức độ toxic từng comment (0-100)
  - Tương quan độ dài vs toxic
  - Từ khóa đặc trưng từng loại

---

## 🚀 CÁCH CHẠY

**Lệnh không đổi, vẫn như cũ:**

```powershell
.\.venv\Scripts\python.exe .\toxic_analysis\main.py --no-youtube --no-label
```

**Kết quả:**
- Chạy trong ~58 giây (thay vì ~10 giây trước đây)
- Tạo 11 biểu đồ (thay vì 6)
- Tạo 2 file CSV (thay vì 1)

---

## 📁 CẤU TRÚC FILE MỚI

```
toxic_analysis/
├── analyze/
│   ├── statistics.py           # Cũ - Thống kê cơ bản
│   ├── visualize.py            # Cũ - Biểu đồ cơ bản
│   ├── advanced_stats.py       # ⭐ MỚI - Phân tích nâng cao
│   └── advanced_visualize.py   # ⭐ MỚI - Biểu đồ nâng cao
├── main.py                     # ✏️ Đã cập nhật
└── output/
    ├── results.csv             # Cũ - Dữ liệu cơ bản
    ├── results_advanced.csv    # ⭐ MỚI - Dữ liệu nâng cao
    └── charts/
        ├── 01-06_*.png         # Cũ - 6 biểu đồ cơ bản
        └── 07-11_*.png         # ⭐ MỚI - 5 biểu đồ nâng cao
```

---

## 🎓 LỢI ÍCH CHO BÁO CÁO

### Trước đây chỉ nói được:
- "Có 24,158 bình luận CLEAN (81.8%)"
- "Có 3,336 bình luận HATE (11.3%)"
- "Từ 'mẹ' xuất hiện 682 lần"

### Bây giờ có thể nói thêm:
- "Cụm từ toxic phổ biến nhất là 'địt mẹ' (267 lần)"
- "Bình luận HATE có điểm toxic trung bình 30.10/100"
- "Không có mối liên hệ mạnh giữa độ dài comment và mức độ toxic (r=0.173)"
- "Bình luận HATE thường chứa từ kỳ thị như 'con', 'nó', 'cái'"
- "83.8% bình luận không toxic, chỉ 1.6% cực kỳ toxic"

➡️ **Báo cáo sâu hơn, chuyên nghiệp hơn, có số liệu cụ thể hơn!**

---

## ✅ ĐÃ TEST VÀ HOẠT ĐỘNG TỐT

- ✅ Chạy thành công không lỗi
- ✅ Tạo đầy đủ 11 biểu đồ
- ✅ Xuất 2 file CSV đúng format
- ✅ Log chi tiết trong `run.log`
- ✅ Thời gian chạy hợp lý (~58 giây)

---

## 📝 GHI CHÚ QUAN TRỌNG

1. **Không cần cài thêm thư viện** - Tất cả đã có trong `requirements.txt`
2. **Không cần thay đổi cách chạy** - Lệnh vẫn như cũ
3. **Tương thích ngược** - Vẫn tạo 6 biểu đồ cơ bản như trước
4. **Tự động** - Phân tích nâng cao chạy tự động, không cần config thêm

---

## 🤔 CÂU HỎI THƯỜNG GẶP

**Q: Tại sao chạy lâu hơn?**  
A: Vì phải tính điểm toxic cho 29,533 bình luận (~13 giây) và phân tích n-gram (~7 giây)

**Q: Có thể tắt phân tích nâng cao không?**  
A: Có, nhưng cần sửa code trong `main.py` (comment dòng gọi `buoc_4_5_phan_tich_nang_cao`)

**Q: Điểm toxic tính như thế nào?**  
A: Dựa trên từ điển 100+ từ toxic với trọng số 1-10, sau đó chuẩn hóa về 0-100

**Q: File nào quan trọng nhất để xem?**  
A: `results_advanced.csv` - Có đầy đủ thông tin cơ bản + nâng cao

---

## 📞 HỖ TRỢ

Nếu có lỗi, kiểm tra:
1. File `toxic_analysis/run.log` - Xem log chi tiết
2. Đảm bảo đã cài đủ thư viện: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Kiểm tra Python version: `python --version` (cần >= 3.11)

---

**🎉 Chúc bạn làm báo cáo tốt!**
