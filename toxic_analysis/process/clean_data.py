"""
clean_data.py
-------------
Làm sạch và chuẩn hóa dữ liệu bình luận tiếng Việt.

Các bước xử lý:
1. Xóa dòng trống và trùng lặp
2. Xóa URL, email, số điện thoại
3. Xóa emoji thừa (giữ lại nếu cần phân tích cảm xúc)
4. Chuẩn hóa khoảng trắng, dấu câu
5. Xử lý viết tắt toxic tiếng Việt
6. Chuẩn hóa tiếng Việt bằng underthesea
"""

import re
import logging
import pandas as pd
from tqdm import tqdm

# Thử import underthesea (NLP tiếng Việt)
try:
    from underthesea import text_normalize
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    UNDERTHESEA_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "⚠ underthesea chưa được cài. Bỏ qua bước chuẩn hóa NLP tiếng Việt."
    )

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Từ điển viết tắt toxic phổ biến tiếng Việt
VIET_ABBREVIATIONS = {
    r"\bdcm\b": "địt con mẹ",
    r"\bđcm\b": "địt con mẹ",
    r"\bvl\b":  "vãi lờ",
    r"\bdm\b":  "địt mẹ",
    r"\bđm\b":  "địt mẹ",
    r"\bcmm\b": "cái mặt mày",
    r"\bcl\b":  "cái lờ",
    r"\bvcl\b": "vãi cái lờ",
    r"\bcc\b":  "con cặc",
    r"\bđkm\b": "địt kẹc mẹ",
    r"\bdkm\b": "địt kẹc mẹ",
    r"\bkys\b": "kill yourself",
    r"\bfck\b": "fuck",
    r"\bfk\b":  "fuck",
    r"\bwtf\b": "what the fuck",
    r"\bomg\b": "oh my god",
    r"\blol\b": "laugh out loud",
}

# Pattern regex dùng chung
PATTERN_URL     = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
PATTERN_EMAIL   = re.compile(r"\S+@\S+\.\S+")
PATTERN_PHONE   = re.compile(r"(\+84|0)\d{9,10}")
PATTERN_EMOJI   = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE
)
PATTERN_REPEAT  = re.compile(r"(.)\1{3,}")  # Ký tự lặp 4+ lần
PATTERN_SPACES  = re.compile(r"\s+")


def _mo_rong_viet_tat(text: str) -> str:
    """Thay thế viết tắt toxic tiếng Việt."""
    text_lower = text.lower()
    for pattern, replacement in VIET_ABBREVIATIONS.items():
        text_lower = re.sub(pattern, replacement, text_lower, flags=re.IGNORECASE)
    return text_lower


def lam_sach_van_ban(text: str, giu_emoji: bool = False) -> str:
    """
    Làm sạch một chuỗi văn bản tiếng Việt.
    
    Args:
        text: Văn bản cần làm sạch
        giu_emoji: Nếu True, giữ lại emoji (hữu ích cho phân tích cảm xúc)
    
    Returns:
        Văn bản đã được làm sạch
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    # Bước 1: Mở rộng viết tắt toxic
    text = _mo_rong_viet_tat(text)
    
    # Bước 2: Xóa URL, email, số điện thoại
    text = PATTERN_URL.sub(" ", text)
    text = PATTERN_EMAIL.sub(" ", text)
    text = PATTERN_PHONE.sub(" ", text)
    
    # Bước 3: Xử lý emoji
    if not giu_emoji:
        text = PATTERN_EMOJI.sub(" ", text)
    
    # Bước 4: Rút gọn ký tự lặp quá nhiều (vd: "haaahaaa" → "haaha")
    text = PATTERN_REPEAT.sub(r"\1\1", text)
    
    # Bước 5: Xóa ký tự đặc biệt (giữ lại chữ cái, số, dấu câu cơ bản)
    text = re.sub(r"[^\w\s\.,!?\-àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
                  " ", text, flags=re.IGNORECASE)
    
    # Bước 6: Chuẩn hóa khoảng trắng
    text = PATTERN_SPACES.sub(" ", text).strip()
    
    # Bước 7: Chuẩn hóa NLP tiếng Việt bằng underthesea
    if UNDERTHESEA_AVAILABLE and len(text) > 0:
        try:
            text = text_normalize(text)
        except Exception:
            pass  # Bỏ qua nếu lỗi
    
    return text


def lam_sach_dataframe(
    df: pd.DataFrame,
    text_col: str = "text",
    giu_emoji: bool = False,
    xoa_trung_lap: bool = True,
    do_dai_toi_thieu: int = 5,
    duplicate_subset: list[str] | None = None
) -> pd.DataFrame:
    """
    Làm sạch toàn bộ DataFrame bình luận.
    
    Args:
        df: DataFrame đầu vào có cột text
        text_col: Tên cột chứa văn bản
        giu_emoji: Giữ lại emoji hay không
        xoa_trung_lap: Xóa bình luận trùng lặp
        do_dai_toi_thieu: Độ dài tối thiểu của văn bản sau khi làm sạch
        duplicate_subset: Danh sách cột dùng để xác định trùng lặp.
            Nếu bỏ trống, chỉ dùng cột văn bản.
    
    Returns:
        DataFrame đã làm sạch
    """
    if df.empty:
        logger.warning("⚠ DataFrame đầu vào rỗng!")
        return df
    if text_col not in df.columns:
        raise ValueError(f"DataFrame thiếu cột văn bản bắt buộc: {text_col}")
    
    so_truoc = len(df)
    logger.info(f"▶ Bắt đầu làm sạch {so_truoc} bình luận...")
    
    # Bước 1: Xóa dòng text bị null
    df = df.dropna(subset=[text_col]).copy()
    logger.info(f"  → Sau xóa null: {len(df)} dòng")
    
    # Bước 2: Làm sạch từng văn bản (hiển thị progress bar)
    tqdm.pandas(desc="  Làm sạch văn bản")
    df.loc[:, text_col] = df[text_col].progress_apply(
        lambda x: lam_sach_van_ban(x, giu_emoji=giu_emoji)
    )
    
    # Bước 3: Xóa dòng văn bản quá ngắn sau khi làm sạch
    df = df[df[text_col].str.len() >= do_dai_toi_thieu].copy()
    logger.info(f"  → Sau lọc độ dài (≥{do_dai_toi_thieu}): {len(df)} dòng")
    
    # Bước 4: Xóa trùng lặp
    if xoa_trung_lap:
        subset = duplicate_subset or [text_col]
        subset = [c for c in subset if c in df.columns]
        if not subset:
            subset = [text_col]
        df = df.drop_duplicates(subset=subset)
        logger.info(f"  → Sau xóa trùng lặp theo {subset}: {len(df)} dòng")
    
    so_sau = len(df)
    logger.info(f"✓ Làm sạch xong: {so_truoc} → {so_sau} dòng "
                f"(đã loại {so_truoc - so_sau} dòng)")
    
    return df.reset_index(drop=True)


if __name__ == "__main__":
    # Test nhanh
    test_data = pd.DataFrame({
        "text": [
            "dcm mày nói gì vậy??? https://example.com",
            "Video hay quá! 😍😍😍",
            "vl thằng kia ngu vl",
            "",
            "bình luận bình thường hoàn toàn",
        ],
        "label":  ["OFFENSIVE", "CLEAN", "OFFENSIVE", "CLEAN", "CLEAN"],
        "source": ["youtube"] * 5,
    })
    
    df_clean = lam_sach_dataframe(test_data)
    print(df_clean)
