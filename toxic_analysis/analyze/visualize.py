"""
visualize.py
------------
Trực quan hóa kết quả phân tích toxic bình luận tiếng Việt.

Các biểu đồ được tạo:
1. Biểu đồ cột: Phân phối nhãn CLEAN / OFFENSIVE / HATE
2. Biểu đồ tròn: Tỷ lệ toxic vs clean
3. Biểu đồ cột ngang: Top 20 từ toxic phổ biến nhất
4. WordCloud riêng cho HATE, OFFENSIVE, CLEAN
5. Biểu đồ đường: Tỷ lệ toxic theo giờ trong ngày
6. Biểu đồ nhóm: So sánh toxic theo nguồn dữ liệu

Tất cả biểu đồ được lưu vào thư mục output/charts/
"""

import os
import logging
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# Tắt cảnh báo không cần thiết
warnings.filterwarnings("ignore")
matplotlib.use("Agg")  # Non-interactive backend (không cần display)

# Thử import WordCloud
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except ImportError:
    WORDCLOUD_AVAILABLE = False

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── CẤU HÌNH THIẾT KẾ ─────────────────────────────────────────────────────

# Bảng màu cho từng nhãn
COLORS = {
    "CLEAN":     "#2ECC71",   # Xanh lá sáng
    "OFFENSIVE": "#F39C12",   # Cam
    "HATE":      "#E74C3C",   # Đỏ
}

# Style seaborn
sns.set_theme(style="darkgrid", palette="muted")

# Font chữ hỗ trợ tiếng Việt (dùng DejaVu Sans mặc định nếu không có font riêng)
plt.rcParams.update({
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor":   "#16213e",
    "axes.labelcolor":  "#eaeaea",
    "axes.titlecolor":  "#ffffff",
    "xtick.color":      "#eaeaea",
    "ytick.color":      "#eaeaea",
    "grid.color":       "#2d3561",
    "text.color":       "#ffffff",
    "figure.dpi":       120,
    "font.size":        11,
})

OUTPUT_DIR = "output/charts"


def _setup_output_dir(output_dir: str = OUTPUT_DIR):
    """Tạo thư mục output nếu chưa tồn tại."""
    os.makedirs(output_dir, exist_ok=True)


def _save_fig(fig: plt.Figure, filename: str, output_dir: str = OUTPUT_DIR):
    """Lưu figure và đóng để giải phóng bộ nhớ."""
    path = os.path.join(output_dir, filename)
    fig.savefig(path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info(f"  ✓ Đã lưu: {path}")
    return path


# ─── BIỂU ĐỒ 1: PHÂN PHỐI NHÃN ────────────────────────────────────────────

def ve_phan_phoi_nhan(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ cột phân phối nhãn CLEAN / OFFENSIVE / HATE.
    
    Args:
        df: DataFrame với cột 'label'
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file biểu đồ
    """
    _setup_output_dir(output_dir)
    counts = df["label"].value_counts().reindex(["CLEAN", "OFFENSIVE", "HATE"], fill_value=0)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    bars = ax.bar(
        counts.index,
        counts.values,
        color=[COLORS[l] for l in counts.index],
        width=0.6,
        edgecolor="#ffffff",
        linewidth=0.5,
        alpha=0.9
    )
    
    # Thêm số liệu lên đỉnh cột
    for bar, val in zip(bars, counts.values):
        pct = val / counts.sum() * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + counts.max() * 0.01,
            f"{val:,}\n({pct:.1f}%)",
            ha="center", va="bottom",
            fontsize=12, fontweight="bold", color="#ffffff"
        )
    
    ax.set_title("Phân phối nhãn bình luận\nCLEAN / OFFENSIVE / HATE", fontsize=16, pad=20)
    ax.set_xlabel("Nhãn", fontsize=13)
    ax.set_ylabel("Số lượng bình luận", fontsize=13)
    ax.set_ylim(0, counts.max() * 1.2)
    
    fig.tight_layout()
    return _save_fig(fig, "01_phan_phoi_nhan.png", output_dir)


# ─── BIỂU ĐỒ 2: TỶ LỆ TOXIC VS CLEAN ──────────────────────────────────────

def ve_bieu_do_tron(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ tròn tỷ lệ toxic vs clean.
    
    Args:
        df: DataFrame với cột 'label'
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file biểu đồ
    """
    _setup_output_dir(output_dir)
    
    # Nhóm: TOXIC = OFFENSIVE + HATE, CLEAN = CLEAN
    toxic_count = (df["label"].isin(["OFFENSIVE", "HATE"])).sum()
    clean_count = (df["label"] == "CLEAN").sum()
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    
    # --- Subplot trái: Toxic vs Clean ---
    sizes1  = [clean_count, toxic_count]
    labels1 = [f"CLEAN\n{clean_count:,}", f"TOXIC\n{toxic_count:,}"]
    colors1 = ["#2ECC71", "#E74C3C"]
    explode = (0, 0.05)
    
    axes[0].pie(
        sizes1, labels=labels1, colors=colors1, explode=explode,
        autopct="%1.1f%%", startangle=90,
        textprops={"fontsize": 13, "color": "white"},
        wedgeprops={"linewidth": 2, "edgecolor": "#1a1a2e"}
    )
    axes[0].set_title("Tỷ lệ Toxic vs Clean", fontsize=14)
    
    # --- Subplot phải: Chi tiết 3 nhãn ---
    counts   = df["label"].value_counts().reindex(["CLEAN", "OFFENSIVE", "HATE"], fill_value=0)
    sizes2   = counts.values
    labels2  = [f"{l}\n{v:,}" for l, v in zip(counts.index, sizes2)]
    colors2  = [COLORS[l] for l in counts.index]
    explode2 = [0, 0.05, 0.1]
    
    axes[1].pie(
        sizes2, labels=labels2, colors=colors2, explode=explode2,
        autopct="%1.1f%%", startangle=140,
        textprops={"fontsize": 12, "color": "white"},
        wedgeprops={"linewidth": 2, "edgecolor": "#1a1a2e"}
    )
    axes[1].set_title("Phân phối 3 nhãn chi tiết", fontsize=14)
    
    fig.suptitle("Phân tích tỷ lệ Toxic trong bình luận tiếng Việt", fontsize=16, y=1.02)
    fig.tight_layout()
    return _save_fig(fig, "02_ty_le_toxic.png", output_dir)


# ─── BIỂU ĐỒ 3: TOP TỪ TOXIC ───────────────────────────────────────────────

def ve_top_tu_toxic(df_top_words: pd.DataFrame, top_n: int = 20, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ cột ngang Top N từ toxic phổ biến nhất.
    
    Args:
        df_top_words: DataFrame với cột 'word' và 'count'
        top_n: Số từ hiển thị
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file biểu đồ
    """
    if df_top_words.empty:
        logger.warning("⚠ Không có dữ liệu top từ để vẽ")
        return ""
    
    _setup_output_dir(output_dir)
    df_plot = df_top_words.head(top_n).sort_values("count", ascending=True)
    
    fig, ax = plt.subplots(figsize=(12, 9))
    
    # Gradient màu từ cam đến đỏ
    n = len(df_plot)
    colors = plt.cm.YlOrRd(np.linspace(0.4, 0.9, n))
    
    bars = ax.barh(df_plot["word"], df_plot["count"], color=colors, edgecolor="white", linewidth=0.3)
    
    # Thêm số lượng vào cuối thanh
    for bar, val in zip(bars, df_plot["count"]):
        ax.text(
            bar.get_width() + df_plot["count"].max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", fontsize=10, color="#eaeaea"
        )
    
    ax.set_title(f"Top {top_n} từ phổ biến nhất trong bình luận OFFENSIVE & HATE", fontsize=14, pad=15)
    ax.set_xlabel("Tần suất xuất hiện", fontsize=12)
    ax.set_ylabel("Từ", fontsize=12)
    ax.set_xlim(0, df_plot["count"].max() * 1.15)
    
    fig.tight_layout()
    return _save_fig(fig, "03_top_tu_toxic.png", output_dir)


# ─── BIỂU ĐỒ 4: WORDCLOUD ───────────────────────────────────────────────────

def ve_wordcloud(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> list[str]:
    """
    Vẽ WordCloud riêng cho mỗi nhãn: HATE, OFFENSIVE, CLEAN.
    
    Args:
        df: DataFrame với cột 'text' và 'label'
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Danh sách đường dẫn file biểu đồ
    """
    if not WORDCLOUD_AVAILABLE:
        logger.warning("⚠ wordcloud chưa được cài. Bỏ qua bước WordCloud.")
        return []
    
    _setup_output_dir(output_dir)
    
    # Cấu hình nền + màu cho từng nhãn
    wordcloud_configs = {
        "HATE":      {"background_color": "#1a0000", "colormap": "Reds"},
        "OFFENSIVE": {"background_color": "#1a1200", "colormap": "YlOrRd"},
        "CLEAN":     {"background_color": "#001a0a", "colormap": "Greens"},
    }
    
    saved_paths = []
    
    for nhan, config in wordcloud_configs.items():
        df_nhan = df[df["label"] == nhan]
        
        if df_nhan.empty:
            logger.warning(f"  ⚠ Không có dữ liệu nhãn {nhan} để vẽ WordCloud")
            continue
        
        # Gộp tất cả văn bản
        all_text = " ".join(df_nhan["text"].dropna().astype(str))
        
        if len(all_text.strip()) < 10:
            logger.warning(f"  ⚠ Văn bản {nhan} quá ngắn để tạo WordCloud")
            continue
        
        try:
            wc = WordCloud(
                width=1200, height=600,
                background_color=config["background_color"],
                colormap=config["colormap"],
                max_words=150,
                min_font_size=10,
                max_font_size=100,
                prefer_horizontal=0.8,
                collocations=False,
            ).generate(all_text)
            
            fig, ax = plt.subplots(figsize=(14, 7))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            ax.set_title(f"WordCloud - Bình luận {nhan}", fontsize=18, pad=15,
                        color={"HATE": "#ff6b6b", "OFFENSIVE": "#ffd700", "CLEAN": "#69ff69"}[nhan])
            
            path = _save_fig(fig, f"04_wordcloud_{nhan.lower()}.png", output_dir)
            saved_paths.append(path)
            
        except Exception as e:
            logger.error(f"  ✗ Lỗi tạo WordCloud {nhan}: {e}")
    
    return saved_paths


# ─── BIỂU ĐỒ 5: TOXIC THEO THỜI GIAN ───────────────────────────────────────

def ve_toxic_theo_gio(df_theo_gio: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ đường tỷ lệ toxic theo giờ trong ngày.
    
    Args:
        df_theo_gio: DataFrame từ analyze/statistics.phan_tich_thoi_gian()
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file biểu đồ
    """
    if df_theo_gio is None or df_theo_gio.empty:
        logger.info("ℹ Bỏ qua biểu đồ thời gian (không có dữ liệu)")
        return ""
    
    _setup_output_dir(output_dir)
    
    fig, ax1 = plt.subplots(figsize=(14, 6))
    
    # Đường tỷ lệ toxic
    ax1.plot(df_theo_gio["hour"], df_theo_gio["ty_le_toxic"],
             color="#E74C3C", linewidth=2.5, marker="o", markersize=7, label="Tỷ lệ toxic (%)")
    ax1.fill_between(df_theo_gio["hour"], df_theo_gio["ty_le_toxic"],
                     alpha=0.2, color="#E74C3C")
    ax1.set_ylabel("Tỷ lệ toxic (%)", color="#E74C3C", fontsize=12)
    ax1.tick_params(axis="y", labelcolor="#E74C3C")
    
    # Cột số bình luận (trục y phụ)
    ax2 = ax1.twinx()
    ax2.bar(df_theo_gio["hour"], df_theo_gio["tong_binh_luan"],
            alpha=0.25, color="#3498DB", label="Tổng bình luận")
    ax2.set_ylabel("Số lượng bình luận", color="#3498DB", fontsize=12)
    ax2.tick_params(axis="y", labelcolor="#3498DB")
    
    ax1.set_title("Tỷ lệ Toxic theo giờ trong ngày (YouTube)", fontsize=14, pad=15)
    ax1.set_xlabel("Giờ trong ngày (0–23)", fontsize=12)
    ax1.set_xticks(range(0, 24))
    
    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=11)
    
    fig.tight_layout()
    return _save_fig(fig, "05_toxic_theo_gio.png", output_dir)


# ─── BIỂU ĐỒ 6: SO SÁNH NGUỒN ──────────────────────────────────────────────

def ve_so_sanh_nguon(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ nhóm so sánh tỷ lệ nhãn giữa các nguồn dữ liệu.
    
    Args:
        df: DataFrame với cột 'label' và 'source'
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file biểu đồ
    """
    if "source" not in df.columns or df["source"].nunique() < 2:
        logger.info("ℹ Chỉ có 1 nguồn dữ liệu, bỏ qua biểu đồ so sánh.")
        return ""
    
    _setup_output_dir(output_dir)
    
    # Tính tỷ lệ phần trăm theo nguồn
    ct = pd.crosstab(df["source"], df["label"], normalize="index") * 100
    ct = ct.reindex(columns=["CLEAN", "OFFENSIVE", "HATE"], fill_value=0)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    x     = np.arange(len(ct.index))
    width = 0.25
    
    for i, (col, color) in enumerate(COLORS.items()):
        if col in ct.columns:
            bars = ax.bar(
                x + i * width, ct[col], width,
                label=col, color=color, alpha=0.85,
                edgecolor="white", linewidth=0.5
            )
            # Số liệu trên cột
            for bar, val in zip(bars, ct[col]):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.5,
                        f"{val:.1f}%",
                        ha="center", fontsize=9, color="white")
    
    ax.set_title("So sánh tỷ lệ toxic giữa YouTube và ViHSD (%)", fontsize=14, pad=15)
    ax.set_xticks(x + width)
    ax.set_xticklabels(ct.index, fontsize=12)
    ax.set_ylabel("Tỷ lệ (%)", fontsize=12)
    ax.legend(fontsize=11)
    ax.set_ylim(0, max(ct.max()) * 1.15)
    
    fig.tight_layout()
    return _save_fig(fig, "06_so_sanh_nguon.png", output_dir)


# ─── HÀM CHÍNH: Vẽ tất cả biểu đồ ─────────────────────────────────────────

def ve_tat_ca_bieu_do(df: pd.DataFrame, stats: dict, output_dir: str = OUTPUT_DIR) -> list[str]:
    """
    Vẽ tất cả biểu đồ phân tích và lưu vào output_dir.
    
    Args:
        df: DataFrame đầy đủ đã gán nhãn
        stats: Dict kết quả từ analyze/statistics.chay_tat_ca_thong_ke()
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Danh sách đường dẫn các file biểu đồ đã tạo
    """
    logger.info("=" * 60)
    logger.info("▶ BẮT ĐẦU VẼ BIỂU ĐỒ")
    logger.info("=" * 60)
    
    saved = []
    
    # 1. Phân phối nhãn
    logger.info("[1/6] Biểu đồ phân phối nhãn...")
    saved.append(ve_phan_phoi_nhan(df, output_dir))
    
    # 2. Tỷ lệ toxic vs clean
    logger.info("[2/6] Biểu đồ tròn tỷ lệ toxic...")
    saved.append(ve_bieu_do_tron(df, output_dir))
    
    # 3. Top từ toxic
    logger.info("[3/6] Biểu đồ top từ toxic...")
    if "top_tu_toxic" in stats and not stats["top_tu_toxic"].empty:
        saved.append(ve_top_tu_toxic(stats["top_tu_toxic"], output_dir=output_dir))
    
    # 4. WordCloud
    logger.info("[4/6] WordCloud cho từng nhãn...")
    saved.extend(ve_wordcloud(df, output_dir))
    
    # 5. Toxic theo giờ
    logger.info("[5/6] Biểu đồ toxic theo giờ...")
    if "phan_tich_gio" in stats:
        saved.append(ve_toxic_theo_gio(stats["phan_tich_gio"], output_dir))
    
    # 6. So sánh nguồn
    logger.info("[6/6] Biểu đồ so sánh nguồn...")
    saved.append(ve_so_sanh_nguon(df, output_dir))
    
    # Lọc path rỗng
    saved = [p for p in saved if p]
    
    logger.info(f"✓ Đã tạo {len(saved)} biểu đồ tại: {output_dir}/")
    return saved
