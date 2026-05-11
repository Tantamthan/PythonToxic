"""
advanced_stats.py
-----------------
Phân tích nâng cao cho dữ liệu bình luận toxic tiếng Việt.

Các phân tích thực hiện:
1. N-gram Analysis: Phân tích cụm từ toxic phổ biến (bigram, trigram)
2. Sentiment Intensity: Đo mức độ toxic (nhẹ → nặng)
3. Correlation Analysis: Mối liên hệ giữa độ dài comment và mức độ toxic
4. Topic Modeling: Phát hiện chủ đề trong bình luận toxic
"""

import re
import logging
import pandas as pd
import numpy as np
from collections import Counter
from typing import Dict, List, Tuple

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Thử import underthesea để tách từ
try:
    from underthesea import word_tokenize
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    UNDERTHESEA_AVAILABLE = False
    logger.warning("⚠ underthesea chưa được cài. N-gram sẽ dùng split đơn giản.")

# Stopwords tiếng Việt cơ bản
STOPWORDS_VI = {
    "và", "của", "là", "có", "trong", "đã", "được", "với", "cho", "không",
    "này", "đó", "bạn", "mình", "một", "các", "những", "thì", "cũng", "như",
    "đến", "từ", "lại", "nên", "nhưng", "vì", "để", "hay", "ra", "vào", "rất",
    "thế", "thật", "quá", "lên", "xuống", "rồi", "đây", "khi", "tới", "ở",
    "ai", "gì", "sao", "vậy", "à", "ơi", "he", "she", "it", "the", "a", "an",
    "nan", "nen", "di", "ve", "do", "ma", "la", "co", "i", "you", "me", "my",
}


def _tach_tu(text: str) -> List[str]:
    """
    Tách từ từ văn bản tiếng Việt.
    
    Args:
        text: Văn bản cần tách từ
    
    Returns:
        Danh sách từ (đã lọc stopwords và ký tự số)
    """
    if UNDERTHESEA_AVAILABLE:
        try:
            tokens = word_tokenize(text, format="text").split()
        except Exception:
            tokens = text.lower().split()
    else:
        tokens = text.lower().split()
    
    # Lọc: bỏ stopwords, số, ký tự đặc biệt, từ quá ngắn
    tokens = [
        t for t in tokens
        if t not in STOPWORDS_VI
        and not re.match(r"^\d+$", t)
        and len(t) >= 2
        and re.search(r"[a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]", t)
    ]
    return tokens


# ═══════════════════════════════════════════════════════════════════════════
# 1. N-GRAM ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def phan_tich_ngram(
    df: pd.DataFrame,
    n: int = 2,
    top_k: int = 20,
    chi_toxic: bool = True
) -> pd.DataFrame:
    """
    Phân tích N-gram (cụm từ) phổ biến trong bình luận.
    
    Args:
        df: DataFrame với cột 'text' và 'label'
        n: Độ dài n-gram (2=bigram, 3=trigram)
        top_k: Số n-gram muốn lấy
        chi_toxic: Nếu True, chỉ phân tích OFFENSIVE và HATE
    
    Returns:
        DataFrame chứa n-gram và tần suất
    """
    logger.info(f"▶ Phân tích {n}-gram (cụm {n} từ) phổ biến...")
    
    # Lọc dữ liệu
    if chi_toxic:
        df_filter = df[df["label"].isin(["OFFENSIVE", "HATE"])]
        loai = "toxic (OFFENSIVE + HATE)"
    else:
        df_filter = df.copy()
        loai = "tất cả"
    
    if df_filter.empty:
        logger.warning(f"⚠ Không có dữ liệu {loai} để phân tích {n}-gram")
        return pd.DataFrame(columns=["ngram", "count"])
    
    logger.info(f"  → Phân tích {len(df_filter)} bình luận {loai}...")
    
    # Đếm n-gram
    ngram_counter = Counter()
    
    for text in df_filter["text"].dropna():
        tokens = _tach_tu(str(text))
        
        # Tạo n-gram
        if len(tokens) >= n:
            for i in range(len(tokens) - n + 1):
                ngram = " ".join(tokens[i:i+n])
                ngram_counter[ngram] += 1
    
    # Lấy top K
    top_ngrams = ngram_counter.most_common(top_k)
    df_result = pd.DataFrame(top_ngrams, columns=["ngram", "count"])
    
    logger.info(f"✓ Tìm thấy {len(ngram_counter)} {n}-gram khác nhau")
    logger.info(f"  Top {min(5, len(df_result))} {n}-gram phổ biến nhất:")
    for _, row in df_result.head(5).iterrows():
        logger.info(f"    '{row['ngram']}': {row['count']:,} lần")
    
    return df_result


def phan_tich_bigram_trigram(df: pd.DataFrame, top_k: int = 20) -> Dict[str, pd.DataFrame]:
    """
    Phân tích cả bigram và trigram cùng lúc.
    
    Args:
        df: DataFrame với cột 'text' và 'label'
        top_k: Số n-gram muốn lấy cho mỗi loại
    
    Returns:
        Dict chứa kết quả bigram và trigram
    """
    logger.info("=" * 60)
    logger.info("📊 PHÂN TÍCH N-GRAM (CỤM TỪ TOXIC)")
    logger.info("=" * 60)
    
    results = {
        "bigram": phan_tich_ngram(df, n=2, top_k=top_k, chi_toxic=True),
        "trigram": phan_tich_ngram(df, n=3, top_k=top_k, chi_toxic=True),
    }
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 2. SENTIMENT INTENSITY (MỨC ĐỘ TOXIC)
# ═══════════════════════════════════════════════════════════════════════════

# Từ điển từ toxic với trọng số (1-10, 10 là nặng nhất)
TU_TOXIC_TRONG_SO = {
    # Mức độ nhẹ (1-3)
    "ngu": 2, "ngốc": 2, "khùng": 2, "điên": 2, "dở": 1, "tệ": 1, "xấu": 1,
    "kém": 1, "tồi": 1, "vớ vẩn": 2, "vô dụng": 2,
    
    # Mức độ trung bình (4-6)
    "đồ": 4, "thằng": 4, "con": 4, "đéo": 5, "vl": 5, "vcl": 5, "vãi": 4,
    "đm": 6, "dm": 6, "đmm": 6, "lồn": 6, "cặc": 6, "buồi": 5, "cứt": 4,
    
    # Mức độ nặng (7-10)
    "địt": 8, "đụ": 8, "fuck": 7, "shit": 6, "bitch": 7, "đĩ": 8, "cave": 7,
    "mẹ": 7, "cha": 7, "dcm": 9, "dcmm": 9, "clgt": 8, "clmm": 8,
    "chết": 6, "giết": 9, "thối": 5, "rác": 5, "súc vật": 8, "súc sinh": 8,
    "đồ chó": 7, "chó": 6, "lợn": 6, "heo": 5, "khốn": 6, "nạn": 6,
}


def tinh_diem_toxic(text: str) -> float:
    """
    Tính điểm toxic của một bình luận dựa trên từ điển.
    
    Args:
        text: Văn bản cần đánh giá
    
    Returns:
        Điểm toxic (0-100)
    """
    if not text or pd.isna(text):
        return 0.0
    
    text_lower = str(text).lower()
    tokens = _tach_tu(text_lower)
    
    # Tính tổng điểm
    tong_diem = 0
    so_tu_toxic = 0
    
    for token in tokens:
        if token in TU_TOXIC_TRONG_SO:
            tong_diem += TU_TOXIC_TRONG_SO[token]
            so_tu_toxic += 1
    
    # Kiểm tra cụm từ (bigram)
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} {tokens[i+1]}"
        if bigram in TU_TOXIC_TRONG_SO:
            tong_diem += TU_TOXIC_TRONG_SO[bigram]
            so_tu_toxic += 1
    
    # Chuẩn hóa điểm về thang 0-100
    if so_tu_toxic == 0:
        return 0.0
    
    # Điểm trung bình * số từ toxic (có trọng số)
    diem_tb = tong_diem / so_tu_toxic
    diem_cuoi = min(100, diem_tb * 10 + so_tu_toxic * 5)
    
    return round(diem_cuoi, 2)


def phan_tich_muc_do_toxic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phân tích mức độ toxic của từng bình luận và phân loại thành các mức.
    
    Args:
        df: DataFrame với cột 'text' và 'label'
    
    Returns:
        DataFrame với cột 'toxic_score' và 'toxic_level'
    """
    logger.info("=" * 60)
    logger.info("📊 PHÂN TÍCH MỨC ĐỘ TOXIC (SENTIMENT INTENSITY)")
    logger.info("=" * 60)
    
    df = df.copy()
    
    # Tính điểm toxic cho từng dòng
    logger.info("▶ Đang tính điểm toxic cho từng bình luận...")
    df["toxic_score"] = df["text"].apply(tinh_diem_toxic)
    
    # Phân loại mức độ
    def phan_loai_muc_do(score: float) -> str:
        if score == 0:
            return "KHÔNG TOXIC"
        elif score < 20:
            return "TOXIC NHẸ"
        elif score < 50:
            return "TOXIC TRUNG BÌNH"
        elif score < 80:
            return "TOXIC NẶNG"
        else:
            return "CỰC KỲ TOXIC"
    
    df["toxic_level"] = df["toxic_score"].apply(phan_loai_muc_do)
    
    # Thống kê
    logger.info("✓ Phân phối mức độ toxic:")
    phan_phoi = df["toxic_level"].value_counts()
    for level, count in phan_phoi.items():
        pct = count / len(df) * 100
        logger.info(f"  {level:20s}: {count:6,d} ({pct:5.1f}%)")
    
    # Thống kê theo nhãn
    logger.info("\n✓ Điểm toxic trung bình theo nhãn:")
    for label in ["CLEAN", "OFFENSIVE", "HATE"]:
        df_label = df[df["label"] == label]
        if not df_label.empty:
            avg_score = df_label["toxic_score"].mean()
            logger.info(f"  {label:12s}: {avg_score:.2f}/100")
    
    return df


# ═══════════════════════════════════════════════════════════════════════════
# 3. CORRELATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def phan_tich_tuong_quan(df: pd.DataFrame) -> Dict[str, any]:
    """
    Phân tích mối tương quan giữa các yếu tố:
    - Độ dài comment vs mức độ toxic
    - Số từ toxic vs nhãn
    - Độ dài vs nhãn
    
    Args:
        df: DataFrame với cột 'text', 'label', 'toxic_score'
    
    Returns:
        Dict chứa kết quả phân tích tương quan
    """
    logger.info("=" * 60)
    logger.info("📊 PHÂN TÍCH TƯƠNG QUAN (CORRELATION ANALYSIS)")
    logger.info("=" * 60)
    
    df = df.copy()
    
    # Tính các metrics
    df["do_dai"] = df["text"].str.len()
    df["so_tu"] = df["text"].apply(lambda x: len(str(x).split()))
    
    # Đếm số từ toxic
    def dem_tu_toxic(text: str) -> int:
        if not text or pd.isna(text):
            return 0
        tokens = _tach_tu(str(text).lower())
        return sum(1 for t in tokens if t in TU_TOXIC_TRONG_SO)
    
    df["so_tu_toxic"] = df["text"].apply(dem_tu_toxic)
    
    # 1. Tương quan độ dài vs toxic score
    if "toxic_score" in df.columns:
        corr_dodai_toxic = df[["do_dai", "toxic_score"]].corr().iloc[0, 1]
        logger.info(f"✓ Tương quan độ dài comment vs điểm toxic: {corr_dodai_toxic:.3f}")
        
        if abs(corr_dodai_toxic) < 0.3:
            logger.info("  → Tương quan yếu (không có mối liên hệ rõ ràng)")
        elif abs(corr_dodai_toxic) < 0.7:
            logger.info("  → Tương quan trung bình")
        else:
            logger.info("  → Tương quan mạnh")
    
    # 2. Thống kê theo nhãn
    logger.info("\n✓ Thống kê theo nhãn:")
    stats_by_label = df.groupby("label").agg({
        "do_dai": ["mean", "median"],
        "so_tu": ["mean", "median"],
        "so_tu_toxic": ["mean", "sum"]
    }).round(2)
    
    logger.info(f"\n{stats_by_label.to_string()}")
    
    # 3. Phân tích chi tiết
    results = {
        "correlation_length_toxic": corr_dodai_toxic if "toxic_score" in df.columns else None,
        "stats_by_label": stats_by_label,
        "df_with_metrics": df
    }
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# 4. TOPIC MODELING (ĐƠN GIẢN)
# ═══════════════════════════════════════════════════════════════════════════

def phan_tich_chu_de(df: pd.DataFrame, top_k: int = 10) -> Dict[str, pd.DataFrame]:
    """
    Phân tích chủ đề trong bình luận toxic bằng phương pháp đơn giản:
    - Tìm từ khóa đặc trưng cho từng nhãn
    - So sánh từ xuất hiện nhiều ở HATE vs OFFENSIVE vs CLEAN
    
    Args:
        df: DataFrame với cột 'text' và 'label'
        top_k: Số từ khóa đặc trưng cho mỗi nhãn
    
    Returns:
        Dict chứa từ khóa đặc trưng cho từng nhãn
    """
    logger.info("=" * 60)
    logger.info("📊 PHÂN TÍCH CHỦ ĐỀ (TOPIC MODELING)")
    logger.info("=" * 60)
    
    results = {}
    
    for label in ["HATE", "OFFENSIVE", "CLEAN"]:
        df_label = df[df["label"] == label]
        
        if df_label.empty:
            continue
        
        logger.info(f"\n▶ Phân tích chủ đề cho nhãn: {label}")
        
        # Đếm từ
        word_counter = Counter()
        for text in df_label["text"].dropna():
            tokens = _tach_tu(str(text))
            word_counter.update(tokens)
        
        # Lấy top K
        top_words = word_counter.most_common(top_k)
        df_result = pd.DataFrame(top_words, columns=["word", "count"])
        
        results[label] = df_result
        
        logger.info(f"  Top {min(5, len(df_result))} từ khóa:")
        for _, row in df_result.head(5).iterrows():
            logger.info(f"    '{row['word']}': {row['count']:,} lần")
    
    # So sánh từ đặc trưng
    logger.info("\n✓ Phân tích hoàn tất!")
    logger.info("  → HATE thường chứa: từ kỳ thị, phân biệt đối xử")
    logger.info("  → OFFENSIVE thường chứa: từ chửi thề, xúc phạm")
    logger.info("  → CLEAN thường chứa: từ bình thường, tích cực")
    
    return results


# ═══════════════════════════════════════════════════════════════════════════
# HÀM CHÍNH: CHẠY TẤT CẢ PHÂN TÍCH NÂNG CAO
# ═══════════════════════════════════════════════════════════════════════════

def chay_phan_tich_nang_cao(df: pd.DataFrame) -> Dict[str, any]:
    """
    Chạy toàn bộ phân tích nâng cao.
    
    Args:
        df: DataFrame đã gán nhãn
    
    Returns:
        Dict chứa tất cả kết quả phân tích
    """
    logger.info("\n" + "=" * 60)
    logger.info("🚀 BẮT ĐẦU PHÂN TÍCH NÂNG CAO")
    logger.info("=" * 60)
    
    results = {}
    
    # 1. N-gram Analysis
    results["ngram"] = phan_tich_bigram_trigram(df, top_k=20)
    
    # 2. Sentiment Intensity
    df_with_score = phan_tich_muc_do_toxic(df)
    results["df_with_intensity"] = df_with_score
    
    # 3. Correlation Analysis
    results["correlation"] = phan_tich_tuong_quan(df_with_score)
    
    # 4. Topic Modeling
    results["topics"] = phan_tich_chu_de(df, top_k=15)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ PHÂN TÍCH NÂNG CAO HOÀN TẤT!")
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    # Test với dữ liệu mẫu
    test_df = pd.DataFrame({
        "text": [
            "video hay quá cảm ơn bạn",
            "địt con mẹ thằng đó ngu vl",
            "dân tộc này toàn loại rác rưởi súc vật",
            "đồ ngu ngốc khùng điên",
            "bài viết rất hay và bổ ích",
        ],
        "label": ["CLEAN", "OFFENSIVE", "HATE", "OFFENSIVE", "CLEAN"]
    })
    
    results = chay_phan_tich_nang_cao(test_df)
    print("\n✓ Test hoàn tất!")
