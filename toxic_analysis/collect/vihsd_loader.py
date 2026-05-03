"""
vihsd_loader.py
---------------
Tải và chuẩn hóa dataset ViHSD (Vietnamese Hate Speech Detection).
Hỗ trợ nhiều định dạng cột khác nhau của ViHSD.
Kết hợp train/dev/test thành một DataFrame duy nhất.
"""

import os
import logging
import pandas as pd

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Ánh xạ nhãn số → chuỗi
LABEL_MAP = {
    0: "CLEAN",
    1: "OFFENSIVE",
    2: "HATE"
}

# Các tên cột có thể có trong ViHSD
POSSIBLE_TEXT_COLS  = ["free_text", "text", "comment", "sentence", "content"]
POSSIBLE_LABEL_COLS = ["label_id", "label", "Label", "class", "toxic"]


def _detect_columns(df: pd.DataFrame) -> tuple[str, str]:
    """
    Tự động phát hiện cột text và label trong DataFrame.
    
    Args:
        df: DataFrame cần phát hiện cột
    
    Returns:
        Tuple (tên_cột_text, tên_cột_label)
    
    Raises:
        ValueError: nếu không tìm thấy cột phù hợp
    """
    text_col  = next((c for c in POSSIBLE_TEXT_COLS  if c in df.columns), None)
    label_col = next((c for c in POSSIBLE_LABEL_COLS if c in df.columns), None)
    
    if text_col is None:
        raise ValueError(f"Không tìm thấy cột text. Các cột hiện có: {df.columns.tolist()}")
    if label_col is None:
        raise ValueError(f"Không tìm thấy cột label. Các cột hiện có: {df.columns.tolist()}")
    
    return text_col, label_col


def _chuan_hoa_nhan(series: pd.Series) -> pd.Series:
    """
    Chuẩn hóa nhãn về dạng chuỗi CLEAN / OFFENSIVE / HATE.
    Hỗ trợ cả nhãn số (0/1/2) và chuỗi.
    
    Args:
        series: Cột nhãn cần chuẩn hóa
    
    Returns:
        pd.Series với nhãn đã chuẩn hóa
    """
    # Nếu là số thì ánh xạ sang chuỗi
    try:
        series = series.astype(int).map(LABEL_MAP)
    except (ValueError, TypeError):
        # Đã là chuỗi, chuyển về chữ hoa
        series = series.astype(str).str.upper().str.strip()
    
    # Ánh xạ các nhãn đồng nghĩa
    alias_map = {
        "0": "CLEAN", "1": "OFFENSIVE", "2": "HATE",
        "NORMAL": "CLEAN", "NON-HATE": "CLEAN", "NONE": "CLEAN",
        "SPAM": "OFFENSIVE",
    }
    series = series.replace(alias_map)
    
    return series


def tai_vihsd(
    vihsd_dir: str = None,
    train_path: str = None,
    dev_path: str = None,
    test_path: str = None
) -> pd.DataFrame:
    """
    Tải dataset ViHSD từ các file CSV và chuẩn hóa thành DataFrame chuẩn.
    
    Args:
        vihsd_dir: Thư mục chứa train/dev/test CSV. Nếu cung cấp, sẽ tự tìm file.
        train_path: Đường dẫn trực tiếp đến train.csv (hoặc ._train.csv)
        dev_path: Đường dẫn trực tiếp đến dev.csv
        test_path: Đường dẫn trực tiếp đến test.csv
    
    Returns:
        DataFrame chuẩn với các cột: text, label, source, split
    """
    # Xác định đường dẫn các file
    if vihsd_dir:
        # Tự động tìm file trong thư mục (hỗ trợ cả dạng '._train.csv')
        def _find_file(folder, name):
            files = os.listdir(folder)
            # Ưu tiên 1: file thật (train.csv), không có tiền tố ._
            for fname in files:
                if fname.lower() == name.lower() and not fname.startswith("._"):
                    return os.path.join(folder, fname)
            # Ưu tiên 2: file có tiền tố ._ (macOS naming, nhưng vẫn có thể chứa data)
            for fname in files:
                if fname.replace("._", "").lower() == name.lower():
                    return os.path.join(folder, fname)
            return None
        
        train_path = train_path or _find_file(vihsd_dir, "train.csv")
        dev_path   = dev_path   or _find_file(vihsd_dir, "dev.csv")
        test_path  = test_path  or _find_file(vihsd_dir, "test.csv")
    
    splits = {
        "train": train_path,
        "dev":   dev_path,
        "test":  test_path
    }
    
    ket_qua = []
    
    for split_name, path in splits.items():
        if not path or not os.path.exists(path):
            logger.warning(f"  ⚠ Không tìm thấy file {split_name}: {path}")
            continue
        
        try:
            # Thử đọc với nhiều encoding
            for enc in ["utf-8", "utf-8-sig", "utf-16", "latin1"]:
                try:
                    df_split = pd.read_csv(path, encoding=enc)
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            else:
                logger.error(f"  ✗ Không thể đọc file {path}")
                continue
            
            logger.info(f"  ✓ Tải {split_name}: {len(df_split)} dòng | Cột: {df_split.columns.tolist()}")
            
            # Phát hiện cột text và label
            text_col, label_col = _detect_columns(df_split)
            
            # Tạo DataFrame chuẩn
            df_clean = pd.DataFrame({
                "text":   df_split[text_col].astype(str).str.strip(),
                "label":  _chuan_hoa_nhan(df_split[label_col]),
                "source": "vihsd",
                "split":  split_name
            })
            
            ket_qua.append(df_clean)
            
        except Exception as e:
            logger.error(f"  ✗ Lỗi khi xử lý {split_name}: {e}")
    
    if not ket_qua:
        logger.error("✗ Không tải được dữ liệu ViHSD!")
        return pd.DataFrame(columns=["text", "label", "source", "split"])
    
    # Gộp tất cả splits
    df_full = pd.concat(ket_qua, ignore_index=True)
    
    # Loại bỏ dòng rỗng
    df_full = df_full[df_full["text"].str.len() > 0]
    df_full = df_full[df_full["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])]
    
    logger.info(f"✓ Tổng ViHSD: {len(df_full)} mẫu | Phân phối nhãn:")
    for lbl, cnt in df_full["label"].value_counts().items():
        logger.info(f"   {lbl}: {cnt} ({cnt/len(df_full)*100:.1f}%)")
    
    return df_full


if __name__ == "__main__":
    # Test với thư mục vihsd — đường dẫn tương đối từ collect/
    df = tai_vihsd(vihsd_dir="../../../vihsd")
    print(df.head())
