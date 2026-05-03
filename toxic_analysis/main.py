"""
main.py
-------
Pipeline chính: Phân tích hành vi toxic trong bình luận mạng xã hội tiếng Việt.

Thứ tự thực thi:
  BƯỚC 1: Thu thập dữ liệu (YouTube + Reddit + ViHSD)
  BƯỚC 2: Làm sạch dữ liệu
  BƯỚC 3: Gán nhãn tự động bằng Gemini (cho dữ liệu YouTube & Reddit)
  BƯỚC 4: Phân tích & thống kê
  BƯỚC 5: Trực quan hóa & xuất kết quả

Chạy: python main.py
"""

import os
import sys
import time
import logging
import argparse
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ─── CẤU HÌNH ĐƯỜNG DẪN ────────────────────────────────────────────────────
# Đảm bảo Python tìm thấy các package nội bộ
BASE_DIR   = Path(__file__).parent.resolve()
ROOT_DIR   = BASE_DIR.parent
VIHSD_DIR  = ROOT_DIR / "vihsd"
OUTPUT_DIR = BASE_DIR / "output"
CHARTS_DIR = OUTPUT_DIR / "charts"
DATA_DIR   = BASE_DIR / "data" / "collected"

# Thêm BASE_DIR vào sys.path
sys.path.insert(0, str(BASE_DIR))

# Tải biến môi trường (API keys)
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

# ─── CẤU HÌNH LOGGING ───────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE_DIR / "run.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


# ─── IMPORT CÁC MODULE NỘI BỘ ───────────────────────────────────────────────
from collect.youtube_scraper import thu_thap_youtube
from collect.reddit_scraper  import thu_thap_reddit
from collect.vihsd_loader    import tai_vihsd
from process.clean_data      import lam_sach_dataframe
from process.label_data      import gan_nhan_gemini, phan_loai_va_di_chuyen
from analyze.statistics      import chay_tat_ca_thong_ke
from analyze.visualize       import ve_tat_ca_bieu_do
from analyze.advanced_stats  import chay_phan_tich_nang_cao
from analyze.advanced_visualize import ve_tat_ca_bieu_do_nang_cao


# ─── HÀM TIỆN ÍCH ───────────────────────────────────────────────────────────

def _tao_thu_muc():
    """Tạo các thư mục cần thiết nếu chưa tồn tại."""
    for d in [OUTPUT_DIR, CHARTS_DIR, DATA_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    logger.info("✓ Đã khởi tạo cấu trúc thư mục")


def _in_banner():
    """In banner dự án."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║   PHÂN TÍCH HÀNH VI TOXIC BÌNH LUẬN MẠNG XÃ HỘI TIẾNG VIỆT ║
║   Dataset: ViHSD + YouTube   |   Gemini AI Auto-Labeling     ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def _luu_ket_qua(df: pd.DataFrame, path: str):
    """Lưu DataFrame kết quả ra CSV (chỉ giữ text, label, source)."""
    cols = ["text", "label", "source"]
    df_out = df[[c for c in cols if c in df.columns]]
    df_out.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info(f"✓ Đã lưu kết quả → {path}")


# ─── BƯỚC 1: THU THẬP DỮ LIỆU ──────────────────────────────────────────────

def buoc_1_thu_thap(
    thu_thap_youtube_flag: bool = True,
    thu_thap_reddit_flag: bool = False,
    max_youtube_per_video: int = 500,
    video_ids: list = None,
    reddit_subreddits: list = None,
    reddit_sort: str = "hot",
    reddit_max_posts: int = 50
) -> pd.DataFrame:
    """
    Thu thập dữ liệu từ YouTube, Reddit và tải ViHSD.
    
    Args:
        thu_thap_youtube_flag: Có thu thập YouTube hay không
        thu_thap_reddit_flag: Có thu thập Reddit hay không
        max_youtube_per_video: Số bình luận tối đa mỗi video
        video_ids: Danh sách ID video tùy chỉnh
        reddit_subreddits: Danh sách subreddit tùy chỉnh
        reddit_sort: Cách sắp xếp bài Reddit (hot/new/top/controversial)
        reddit_max_posts: Số bài viết tối đa mỗi subreddit
    
    Returns:
        Tuple (DataFrame tổng hợp, DataFrame dữ liệu chưa gán nhãn)
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 1: THU THẬP DỮ LIỆU")
    logger.info("=" * 65)
    
    tat_ca_df = []
    df_chua_nhan = pd.DataFrame()  # Tổng hợp YouTube + Reddit (chưa có nhãn)
    
    # ── 1a. Thu thập YouTube ──────────────────────────────────────
    if thu_thap_youtube_flag:
        youtube_cache = DATA_DIR / "youtube_comments.csv"
        
        if youtube_cache.exists() and not video_ids:
            logger.info(f"  ♻ Tìm thấy cache YouTube: {youtube_cache}")
            df_youtube = pd.read_csv(youtube_cache, encoding="utf-8-sig")
            logger.info(f"  ✓ Tải từ cache: {len(df_youtube)} bình luận")
        else:
            logger.info("  ▶ Thu thập bình luận YouTube mới...")
            if video_ids:
                logger.info(f"  (Bỏ qua cache vì bạn đang thu thập video ID tùy chỉnh: {video_ids})")
            
            df_youtube = thu_thap_youtube(
                video_ids=video_ids,
                max_per_video=max_youtube_per_video,
                output_path=str(youtube_cache)
            )
        
        if not df_youtube.empty:
            df_youtube["label"]  = None
            df_youtube["source"] = "youtube"
            df_youtube["split"]  = "collected"
            tat_ca_df.append(df_youtube)
            df_chua_nhan = pd.concat([df_chua_nhan, df_youtube], ignore_index=True)
            logger.info(f"  ✓ YouTube: {len(df_youtube)} bình luận")
    
    # ── 1b. Thu thập Reddit ───────────────────────────────────────
    if thu_thap_reddit_flag:
        reddit_cache = DATA_DIR / "reddit_comments.csv"
        
        if reddit_cache.exists() and not reddit_subreddits:
            logger.info(f"  ♻ Tìm thấy cache Reddit: {reddit_cache}")
            df_reddit = pd.read_csv(reddit_cache, encoding="utf-8-sig")
            logger.info(f"  ✓ Tải từ cache: {len(df_reddit)} bình luận")
        else:
            logger.info("  ▶ Thu thập bình luận Reddit mới...")
            df_reddit = thu_thap_reddit(
                subreddits=reddit_subreddits,
                sort_by=reddit_sort,
                max_posts_per_sub=reddit_max_posts,
                output_path=str(reddit_cache)
            )
        
        if not df_reddit.empty:
            df_reddit["label"] = None
            if "source" not in df_reddit.columns:
                df_reddit["source"] = "reddit"
            df_reddit["split"] = "collected"
            tat_ca_df.append(df_reddit)
            df_chua_nhan = pd.concat([df_chua_nhan, df_reddit], ignore_index=True)
            logger.info(f"  ✓ Reddit: {len(df_reddit)} bình luận")
    
    # ── 1c. Tải ViHSD ─────────────────────────────────────────────
    logger.info(f"  ▶ Tải dataset ViHSD từ: {VIHSD_DIR}")
    df_vihsd = tai_vihsd(vihsd_dir=str(VIHSD_DIR))
    
    if not df_vihsd.empty:
        if "published_at" not in df_vihsd.columns:
            df_vihsd["published_at"] = None
        tat_ca_df.append(df_vihsd)
        logger.info(f"  ✓ ViHSD: {len(df_vihsd)} mẫu")
    else:
        logger.warning("  ⚠ Không tải được dữ liệu ViHSD!")
    
    if not tat_ca_df:
        logger.error("✗ Không có dữ liệu nào! Pipeline dừng lại.")
        sys.exit(1)
    
    # Gộp tất cả
    df_all = pd.concat(tat_ca_df, ignore_index=True)
    logger.info(f"\n  ✓ BƯỚC 1 HOÀN TẤT: Tổng {len(df_all)} mẫu")
    
    return df_all, df_chua_nhan


# ─── BƯỚC 2: LÀM SẠCH DỮ LIỆU ─────────────────────────────────────────────

def buoc_2_lam_sach(df: pd.DataFrame) -> pd.DataFrame:
    """
    Làm sạch toàn bộ dữ liệu bình luận.
    
    Args:
        df: DataFrame tổng hợp từ Bước 1
    
    Returns:
        DataFrame đã làm sạch
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 2: LÀM SẠCH DỮ LIỆU")
    logger.info("=" * 65)
    
    df_clean = lam_sach_dataframe(
        df,
        text_col="text",
        giu_emoji=False,
        xoa_trung_lap=True,
        do_dai_toi_thieu=5
    )
    
    logger.info(f"✓ BƯỚC 2 HOÀN TẤT: {len(df_clean)} mẫu sau làm sạch")
    return df_clean


# ─── BƯỚC 3: GÁN NHÃN TỰ ĐỘNG ─────────────────────────────────────────────

def buoc_3_gan_nhan(
    df: pd.DataFrame,
    df_collected_raw: pd.DataFrame,
    skip_cache: bool = False,
    label_batch_size: int = 25,
    label_delay: float = 1.5,
    max_label_rows: int = 0,
    gemini_model: str = "gemini-2.5-flash",
    label_retries: int = 6,
    stop_on_quota: bool = True
) -> pd.DataFrame:
    """
    Gán nhãn cho bình luận YouTube & Reddit bằng Gemini API.
    Sử dụng quy trình phân loại tăng dần (incremental labeling):
    
    - Comment phân loại thành công → chuyển vào labeled_collected.csv
    - Comment phân loại thành công → xóa khỏi CSV nền tảng gốc
    - Comment lỗi → giữ nguyên trong CSV nền tảng để retry lần sau
    - ViHSD đã có nhãn nên bỏ qua.
    
    Args:
        df: DataFrame tổng hợp đã làm sạch
        df_collected_raw: DataFrame YouTube+Reddit gốc (chưa có nhãn)
        skip_cache: Nếu True, sẽ tiến hành gọi API dù đã có file cache.
    
    Returns:
        DataFrame đầy đủ với nhãn
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 3: GÁN NHÃN TỰ ĐỘNG BẰNG GEMINI (INCREMENTAL)")
    logger.info("=" * 65)
    
    # Tách phần đã có nhãn (ViHSD) — luôn giữ nguyên
    df_co_nhan = df[df["label"].notna() & df["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])].copy()
    
    # Kiểm tra xem có comment chưa phân loại trong CSV nền tảng không
    platform_files = {}
    if (DATA_DIR / "youtube_comments.csv").exists():
        platform_files["youtube"] = "youtube_comments.csv"
    if (DATA_DIR / "reddit_comments.csv").exists():
        platform_files["reddit"] = "reddit_comments.csv"
    
    if not platform_files:
        logger.info("  ℹ Không tìm thấy CSV nền tảng nào, kiểm tra cache...")
        # Fallback: tải từ labeled_collected.csv nếu có
        labeled_cache = DATA_DIR / "labeled_collected.csv"
        if labeled_cache.exists():
            df_labeled = pd.read_csv(labeled_cache, encoding="utf-8-sig")
            df_labeled = df_labeled[
                df_labeled["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])
            ]
            df_full = pd.concat([df_co_nhan, df_labeled], ignore_index=True)
            df_full = df_full.drop_duplicates(subset=["text", "source"], keep="last")
            logger.info(f"✓ BƯỚC 3 HOÀN TẤT: {len(df_full)} mẫu đã có nhãn")
            return df_full
        logger.info("  ℹ Tất cả dữ liệu đã có nhãn, bỏ qua bước gán nhãn Gemini")
        return df_co_nhan
    
    if not skip_cache:
        # Kiểm tra xem tất cả CSV nền tảng có rỗng không
        co_du_lieu_moi = False
        for filename in platform_files.values():
            p = DATA_DIR / filename
            if p.exists():
                try:
                    tmp = pd.read_csv(p, encoding="utf-8-sig")
                    if not tmp.empty:
                        co_du_lieu_moi = True
                        break
                except Exception:
                    pass
        
        if not co_du_lieu_moi:
            logger.info("  ℹ CSV nền tảng rỗng, tải từ labeled_collected.csv...")
            labeled_cache = DATA_DIR / "labeled_collected.csv"
            if labeled_cache.exists():
                df_labeled = pd.read_csv(labeled_cache, encoding="utf-8-sig")
                df_labeled = df_labeled[
                    df_labeled["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])
                ]
                df_full = pd.concat([df_co_nhan, df_labeled], ignore_index=True)
                df_full = df_full.drop_duplicates(subset=["text", "source"], keep="last")
                logger.info(f"✓ BƯỚC 3 HOÀN TẤT: {len(df_full)} mẫu đã có nhãn")
                return df_full
    
    # ── Gọi phân loại tăng dần ──────────────────────────────────────
    logger.info("  ▶ Bắt đầu phân loại tăng dần (incremental labeling)...")
    
    df_labeled_collected = phan_loai_va_di_chuyen(
        data_dir=str(DATA_DIR),
        platform_files=platform_files,
        labeled_file="labeled_collected.csv",
        text_col="text",
        batch_size=label_batch_size,
        delay_giay=label_delay,
        model_name=gemini_model,
        max_retries=label_retries,
        stop_on_quota=stop_on_quota,
        max_label_rows=max_label_rows
    )
    
    # Gộp ViHSD (đã có nhãn) với dữ liệu vừa phân loại
    df_full = pd.concat([df_co_nhan, df_labeled_collected], ignore_index=True)
    df_full = df_full.drop_duplicates(subset=["text", "source"], keep="last")
    
    # Đảm bảo chỉ giữ nhãn hợp lệ
    df_full = df_full[df_full["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])]
    
    logger.info(f"✓ BƯỚC 3 HOÀN TẤT: {len(df_full)} mẫu đã có nhãn")
    return df_full


# ─── BƯỚC 4: PHÂN TÍCH THỐNG KÊ ────────────────────────────────────────────

def buoc_4_thong_ke(df: pd.DataFrame) -> dict:
    """
    Chạy toàn bộ phân tích thống kê.
    
    Args:
        df: DataFrame đầy đủ đã gán nhãn
    
    Returns:
        Dict chứa kết quả thống kê
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 4: PHÂN TÍCH & THỐNG KÊ")
    logger.info("=" * 65)
    
    stats = chay_tat_ca_thong_ke(df)
    
    logger.info(f"✓ BƯỚC 4 HOÀN TẤT")
    return stats


# ─── BƯỚC 4.5: PHÂN TÍCH NÂNG CAO ───────────────────────────────────────────

def buoc_4_5_phan_tich_nang_cao(df: pd.DataFrame) -> dict:
    """
    Chạy phân tích nâng cao: N-gram, Sentiment Intensity, Correlation, Topic Modeling.
    
    Args:
        df: DataFrame đầy đủ đã gán nhãn
    
    Returns:
        Dict chứa kết quả phân tích nâng cao
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 4.5: PHÂN TÍCH NÂNG CAO")
    logger.info("=" * 65)
    
    advanced_stats = chay_phan_tich_nang_cao(df)
    
    logger.info(f"✓ BƯỚC 4.5 HOÀN TẤT")
    return advanced_stats


# ─── BƯỚC 5: TRỰC QUAN HÓA ─────────────────────────────────────────────────

def buoc_5_truc_quan(df: pd.DataFrame, stats: dict, advanced_stats: dict):
    """
    Vẽ tất cả biểu đồ và lưu kết quả cuối cùng.
    
    Args:
        df: DataFrame đầy đủ đã gán nhãn
        stats: Dict kết quả thống kê từ Bước 4
        advanced_stats: Dict kết quả phân tích nâng cao từ Bước 4.5
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 5: TRỰC QUAN HÓA")
    logger.info("=" * 65)
    
    # Vẽ biểu đồ cơ bản
    saved_charts = ve_tat_ca_bieu_do(
        df, stats, output_dir=str(CHARTS_DIR)
    )
    
    # Vẽ biểu đồ nâng cao
    saved_advanced = ve_tat_ca_bieu_do_nang_cao(
        advanced_stats, output_dir=str(CHARTS_DIR)
    )
    saved_charts.extend(saved_advanced)
    
    # Lưu kết quả tổng hợp
    results_path = OUTPUT_DIR / "results.csv"
    _luu_ket_qua(df, str(results_path))
    
    # Lưu kết quả phân tích nâng cao
    if "df_with_intensity" in advanced_stats:
        advanced_path = OUTPUT_DIR / "results_advanced.csv"
        df_advanced = advanced_stats["df_with_intensity"]
        cols_to_save = ["text", "label", "source", "toxic_score", "toxic_level"]
        df_out = df_advanced[[c for c in cols_to_save if c in df_advanced.columns]]
        df_out.to_csv(advanced_path, index=False, encoding="utf-8-sig")
        logger.info(f"✓ Đã lưu kết quả nâng cao → {advanced_path}")
    
    # In tóm tắt
    logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║                        KẾT QUẢ PHÂN TÍCH                    ║
╠══════════════════════════════════════════════════════════════╣
║  Tổng mẫu phân tích : {len(df):>8,d}                           ║
║  Biểu đồ cơ bản     : {len(saved_charts) - len(saved_advanced):>8d}                           ║
║  Biểu đồ nâng cao   : {len(saved_advanced):>8d}                           ║
║  Tổng biểu đồ       : {len(saved_charts):>8d}                           ║
║  Kết quả CSV        : output/results.csv                     ║
║  Kết quả nâng cao   : output/results_advanced.csv            ║
║  Biểu đồ            : output/charts/                         ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    logger.info("✓ BƯỚC 5 HOÀN TẤT")


# ─── PIPELINE CHÍNH ─────────────────────────────────────────────────────────

def chay_pipeline(args):
    """
    Chạy toàn bộ pipeline từ thu thập đến trực quan hóa.
    
    Args:
        args: Namespace từ argparse
    """
    thoi_gian_bat_dau = time.time()
    
    _in_banner()
    _tao_thu_muc()
    
    logger.info(f"Cấu hình:")
    logger.info(f"  Thu thập YouTube : {'Bật' if not args.no_youtube else 'Tắt'}")
    logger.info(f"  Thu thập Reddit  : {'Bật' if args.reddit else 'Tắt'}")
    logger.info(f"  Max/video        : {args.max_per_video}")
    logger.info(f"  ViHSD dir        : {VIHSD_DIR}")
    logger.info(f"  Gán nhãn Gemini  : {'Bật' if not args.no_label else 'Tắt'}")
    logger.info(f"  Gemini batch     : {args.label_batch_size}")
    logger.info(f"  Gemini delay     : {args.label_delay}s")
    logger.info(f"  Gemini max rows  : {args.max_label_rows if args.max_label_rows else 'Không giới hạn'}")
    logger.info(f"  Gemini model     : {args.gemini_model}")
    logger.info(f"  Gemini retries   : {args.label_retries}")
    logger.info(f"  Stop on quota    : {'Bật' if args.stop_on_quota else 'Tắt'}")
    
    # ── Bước 1: Thu thập ──────────────────────────────────────────
    df_all, df_collected = buoc_1_thu_thap(
        thu_thap_youtube_flag=not args.no_youtube,
        thu_thap_reddit_flag=args.reddit,
        max_youtube_per_video=args.max_per_video,
        video_ids=args.video_ids if args.video_ids else None,
        reddit_subreddits=args.reddit_subs if args.reddit_subs else None,
        reddit_sort=args.reddit_sort,
        reddit_max_posts=args.reddit_max_posts
    )
    
    # ── Bước 2: Làm sạch ──────────────────────────────────────────
    df_clean = buoc_2_lam_sach(df_all)
    
    # ── Bước 3: Gán nhãn ──────────────────────────────────────────
    if not args.no_label:
        # Bỏ qua cache nhãn nếu người dùng dùng video/subreddit tùy chỉnh
        phai_bo_qua_cache = (
            (args.video_ids is not None)
            or (args.reddit_subs is not None)
            or args.refresh_label_cache
        )
        df_labeled = buoc_3_gan_nhan(
            df_clean,
            df_collected,
            skip_cache=phai_bo_qua_cache,
            label_batch_size=args.label_batch_size,
            label_delay=args.label_delay,
            max_label_rows=args.max_label_rows,
            gemini_model=args.gemini_model,
            label_retries=args.label_retries,
            stop_on_quota=args.stop_on_quota
        )
    else:
        # Bỏ qua gán nhãn, loại bỏ dòng chưa có nhãn
        df_labeled = df_clean[df_clean["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])]
        logger.info("  ℹ Bỏ qua gán nhãn Gemini theo yêu cầu")
    
    if df_labeled.empty:
        logger.error("✗ Không có dữ liệu sau khi gán nhãn!")
        sys.exit(1)
    
    # ── Bước 4: Thống kê ──────────────────────────────────────────
    stats = buoc_4_thong_ke(df_labeled)
    
    # ── Bước 4.5: Phân tích nâng cao ──────────────────────────────
    advanced_stats = buoc_4_5_phan_tich_nang_cao(df_labeled)
    
    # ── Bước 5: Trực quan hóa ─────────────────────────────────────
    buoc_5_truc_quan(df_labeled, stats, advanced_stats)
    
    # Thời gian thực thi
    elapsed = time.time() - thoi_gian_bat_dau
    logger.info(f"\n⏱ Thời gian chạy: {elapsed:.1f}s ({elapsed/60:.1f} phút)")
    logger.info("🎉 PIPELINE HOÀN TẤT!")


# ─── ENTRY POINT ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Phân tích Toxic trong bình luận tiếng Việt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python main.py                              # Chạy YouTube + ViHSD
  python main.py --reddit                      # Thêm thu thập Reddit
  python main.py --reddit --no-youtube         # Chỉ Reddit + ViHSD
  python main.py --no-youtube --no-label       # Chỉ dùng ViHSD
  python main.py --max-per-video 200           # Giới hạn 200 bình luận/video
  python main.py --max-label-rows 100          # Giới hạn số bình luận gọi Gemini
  python main.py --label-batch-size 5 --label-delay 8
  python main.py --refresh-label-cache         # Gán nhãn lại, bỏ cache cũ
  python main.py --video-ids abc123 def456     # Chỉ định video cụ thể
  python main.py --reddit --reddit-subs VietNam TroChuyenLinhTinh
        """
    )
    
    parser.add_argument(
        "--no-youtube", action="store_true",
        help="Bỏ qua bước thu thập YouTube"
    )
    parser.add_argument(
        "--reddit", action="store_true",
        help="Bật thu thập bình luận từ Reddit"
    )
    parser.add_argument(
        "--no-label", action="store_true",
        help="Bỏ qua bước gán nhãn Gemini"
    )
    parser.add_argument(
        "--max-per-video", type=int, default=500, dest="max_per_video",
        help="Số bình luận tối đa mỗi video YouTube (mặc định: 500)"
    )
    parser.add_argument(
        "--video-ids", nargs="+", dest="video_ids",
        help="Danh sách YouTube video ID tùy chỉnh"
    )
    parser.add_argument(
        "--reddit-subs", nargs="+", dest="reddit_subs",
        help="Danh sách subreddit tùy chỉnh (mặc định: Vietnam VietNam TroChuyenLinhTinh)"
    )
    parser.add_argument(
        "--reddit-sort", default="hot", dest="reddit_sort",
        choices=["hot", "new", "top", "controversial"],
        help="Cách sắp xếp bài viết Reddit (mặc định: hot)"
    )
    parser.add_argument(
        "--reddit-max-posts", type=int, default=50, dest="reddit_max_posts",
        help="Số bài viết tối đa mỗi subreddit (mặc định: 50)"
    )
    parser.add_argument(
        "--label-batch-size", type=int, default=25, dest="label_batch_size",
        help="Số bình luận mỗi batch gửi Gemini (mặc định: 25)"
    )
    parser.add_argument(
        "--label-delay", type=float, default=1.5, dest="label_delay",
        help="Số giây nghỉ giữa các lần gọi Gemini (mặc định: 1.5)"
    )
    parser.add_argument(
        "--max-label-rows", type=int, default=0, dest="max_label_rows",
        help="Giới hạn số bình luận gọi Gemini; 0 là không giới hạn"
    )
    parser.add_argument(
        "--gemini-model", default=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        dest="gemini_model",
        help="Tên model Gemini dùng để gán nhãn (mặc định: gemini-2.5-flash)"
    )
    parser.add_argument(
        "--label-retries", type=int, default=6, dest="label_retries",
        help="Số lần retry mỗi batch Gemini khi lỗi 429/503 (mặc định: 6)"
    )
    parser.add_argument(
        "--continue-on-quota", action="store_false", dest="stop_on_quota",
        help="Tiếp tục chạy các batch sau dù Gemini báo hết quota"
    )
    parser.add_argument(
        "--refresh-label-cache", action="store_true", dest="refresh_label_cache",
        help="Bỏ cache gán nhãn cũ và gọi Gemini lại"
    )
    
    args = parser.parse_args()
    
    try:
        chay_pipeline(args)
    except KeyboardInterrupt:
        logger.info("\n⚠ Người dùng đã dừng pipeline.")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"✗ Lỗi không xử lý được: {e}")
        sys.exit(1)
