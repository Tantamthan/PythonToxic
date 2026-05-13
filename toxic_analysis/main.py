"""
main.py
-------
Pipeline chính: Phân tích hành vi toxic trong bình luận mạng xã hội tiếng Việt.

Thứ tự thực thi:
  BƯỚC 1: Tổng hợp CSV đã crawl (YouTube + Reddit + Facebook + ViHSD)
  BƯỚC 2: Làm sạch dữ liệu
  BƯỚC 3: Gán nhãn tự động bằng Gemini (cho dữ liệu mạng xã hội)
  BƯỚC 4: Phân tích & thống kê
  BƯỚC 5: Trực quan hóa & xuất kết quả

Chạy: python main.py
"""

import os
import sys
import time
import json
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
from collect.vihsd_loader    import tai_vihsd
from process.clean_data      import lam_sach_dataframe
from process.label_data      import gan_nhan_gemini, phan_loai_va_di_chuyen
from analyze.statistics      import chay_tat_ca_thong_ke
from analyze.visualize       import ve_tat_ca_bieu_do
from analyze.advanced_stats     import chay_phan_tich_nang_cao
from analyze.advanced_visualize import ve_tat_ca_bieu_do_nang_cao


COLLECTED_SOURCE_FILES = {
    "youtube": "youtube_comments.csv",
    "reddit": "reddit_comments.csv",
    "facebook": "facebook_comments.csv",
}


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
║   Dataset: ViHSD + Social CSV |   Gemini AI Auto-Labeling    ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def _luu_ket_qua(df: pd.DataFrame, path: str):
    """Lưu DataFrame kết quả ra CSV (chỉ giữ text, label, source)."""
    cols = ["text", "label", "source"]
    df_out = df[[c for c in cols if c in df.columns]]
    df_out.to_csv(path, index=False, encoding="utf-8-sig")
    logger.info(f"✓ Đã lưu kết quả → {path}")


def _luu_bao_cao_tom_tat(df: pd.DataFrame, saved_charts: list[str], path: str):
    """Lưu báo cáo tóm tắt dạng JSON để dashboard/report có thể dùng lại."""
    label_counts = df["label"].value_counts().reindex(["CLEAN", "OFFENSIVE", "HATE"], fill_value=0)
    source_counts = df["source"].value_counts().to_dict() if "source" in df.columns else {}

    toxic_by_source = {}
    if "source" in df.columns:
        tmp = df.copy()
        tmp["is_toxic"] = tmp["label"].isin(["OFFENSIVE", "HATE"])
        toxic_by_source = (
            tmp.groupby("source")["is_toxic"]
            .agg(total="count", toxic="sum", toxic_rate="mean")
            .reset_index()
            .assign(toxic_rate_pct=lambda x: (x["toxic_rate"] * 100).round(2))
            .drop(columns=["toxic_rate"])
            .to_dict(orient="records")
        )

    report = {
        "total_rows": int(len(df)),
        "label_distribution": {
            label: {
                "count": int(count),
                "pct": round(float(count / len(df) * 100), 2) if len(df) else 0.0,
            }
            for label, count in label_counts.items()
        },
        "source_distribution": {str(k): int(v) for k, v in source_counts.items()},
        "toxic_by_source": toxic_by_source,
        "charts": [str(p) for p in saved_charts],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Đã lưu báo cáo tóm tắt → {path}")


# ─── BƯỚC 1: TỔNG HỢP DỮ LIỆU ĐÃ CRAWL ─────────────────────────────────────

def _doc_csv_nguon(source: str, csv_path: Path) -> pd.DataFrame:
    """Đọc một file CSV đã crawl và chuẩn hóa các cột tối thiểu."""
    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="utf-8")

    if df.empty:
        logger.info(f"  ℹ {csv_path.name} rỗng, bỏ qua")
        return df

    if "text" not in df.columns:
        logger.warning(f"  ⚠ {csv_path.name} thiếu cột text, bỏ qua")
        return pd.DataFrame()

    df = df.copy()
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 0].copy()

    if "source" not in df.columns:
        df["source"] = source
    else:
        df["source"] = df["source"].fillna(source).replace("", source)

    if "label" not in df.columns:
        df["label"] = None
    if "split" not in df.columns:
        df["split"] = "collected"
    if "published_at" not in df.columns:
        df["published_at"] = None

    logger.info(f"  ✓ {source}: {len(df)} bình luận từ {csv_path.name}")
    return df


def buoc_1_tong_hop_du_lieu(
    sources: list[str] = None,
    include_vihsd: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Tổng hợp dữ liệu đã crawl sẵn từ data/collected và tùy chọn ViHSD.

    Main.py không gọi crawler nữa. Muốn lấy dữ liệu mạng xã hội nào thì chạy
    file scraper riêng của mạng đó trước, sau đó main.py chỉ đọc CSV đã tạo.
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 1: TỔNG HỢP DỮ LIỆU ĐÃ CRAWL")
    logger.info("=" * 65)

    if sources is None:
        sources = list(COLLECTED_SOURCE_FILES.keys())

    unknown_sources = sorted(set(sources) - set(COLLECTED_SOURCE_FILES))
    if unknown_sources:
        logger.warning(f"  ⚠ Bỏ qua source chưa hỗ trợ: {', '.join(unknown_sources)}")

    tat_ca_df = []
    df_chua_nhan = pd.DataFrame()

    for source in sources:
        filename = COLLECTED_SOURCE_FILES.get(source)
        if not filename:
            continue

        csv_path = DATA_DIR / filename
        if not csv_path.exists():
            logger.info(f"  ℹ Chưa có {filename}. Hãy chạy collect/{source}_scraper.py nếu cần.")
            continue

        df_source = _doc_csv_nguon(source, csv_path)
        if df_source.empty:
            continue

        tat_ca_df.append(df_source)
        mask_chua_nhan = ~df_source["label"].isin(["CLEAN", "OFFENSIVE", "HATE"])
        df_chua_nhan = pd.concat([df_chua_nhan, df_source[mask_chua_nhan]], ignore_index=True)

    if include_vihsd:
        logger.info(f"  ▶ Tải dataset ViHSD từ: {VIHSD_DIR}")
        df_vihsd = tai_vihsd(vihsd_dir=str(VIHSD_DIR))

        if not df_vihsd.empty:
            if "published_at" not in df_vihsd.columns:
                df_vihsd["published_at"] = None
            tat_ca_df.append(df_vihsd)
            logger.info(f"  ✓ ViHSD: {len(df_vihsd)} mẫu")
        else:
            logger.warning("  ⚠ Không tải được dữ liệu ViHSD!")
    else:
        logger.info("  ℹ Bỏ qua ViHSD theo tham số --no-vihsd")

    if not tat_ca_df:
        logger.error("✗ Không có dữ liệu nào! Hãy chạy ít nhất một scraper hoặc bật ViHSD.")
        sys.exit(1)

    df_all = pd.concat(tat_ca_df, ignore_index=True)
    logger.info(f"\n  ✓ BƯỚC 1 HOÀN TẤT: Tổng {len(df_all)} mẫu")

    return df_all, df_chua_nhan


# ─── BƯỚC 2: LÀM SẠCH DỮ LIỆU ─────────────────────────────────────────────

def buoc_2_lam_sach(df: pd.DataFrame, similarity_threshold: int = 95) -> pd.DataFrame:
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
        do_dai_toi_thieu=5,
        duplicate_subset=["text", "source"],
        similarity_threshold=similarity_threshold,
        similarity_group_cols=["source"],
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
    Gán nhãn cho bình luận đã crawl bằng Gemini API.
    Sử dụng quy trình phân loại tăng dần (incremental labeling):
    
    - Comment phân loại thành công → chuyển vào labeled_collected.csv
    - Comment phân loại thành công → xóa khỏi CSV nền tảng gốc
    - Comment lỗi → giữ nguyên trong CSV nền tảng để retry lần sau
    - ViHSD đã có nhãn nên bỏ qua.
    
    Args:
        df: DataFrame tổng hợp đã làm sạch
        df_collected_raw: DataFrame dữ liệu mạng xã hội gốc (chưa có nhãn)
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
    selected_sources = set()
    if "source" in df.columns:
        selected_sources = {
            str(source)
            for source in df["source"].dropna().unique()
            if str(source) in COLLECTED_SOURCE_FILES
        }

    platform_files = {
        source: filename
        for source, filename in COLLECTED_SOURCE_FILES.items()
        if source in selected_sources
        if (DATA_DIR / filename).exists()
    }
    
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

def buoc_4_thong_ke(df: pd.DataFrame) -> tuple[dict, dict]:
    """
    Chạy toàn bộ phân tích thống kê (cơ bản + nâng cao).
    
    Args:
        df: DataFrame đầy đủ đã gán nhãn
    
    Returns:
        Tuple (stats cơ bản, stats nâng cao)
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 4: PHÂN TÍCH & THỐNG KÊ")
    logger.info("=" * 65)
    
    # 4a. Thống kê cơ bản
    stats = chay_tat_ca_thong_ke(df)
    
    # 4b. Phân tích nâng cao (N-gram, Toxic Intensity, Correlation, Topic)
    logger.info("")
    advanced_stats = chay_phan_tich_nang_cao(df)
    
    logger.info(f"✓ BƯỚC 4 HOÀN TẤT")
    return stats, advanced_stats


# ─── BƯỚC 5: TRỰC QUAN HÓA ─────────────────────────────────────────────────

def buoc_5_truc_quan(df: pd.DataFrame, stats: dict, advanced_stats: dict):
    """
    Vẽ tất cả biểu đồ (cơ bản + nâng cao) và lưu kết quả cuối cùng.
    
    Args:
        df: DataFrame đầy đủ đã gán nhãn
        stats: Dict kết quả thống kê cơ bản từ Bước 4
        advanced_stats: Dict kết quả phân tích nâng cao từ Bước 4
    """
    logger.info("=" * 65)
    logger.info("BƯỚC 5: TRỰC QUAN HÓA")
    logger.info("=" * 65)
    
    # 5a. Vẽ biểu đồ cơ bản (01 → 06)
    saved_charts = ve_tat_ca_bieu_do(
        df, stats, output_dir=str(CHARTS_DIR)
    )
    
    # 5b. Vẽ biểu đồ nâng cao (07 → 11)
    if advanced_stats:
        logger.info("")
        saved_advanced = ve_tat_ca_bieu_do_nang_cao(
            advanced_stats, output_dir=str(CHARTS_DIR)
        )
        saved_charts.extend(saved_advanced)
    
    # Lưu kết quả tổng hợp
    results_path = OUTPUT_DIR / "results.csv"
    _luu_ket_qua(df, str(results_path))

    summary_path = OUTPUT_DIR / "summary.json"
    _luu_bao_cao_tom_tat(df, saved_charts, str(summary_path))
    
    # In tóm tắt
    logger.info(f"""
╔══════════════════════════════════════════════════════════════╗
║                        KẾT QUẢ PHÂN TÍCH                    ║
╠══════════════════════════════════════════════════════════════╣
║  Tổng mẫu phân tích : {len(df):>8,d}                           ║
║  Biểu đồ đã tạo     : {len(saved_charts):>8d}                           ║
║  Kết quả CSV        : output/results.csv                     ║
║  Tóm tắt JSON       : output/summary.json                     ║
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
    logger.info(f"  Main.py mode     : Tổng hợp CSV đã crawl, không gọi scraper")
    sources = [] if args.no_collected else args.sources
    logger.info(f"  Sources          : {', '.join(sources) if sources else 'Không dùng CSV mạng xã hội'}")
    logger.info(f"  Dữ liệu ViHSD    : {'Tắt' if args.no_vihsd else 'Bật'}")
    logger.info(f"  ViHSD dir        : {VIHSD_DIR}")
    logger.info(f"  Gán nhãn Gemini  : {'Bật' if not args.no_label else 'Tắt'}")
    logger.info(f"  Gemini batch     : {args.label_batch_size}")
    logger.info(f"  Gemini delay     : {args.label_delay}s")
    logger.info(f"  Gemini max rows  : {args.max_label_rows if args.max_label_rows else 'Không giới hạn'}")
    logger.info(f"  Gemini model     : {args.gemini_model}")
    logger.info(f"  Gemini retries   : {args.label_retries}")
    logger.info(f"  Stop on quota    : {'Bật' if args.stop_on_quota else 'Tắt'}")
    logger.info(f"  Lọc trùng giống  : {args.similarity_threshold}%")
    
    # ── Bước 1: Tổng hợp CSV đã crawl ─────────────────────────────
    df_all, df_collected = buoc_1_tong_hop_du_lieu(
        sources=sources,
        include_vihsd=not args.no_vihsd,
    )
    
    # ── Bước 2: Làm sạch ──────────────────────────────────────────
    df_clean = buoc_2_lam_sach(df_all, similarity_threshold=args.similarity_threshold)
    
    # ── Bước 3: Gán nhãn ──────────────────────────────────────────
    if not args.no_label:
        phai_bo_qua_cache = args.refresh_label_cache
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
    stats, advanced_stats = buoc_4_thong_ke(df_labeled)
    
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
  python main.py                                      # Gom CSV YouTube/Reddit/Facebook + ViHSD, rồi gán nhãn Gemini
  python main.py --sources facebook                  # Chỉ gom CSV Facebook + ViHSD
  python main.py --sources youtube reddit --no-vihsd # Chỉ gom dữ liệu đã crawl từ YouTube/Reddit
  python main.py --no-collected --no-label           # Chỉ dùng ViHSD, không cần API
  python main.py --max-label-rows 100                # Giới hạn số bình luận gọi Gemini
  python main.py --similarity-threshold 95           # Lọc bình luận gần giống nhau
  python main.py --label-batch-size 5 --label-delay 8
  python main.py --refresh-label-cache               # Gán nhãn lại, bỏ cache cũ

Crawler chạy riêng:
  python collect/youtube_scraper.py
  python collect/reddit_scraper.py
  python collect/facebook_scraper.py --group-id 263510030791508
        """
    )

    parser.add_argument(
        "--sources", nargs="+", default=list(COLLECTED_SOURCE_FILES.keys()),
        choices=list(COLLECTED_SOURCE_FILES.keys()),
        help="Nguồn CSV cần gom từ data/collected (mặc định: youtube reddit facebook)"
    )
    parser.add_argument(
        "--no-vihsd", action="store_true",
        help="Bỏ qua dataset ViHSD, chỉ dùng CSV đã crawl"
    )
    parser.add_argument(
        "--no-collected", action="store_true",
        help="Bỏ qua toàn bộ CSV mạng xã hội, chỉ dùng ViHSD"
    )
    parser.add_argument(
        "--no-label", action="store_true",
        help="Bỏ qua bước gán nhãn Gemini"
    )
    parser.add_argument(
        "--similarity-threshold", type=int, default=95, dest="similarity_threshold",
        help="Ngưỡng 1-100 để loại bình luận gần giống trong cùng source; 0 là tắt (mặc định: 95)"
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
