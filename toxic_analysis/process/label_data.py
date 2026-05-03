"""
label_data.py
-------------
Gán nhãn tự động cho dữ liệu bình luận tiếng Việt bằng Gemini API.

Nhãn hỗ trợ:
- CLEAN:     Bình luận bình thường, không có nội dung tiêu cực
- OFFENSIVE: Bình luận thô tục hoặc xúc phạm cá nhân
- HATE:      Bình luận thù địch, kỳ thị, kêu gọi bạo lực

Sử dụng batch processing để tiết kiệm API calls.
"""

import os
import time
import json
import logging
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
import re
import importlib.util
from tenacity import retry, wait_exponential, stop_after_attempt

# Tải biến môi trường
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
for noisy_logger in ["google_genai", "google.genai", "google", "httpx", "httpcore"]:
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

def _has_module(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


GEMINI_SDK = None
if _has_module("google.genai"):
    GEMINI_SDK = "google-genai"
elif _has_module("google.generativeai"):
    GEMINI_SDK = "google-generativeai"

GEMINI_AVAILABLE = GEMINI_SDK is not None
if not GEMINI_AVAILABLE:
    logger.warning("⚠ Chưa cài Gemini SDK. Chạy: pip install google-genai")

# Prompt mẫu để gán nhãn
SYSTEM_PROMPT = """Bạn là chuyên gia phân tích nội dung mạng xã hội tiếng Việt.
Nhiệm vụ: Phân loại từng bình luận tiếng Việt vào một trong 3 nhãn:
- CLEAN: Bình luận bình thường, lành mạnh, không có nội dung tiêu cực
- OFFENSIVE: Bình luận thô tục, chửi thề, xúc phạm cá nhân (nhưng không kêu gọi bạo lực)
- HATE: Bình luận thù địch, kỳ thị sắc tộc/giới tính/tôn giáo, kêu gọi bạo lực hoặc phân biệt đối xử

Quy tắc:
1. Chỉ trả lời bằng JSON array
2. Mỗi phần tử có dạng: {{"id": 0, "label": "NHÃN"}}
3. Không giải thích thêm
"""


def _tao_prompt_batch(comments: list[str]) -> str:
    """
    Tạo prompt gán nhãn cho một batch bình luận.
    
    Args:
        comments: Danh sách bình luận cần gán nhãn
    
    Returns:
        Chuỗi prompt hoàn chỉnh
    """
    comments_text = "\n".join(
        f'{i}. "{c}"' for i, c in enumerate(comments)
    )
    return f"""{SYSTEM_PROMPT}

Danh sách bình luận cần phân loại:
{comments_text}

Trả lời (JSON array):"""


def _parse_ket_qua_json(response_text: str, batch_size: int) -> list[str]:
    """
    Parse kết quả JSON từ Gemini thành danh sách nhãn.
    
    Args:
        response_text: Chuỗi JSON trả về từ Gemini
        batch_size: Số bình luận trong batch
    
    Returns:
        Danh sách nhãn (CLEAN/OFFENSIVE/HATE)
    """
    try:
        # Xóa các block markdown code AI có thể vô tình sinh ra
        clean_text = re.sub(r"```(?:json)?", "", response_text, flags=re.IGNORECASE).strip()
        
        # Tìm mảng JSON trong text
        start = clean_text.find("[")
        end   = clean_text.rfind("]") + 1
        if start != -1 and end > 0:
            json_str  = clean_text[start:end]
            parsed    = json.loads(json_str)
            
            # Tạo dict id → label
            label_dict = {item["id"]: item["label"].upper() for item in parsed}
            
            # Đảm bảo đủ nhãn cho batch
            labels = []
            for i in range(batch_size):
                lbl = label_dict.get(i, "LABEL_ERROR")
                # Validate nhãn
                if lbl not in ["CLEAN", "OFFENSIVE", "HATE"]:
                    lbl = "LABEL_ERROR"
                labels.append(lbl)
            return labels
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.debug(f"  Parse JSON lỗi: {e} | Response: {response_text[:200]}")
    
    # Không gán CLEAN mặc định khi parse lỗi vì sẽ làm sai dữ liệu.
    return ["LABEL_ERROR"] * batch_size


def _la_loi_quota(error_message: str) -> bool:
    """Nhận diện lỗi hết quota để dừng sớm, tránh gọi API vô ích."""
    text = error_message.lower()
    quota_markers = [
        "resource_exhausted",
        "quota exceeded",
        "too many requests",
        "exceeded your current quota",
        "generate_content_free_tier_requests",
    ]
    return any(marker in text for marker in quota_markers)


def gan_nhan_gemini(
    df: pd.DataFrame,
    text_col: str = "text",
    batch_size: int = 10,
    delay_giay: float = 1.5,
    output_path: str = "data/collected/labeled_youtube.csv",
    model_name: str = "gemini-2.5-flash",
    max_retries: int = 6,
    stop_on_quota: bool = True
) -> pd.DataFrame:
    """
    Gán nhãn tự động cho DataFrame bằng Gemini API.
    
    Args:
        df: DataFrame chứa bình luận cần gán nhãn
        text_col: Tên cột chứa văn bản
        batch_size: Số bình luận xử lý mỗi lần gọi API
        delay_giay: Thời gian chờ giữa các API call (giây)
        output_path: Đường dẫn lưu kết quả
        model_name: Tên model Gemini sử dụng
        max_retries: Số lần retry mỗi batch khi API lỗi
        stop_on_quota: Dừng ngay khi hết quota 429 để tránh chờ vô ích
    
    Returns:
        DataFrame với cột 'label' được gán nhãn
    """
    if not GEMINI_AVAILABLE:
        logger.error("✗ Gemini SDK chưa được cài đặt!")
        return df
    
    if not GEMINI_API_KEY:
        logger.error("✗ Thiếu GEMINI_API_KEY trong file .env!")
        return df
    
    if df.empty:
        logger.warning("⚠ DataFrame rỗng, không có gì để gán nhãn.")
        return df
    
    logger.info(
        f"▶ Bắt đầu gán nhãn {len(df)} bình luận bằng Gemini "
        f"(model={model_name}, batch={batch_size}, retries={max_retries})..."
    )
    
    # Khởi tạo Gemini
    try:
        if GEMINI_SDK == "google-genai":
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY)

            def _generate_content(prompt: str):
                return client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
        else:
            import google.generativeai as genai

            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(model_name)

            def _generate_content(prompt: str):
                return model.generate_content(prompt)

        logger.info("✓ Khởi tạo Gemini thành công")
    except Exception as e:
        logger.error(f"✗ Không thể khởi tạo Gemini: {e}")
        return df
    
    # Hàm gọi AI có retry chống Rate Limit (lỗi 429) và lỗi server
    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=2, min=4, max=45),
        reraise=True
    )
    def _goi_api_gemini(batch_prompt):
        return _generate_content(batch_prompt)

    # Chạy gán nhãn theo batch
    tat_ca_nhan = []
    tat_ca_loi = []
    texts = df[text_col].tolist()
    
    for i in tqdm(range(0, len(texts), batch_size), desc="  Gán nhãn Gemini"):
        batch = texts[i : i + batch_size]
        dung_vi_quota = False
        
        try:
            prompt   = _tao_prompt_batch(batch)
            response = _goi_api_gemini(prompt)
            labels   = _parse_ket_qua_json(response.text, len(batch))
            
        except Exception as e:
            error_message = str(e).replace("\n", " ")[:500]
            logger.warning(
                f"  ⚠ Lỗi batch {i//batch_size + 1}: {error_message} "
                "— đánh dấu LABEL_ERROR, không gán CLEAN mặc định"
            )
            labels = ["LABEL_ERROR"] * len(batch)
            batch_errors = [error_message] * len(batch)
            if stop_on_quota and _la_loi_quota(error_message):
                remaining = len(texts) - (i + len(batch))
                if remaining > 0:
                    logger.warning(
                        f"  ⚠ Đã hết quota Gemini, dừng gán nhãn. "
                        f"Còn {remaining} dòng được đánh dấu LABEL_ERROR để lưu cache."
                    )
                    labels.extend(["LABEL_ERROR"] * remaining)
                    batch_errors.extend(["quota_exhausted_not_called"] * remaining)
                dung_vi_quota = True
        else:
            batch_errors = ["" if lbl != "LABEL_ERROR" else "parse_error" for lbl in labels]
        
        tat_ca_nhan.extend(labels)
        tat_ca_loi.extend(batch_errors)

        if dung_vi_quota:
            break
        
        # Nghỉ giữa các batch để tránh rate limit
        if i + batch_size < len(texts):
            time.sleep(delay_giay)
    
    # Gán nhãn vào DataFrame
    df = df.copy()
    df["label"] = tat_ca_nhan
    df["label_error"] = tat_ca_loi
    df["labeled_by"] = df["label"].apply(
        lambda lbl: "Gemini_AI" if lbl in ["CLEAN", "OFFENSIVE", "HATE"] else "Gemini_AI_ERROR"
    )
    
    # Thống kê nhanh
    phan_phoi = df["label"].value_counts()
    logger.info("✓ Gán nhãn hoàn tất:")
    for lbl, cnt in phan_phoi.items():
        logger.info(f"   {lbl}: {cnt} ({cnt/len(df)*100:.1f}%)")
    if "LABEL_ERROR" in phan_phoi:
        logger.warning(
            f"⚠ Có {phan_phoi['LABEL_ERROR']} dòng lỗi Gemini. "
            "Các dòng này sẽ không được tính vào phân tích cuối."
        )
    
    # Lưu kết quả
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"✓ Đã lưu kết quả gán nhãn → {output_path}")
    
    return df


def phan_loai_va_di_chuyen(
    data_dir: str,
    platform_files: dict = None,
    labeled_file: str = "labeled_collected.csv",
    text_col: str = "text",
    batch_size: int = 25,
    delay_giay: float = 1.5,
    model_name: str = "gemini-2.5-flash",
    max_retries: int = 6,
    stop_on_quota: bool = True,
    max_label_rows: int = 0
) -> pd.DataFrame:
    """
    Quy trình phân loại tăng dần (incremental labeling):
    
    1. Đọc comment chưa phân loại từ CSV của từng nền tảng
    2. Gọi Gemini để gán nhãn
    3. Comment nào đã phân loại thành công (CLEAN/OFFENSIVE/HATE)
       → chuyển vào labeled_collected.csv chung
       → xóa khỏi CSV gốc của nền tảng
    4. Comment nào lỗi (LABEL_ERROR) → giữ nguyên trong CSV nền tảng
    
    Args:
        data_dir: Thư mục chứa các file CSV
        platform_files: Dict {platform_name: filename}, mặc định youtube + reddit
        labeled_file: Tên file CSV chứa tất cả comment đã phân loại
        text_col: Tên cột chứa văn bản
        batch_size: Số comment mỗi batch gửi Gemini
        delay_giay: Nghỉ giữa các batch (giây)
        model_name: Tên model Gemini
        max_retries: Số lần retry khi lỗi API
        stop_on_quota: Dừng khi hết quota
        max_label_rows: Giới hạn số dòng gán nhãn (0 = không giới hạn)
    
    Returns:
        DataFrame chứa TẤT CẢ comment đã phân loại (cũ + mới)
    """
    from pathlib import Path
    
    data_path = Path(data_dir)
    labeled_path = data_path / labeled_file
    
    # Mặc định các file CSV nền tảng
    if platform_files is None:
        platform_files = {
            "youtube": "youtube_comments.csv",
            "reddit": "reddit_comments.csv",
        }
    
    # ── 1. Tải dữ liệu đã phân loại trước đó (nếu có) ─────────────
    if labeled_path.exists():
        df_da_phan_loai = pd.read_csv(labeled_path, encoding="utf-8-sig")
        # Chỉ giữ những dòng có nhãn hợp lệ
        df_da_phan_loai = df_da_phan_loai[
            df_da_phan_loai["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])
        ].copy()
        logger.info(
            f"  ♻ Đã tải {len(df_da_phan_loai)} comment đã phân loại "
            f"từ {labeled_path.name}"
        )
    else:
        df_da_phan_loai = pd.DataFrame()
    
    # ── 2. Đọc comment chưa phân loại từ từng nền tảng ─────────────
    tat_ca_chua_phan_loai = []
    platform_data = {}  # Lưu lại để biết từng platform có bao nhiêu dòng
    
    for platform, filename in platform_files.items():
        csv_path = data_path / filename
        if not csv_path.exists():
            logger.info(f"  ℹ Không tìm thấy {filename}, bỏ qua nền tảng {platform}")
            continue
        
        df_platform = pd.read_csv(csv_path, encoding="utf-8-sig")
        if df_platform.empty:
            logger.info(f"  ℹ File {filename} rỗng, bỏ qua")
            continue
        
        # Đảm bảo có cột source
        if "source" not in df_platform.columns:
            df_platform["source"] = platform
        
        platform_data[platform] = {
            "path": csv_path,
            "count": len(df_platform),
        }
        tat_ca_chua_phan_loai.append(df_platform)
        logger.info(
            f"  ▶ {platform}: {len(df_platform)} comment chưa phân loại "
            f"({filename})"
        )
    
    if not tat_ca_chua_phan_loai:
        logger.info("  ℹ Không có comment chưa phân loại nào, bỏ qua gán nhãn")
        return df_da_phan_loai
    
    # Gộp tất cả comment chưa phân loại
    df_chua_phan_loai = pd.concat(tat_ca_chua_phan_loai, ignore_index=True)
    logger.info(f"  ▶ Tổng cần phân loại: {len(df_chua_phan_loai)} comment")
    
    # Giới hạn số lượng nếu cần
    if max_label_rows and max_label_rows > 0 and len(df_chua_phan_loai) > max_label_rows:
        logger.warning(
            f"  ⚠ Chỉ gán nhãn {max_label_rows}/{len(df_chua_phan_loai)} "
            "comment để kiểm soát chi phí API"
        )
        df_de_gan_nhan = df_chua_phan_loai.head(max_label_rows).copy()
    else:
        df_de_gan_nhan = df_chua_phan_loai.copy()
    
    # ── 3. Gọi Gemini để gán nhãn ─────────────────────────────────
    df_ket_qua = gan_nhan_gemini(
        df_de_gan_nhan,
        text_col=text_col,
        batch_size=batch_size,
        delay_giay=delay_giay,
        output_path=str(data_path / "_temp_label_result.csv"),
        model_name=model_name,
        max_retries=max_retries,
        stop_on_quota=stop_on_quota
    )
    
    # Xóa file tạm
    temp_path = data_path / "_temp_label_result.csv"
    if temp_path.exists():
        temp_path.unlink()
    
    # ── 4. Tách comment thành công vs thất bại ─────────────────────
    mask_thanh_cong = df_ket_qua["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])
    df_thanh_cong = df_ket_qua[mask_thanh_cong].copy()
    df_that_bai = df_ket_qua[~mask_thanh_cong].copy()
    
    logger.info(
        f"  ✓ Phân loại thành công: {len(df_thanh_cong)} comment | "
        f"Thất bại: {len(df_that_bai)} comment"
    )
    
    if df_thanh_cong.empty:
        logger.warning("  ⚠ Không có comment nào được phân loại thành công!")
        return df_da_phan_loai
    
    # ── 5. Cập nhật labeled_collected.csv (thêm comment mới) ───────
    df_da_phan_loai = pd.concat(
        [df_da_phan_loai, df_thanh_cong], ignore_index=True
    )
    # Loại trùng lặp dựa trên text + source
    df_da_phan_loai = df_da_phan_loai.drop_duplicates(
        subset=[text_col, "source"], keep="last"
    )
    df_da_phan_loai.to_csv(labeled_path, index=False, encoding="utf-8-sig")
    logger.info(
        f"  ✓ Đã lưu {len(df_da_phan_loai)} comment đã phân loại "
        f"→ {labeled_path.name}"
    )
    
    # ── 6. Xóa comment đã phân loại khỏi CSV nền tảng ─────────────
    # Tạo set các text đã phân loại thành công, theo từng source
    texts_thanh_cong_per_source = {}
    for source in df_thanh_cong["source"].unique():
        texts_thanh_cong_per_source[source] = set(
            df_thanh_cong[df_thanh_cong["source"] == source][text_col].tolist()
        )
    
    for platform, filename in platform_files.items():
        csv_path = data_path / filename
        if not csv_path.exists():
            continue
        
        texts_da_xong = texts_thanh_cong_per_source.get(platform, set())
        if not texts_da_xong:
            continue
        
        df_platform = pd.read_csv(csv_path, encoding="utf-8-sig")
        so_truoc = len(df_platform)
        
        # Xóa các comment đã phân loại thành công
        df_platform = df_platform[
            ~df_platform[text_col].isin(texts_da_xong)
        ].copy()
        so_sau = len(df_platform)
        so_da_xoa = so_truoc - so_sau
        
        if so_da_xoa > 0:
            df_platform.to_csv(csv_path, index=False, encoding="utf-8-sig")
            logger.info(
                f"  ✓ Đã xóa {so_da_xoa} comment đã phân loại khỏi "
                f"{filename} (còn lại {so_sau})"
            )
        else:
            logger.info(f"  ℹ Không có comment nào cần xóa trong {filename}")
    
    logger.info(
        f"\n  ═══ KẾT QUẢ PHÂN LOẠI TĂNG DẦN ═══\n"
        f"  Tổng đã phân loại (tích lũy) : {len(df_da_phan_loai)}\n"
        f"  Mới phân loại lần này        : {len(df_thanh_cong)}\n"
        f"  Lỗi (giữ lại trong CSV gốc)  : {len(df_that_bai)}"
    )
    
    return df_da_phan_loai


if __name__ == "__main__":
    # Test nhanh với dữ liệu mẫu
    test_df = pd.DataFrame({
        "text": [
            "video hay quá cảm ơn bạn đã chia sẻ",
            "địt con mẹ thằng đó ngu vl",
            "dân tộc này toàn loại rác rưởi",
            "tiếp tục phát huy nha team",
        ],
        "source": ["youtube"] * 4
    })
    
    result = gan_nhan_gemini(test_df, batch_size=4)
    print(result)
