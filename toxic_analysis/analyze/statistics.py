"""
statistics.py
-------------
Phân tích thống kê mô tả trên tập dữ liệu bình luận đã gán nhãn.

Các phân tích thực hiện:
1. Phân phối nhãn CLEAN / OFFENSIVE / HATE
2. So sánh tỷ lệ toxic giữa YouTube và ViHSD
3. Top 20 từ toxic phổ biến nhất
4. Phân tích theo thời gian (giờ trong ngày)
5. Thống kê độ dài văn bản
"""

import re
import logging
import pandas as pd
import numpy as np
from collections import Counter

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Thử import underthesea để tách từ
try:
    from underthesea import word_tokenize
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    UNDERTHESEA_AVAILABLE = False

# Stopwords tiếng Việt cơ bản
STOPWORDS_VI = {
    "và", "của", "là", "có", "trong", "đã", "được", "với", "cho", "không",
    "này", "đó", "bạn", "mình", "một", "các", "những", "thì", "cũng", "như",
    "đến", "từ", "lại", "nên", "nhưng", "vì", "để", "hay", "ra", "vào", "rất",
    "thế", "thật", "quá", "lên", "xuống", "rồi", "đây", "khi", "tới", "ở",
    "ai", "gì", "sao", "vậy", "à", "ơi", "he", "she", "it", "the", "a", "an",
    "nan", "nen", "di", "ve", "do", "ma", "la", "co", "i", "you", "me", "my",
}


def _tach_tu(text: str) -> list[str]:
    """
    Tách từ từ văn bản tiếng Việt.
    Dùng underthesea nếu có, ngược lại dùng split đơn giản.
    
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


def thong_ke_phan_phoi_nhan(df: pd.DataFrame) -> dict:
    """
    Thống kê phân phối nhãn CLEAN / OFFENSIVE / HATE.
    
    Args:
        df: DataFrame với cột 'label'
    
    Returns:
        Dict chứa số lượng và tỷ lệ từng nhãn
    """
    if "label" not in df.columns:
        logger.error("✗ DataFrame thiếu cột 'label'")
        return {}
    
    tong = len(df)
    ket_qua = {}
    
    logger.info("📊 Phân phối nhãn:")
    for nhan in ["CLEAN", "OFFENSIVE", "HATE"]:
        so_luong = (df["label"] == nhan).sum()
        ty_le    = so_luong / tong * 100 if tong > 0 else 0
        ket_qua[nhan] = {"count": int(so_luong), "pct": round(ty_le, 2)}
        logger.info(f"   {nhan:12s}: {so_luong:6,d} ({ty_le:.1f}%)")
    
    logger.info(f"   {'TỔNG':12s}: {tong:6,d}")
    return ket_qua


def so_sanh_sources(df: pd.DataFrame) -> pd.DataFrame:
    """
    So sánh tỷ lệ toxic giữa các nguồn dữ liệu (YouTube, ViHSD).
    
    Args:
        df: DataFrame với cột 'label' và 'source'
    
    Returns:
        DataFrame cross-tabulation nguồn × nhãn
    """
    if "source" not in df.columns:
        logger.warning("⚠ Không có cột 'source', bỏ qua so sánh nguồn.")
        return pd.DataFrame()
    
    # Cross-tabulation
    ct = pd.crosstab(
        df["source"],
        df["label"],
        margins=True,
        normalize="index"
    ).round(4) * 100
    
    logger.info("📊 Tỷ lệ toxic theo nguồn (%):")
    logger.info(f"\n{ct.to_string()}")
    
    return ct


def top_tu_toxic(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Tìm Top N từ xuất hiện nhiều nhất trong bình luận OFFENSIVE và HATE.
    
    Args:
        df: DataFrame với cột 'text' và 'label'
        top_n: Số từ muốn lấy
    
    Returns:
        DataFrame chứa từ và tần suất xuất hiện
    """
    # Lọc chỉ bình luận toxic
    df_toxic = df[df["label"].isin(["OFFENSIVE", "HATE"])]
    
    if df_toxic.empty:
        logger.warning("⚠ Không có bình luận OFFENSIVE/HATE để phân tích từ")
        return pd.DataFrame(columns=["word", "count"])
    
    logger.info(f"▶ Phân tích top {top_n} từ toxic từ {len(df_toxic)} bình luận...")
    
    # Đếm tần suất từ
    word_counter: Counter = Counter()
    for text in df_toxic["text"].dropna():
        tokens = _tach_tu(str(text))
        word_counter.update(tokens)
    
    # Lấy top N
    top_words = word_counter.most_common(top_n)
    df_top = pd.DataFrame(top_words, columns=["word", "count"])
    
    logger.info(f"✓ Top {top_n} từ toxic phổ biến nhất:")
    for _, row in df_top.head(10).iterrows():
        logger.info(f"   '{row['word']}': {row['count']:,} lần")
    
    return df_top


def phan_tich_thoi_gian(df: pd.DataFrame) -> pd.DataFrame:
    """
    Phân tích tỷ lệ toxic theo giờ trong ngày.
    Chỉ áp dụng cho dữ liệu có cột 'published_at'.
    
    Args:
        df: DataFrame với cột 'published_at' và 'label'
    
    Returns:
        DataFrame với tỷ lệ toxic theo giờ
    """
    if "published_at" not in df.columns:
        logger.info("ℹ Không có cột 'published_at', bỏ qua phân tích thời gian.")
        return pd.DataFrame()
    
    try:
        # Parse thời gian
        df = df.copy()
        df["hour"] = pd.to_datetime(df["published_at"], errors="coerce").dt.hour
        df_valid   = df.dropna(subset=["hour"])
        
        if df_valid.empty:
            logger.warning("⚠ Không parse được thời gian")
            return pd.DataFrame()
        
        # Tính tỷ lệ toxic theo giờ
        df_valid = df_valid.copy()
        df_valid["is_toxic"] = df_valid["label"].isin(["OFFENSIVE", "HATE"]).astype(int)
        
        theo_gio = df_valid.groupby("hour").agg(
            tong_binh_luan=("is_toxic", "count"),
            so_toxic=("is_toxic", "sum")
        ).reset_index()
        theo_gio["ty_le_toxic"] = (theo_gio["so_toxic"] / theo_gio["tong_binh_luan"] * 100).round(2)
        
        logger.info("✓ Phân tích thời gian hoàn tất")
        return theo_gio
        
    except Exception as e:
        logger.error(f"✗ Lỗi phân tích thời gian: {e}")
        return pd.DataFrame()


def thong_ke_do_dai(df: pd.DataFrame) -> pd.DataFrame:
    """
    Thống kê độ dài văn bản theo từng nhãn.
    
    Args:
        df: DataFrame với cột 'text' và 'label'
    
    Returns:
        DataFrame với thống kê độ dài
    """
    df = df.copy()
    df["do_dai"] = df["text"].str.len()
    
    ket_qua = df.groupby("label")["do_dai"].agg(
        trung_binh="mean",
        trung_vi="median",
        ngan_nhat="min",
        dai_nhat="max"
    ).round(1)
    
    logger.info("📊 Thống kê độ dài văn bản theo nhãn:")
    logger.info(f"\n{ket_qua.to_string()}")
    
    return ket_qua


def chay_tat_ca_thong_ke(df: pd.DataFrame) -> dict:
    """
    Chạy toàn bộ phân tích thống kê và trả về kết quả.
    
    Args:
        df: DataFrame đã gán nhãn
    
    Returns:
        Dict chứa tất cả kết quả thống kê
    """
    logger.info("=" * 60)
    logger.info("▶ BẮT ĐẦU PHÂN TÍCH THỐNG KÊ")
    logger.info("=" * 60)
    
    results = {
        "phan_phoi_nhan":  thong_ke_phan_phoi_nhan(df),
        "so_sanh_sources": so_sanh_sources(df),
        "top_tu_toxic":    top_tu_toxic(df, top_n=20),
        "phan_tich_gio":   phan_tich_thoi_gian(df),
        "do_dai_van_ban":  thong_ke_do_dai(df),
    }
    
    logger.info("✓ Phân tích thống kê hoàn tất!")
    return results
