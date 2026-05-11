"""
advanced_visualize.py
---------------------
Trực quan hóa kết quả phân tích nâng cao.

Các biểu đồ:
1. Biểu đồ N-gram (bigram, trigram)
2. Biểu đồ phân phối mức độ toxic
3. Biểu đồ tương quan (scatter plot)
4. Biểu đồ so sánh chủ đề giữa các nhãn
"""

import os
import logging
import warnings
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

# Tắt cảnh báo
warnings.filterwarnings("ignore")
matplotlib.use("Agg")

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Style
sns.set_theme(style="darkgrid", palette="muted")
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


# ═══════════════════════════════════════════════════════════════════════════
# 1. BIỂU ĐỒ N-GRAM
# ═══════════════════════════════════════════════════════════════════════════

def ve_ngram(df_bigram: pd.DataFrame, df_trigram: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> list:
    """
    Vẽ biểu đồ bigram và trigram.
    
    Args:
        df_bigram: DataFrame bigram từ advanced_stats
        df_trigram: DataFrame trigram từ advanced_stats
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Danh sách đường dẫn file
    """
    _setup_output_dir(output_dir)
    saved = []
    
    # Bigram
    if not df_bigram.empty:
        fig, ax = plt.subplots(figsize=(12, 8))
        df_plot = df_bigram.head(15).sort_values("count", ascending=True)
        
        colors = plt.cm.YlOrRd(np.linspace(0.4, 0.9, len(df_plot)))
        bars = ax.barh(df_plot["ngram"], df_plot["count"], color=colors, edgecolor="white", linewidth=0.3)
        
        for bar, val in zip(bars, df_plot["count"]):
            ax.text(bar.get_width() + df_plot["count"].max() * 0.01, bar.get_y() + bar.get_height() / 2,
                   f"{val:,}", va="center", fontsize=10, color="#eaeaea")
        
        ax.set_title("Top 15 Bigram (Cụm 2 Từ) Toxic Phổ Biến", fontsize=14, pad=15)
        ax.set_xlabel("Tần suất xuất hiện", fontsize=12)
        ax.set_ylabel("Bigram", fontsize=12)
        ax.set_xlim(0, df_plot["count"].max() * 1.15)
        
        fig.tight_layout()
        saved.append(_save_fig(fig, "07_bigram_toxic.png", output_dir))
    
    # Trigram
    if not df_trigram.empty:
        fig, ax = plt.subplots(figsize=(12, 8))
        df_plot = df_trigram.head(15).sort_values("count", ascending=True)
        
        colors = plt.cm.Reds(np.linspace(0.4, 0.9, len(df_plot)))
        bars = ax.barh(df_plot["ngram"], df_plot["count"], color=colors, edgecolor="white", linewidth=0.3)
        
        for bar, val in zip(bars, df_plot["count"]):
            ax.text(bar.get_width() + df_plot["count"].max() * 0.01, bar.get_y() + bar.get_height() / 2,
                   f"{val:,}", va="center", fontsize=10, color="#eaeaea")
        
        ax.set_title("Top 15 Trigram (Cụm 3 Từ) Toxic Phổ Biến", fontsize=14, pad=15)
        ax.set_xlabel("Tần suất xuất hiện", fontsize=12)
        ax.set_ylabel("Trigram", fontsize=12)
        ax.set_xlim(0, df_plot["count"].max() * 1.15)
        
        fig.tight_layout()
        saved.append(_save_fig(fig, "08_trigram_toxic.png", output_dir))
    
    return saved


# ═══════════════════════════════════════════════════════════════════════════
# 2. BIỂU ĐỒ MỨC ĐỘ TOXIC
# ═══════════════════════════════════════════════════════════════════════════

def ve_muc_do_toxic(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ phân phối mức độ toxic.
    
    Args:
        df: DataFrame với cột 'toxic_level' và 'label'
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file
    """
    if "toxic_level" not in df.columns:
        logger.warning("⚠ Không có cột 'toxic_level', bỏ qua biểu đồ")
        return ""
    
    _setup_output_dir(output_dir)
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Subplot 1: Phân phối tổng thể
    level_order = ["KHÔNG TOXIC", "TOXIC NHẸ", "TOXIC TRUNG BÌNH", "TOXIC NẶNG", "CỰC KỲ TOXIC"]
    counts = df["toxic_level"].value_counts().reindex(level_order, fill_value=0)
    
    colors_map = {
        "KHÔNG TOXIC": "#2ECC71",
        "TOXIC NHẸ": "#F39C12",
        "TOXIC TRUNG BÌNH": "#E67E22",
        "TOXIC NẶNG": "#E74C3C",
        "CỰC KỲ TOXIC": "#C0392B"
    }
    colors = [colors_map[l] for l in counts.index]
    
    bars = axes[0].bar(range(len(counts)), counts.values, color=colors, edgecolor="white", linewidth=0.5, alpha=0.9)
    
    for i, (bar, val) in enumerate(zip(bars, counts.values)):
        pct = val / counts.sum() * 100
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + counts.max() * 0.01,
                    f"{val:,}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=10, color="#ffffff")
    
    axes[0].set_xticks(range(len(counts)))
    axes[0].set_xticklabels(counts.index, rotation=15, ha="right", fontsize=10)
    axes[0].set_title("Phân Phối Mức Độ Toxic", fontsize=14, pad=15)
    axes[0].set_ylabel("Số lượng bình luận", fontsize=12)
    axes[0].set_ylim(0, counts.max() * 1.2)
    
    # Subplot 2: Phân phối theo nhãn
    ct = pd.crosstab(df["label"], df["toxic_level"], normalize="index") * 100
    ct = ct.reindex(columns=level_order, fill_value=0)
    
    x = np.arange(len(ct.index))
    width = 0.15
    
    for i, level in enumerate(level_order):
        if level in ct.columns:
            offset = (i - 2) * width
            bars = axes[1].bar(x + offset, ct[level], width, label=level, 
                             color=colors_map[level], alpha=0.85, edgecolor="white", linewidth=0.3)
    
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(ct.index, fontsize=11)
    axes[1].set_title("Mức Độ Toxic Theo Nhãn (%)", fontsize=14, pad=15)
    axes[1].set_ylabel("Tỷ lệ (%)", fontsize=12)
    axes[1].legend(fontsize=9, loc="upper right")
    axes[1].set_ylim(0, 100)
    
    fig.tight_layout()
    return _save_fig(fig, "09_muc_do_toxic.png", output_dir)


# ═══════════════════════════════════════════════════════════════════════════
# 3. BIỂU ĐỒ TƯƠNG QUAN
# ═══════════════════════════════════════════════════════════════════════════

def ve_tuong_quan(df: pd.DataFrame, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ scatter plot: độ dài comment vs điểm toxic.
    
    Args:
        df: DataFrame với cột 'do_dai', 'toxic_score', 'label'
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file
    """
    if "toxic_score" not in df.columns or "do_dai" not in df.columns:
        logger.warning("⚠ Thiếu cột cần thiết, bỏ qua biểu đồ tương quan")
        return ""
    
    _setup_output_dir(output_dir)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # Lọc outliers (độ dài quá lớn)
    df_plot = df[df["do_dai"] <= df["do_dai"].quantile(0.95)].copy()
    
    # Vẽ scatter plot theo nhãn
    colors_map = {"CLEAN": "#2ECC71", "OFFENSIVE": "#F39C12", "HATE": "#E74C3C"}
    
    for label, color in colors_map.items():
        df_label = df_plot[df_plot["label"] == label]
        if not df_label.empty:
            ax.scatter(df_label["do_dai"], df_label["toxic_score"], 
                      c=color, label=label, alpha=0.4, s=20, edgecolors="none")
    
    # Thêm đường xu hướng
    z = np.polyfit(df_plot["do_dai"], df_plot["toxic_score"], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df_plot["do_dai"].min(), df_plot["do_dai"].max(), 100)
    ax.plot(x_line, p(x_line), "r--", linewidth=2, alpha=0.7, label="Xu hướng")
    
    # Tính correlation
    corr = df_plot[["do_dai", "toxic_score"]].corr().iloc[0, 1]
    ax.text(0.05, 0.95, f"Correlation: {corr:.3f}", transform=ax.transAxes,
           fontsize=12, verticalalignment="top", bbox=dict(boxstyle="round", facecolor="#16213e", alpha=0.8))
    
    ax.set_title("Tương Quan: Độ Dài Comment vs Điểm Toxic", fontsize=14, pad=15)
    ax.set_xlabel("Độ dài comment (ký tự)", fontsize=12)
    ax.set_ylabel("Điểm toxic (0-100)", fontsize=12)
    ax.legend(fontsize=11, loc="upper right")
    ax.grid(True, alpha=0.3)
    
    fig.tight_layout()
    return _save_fig(fig, "10_tuong_quan_dodai_toxic.png", output_dir)


# ═══════════════════════════════════════════════════════════════════════════
# 4. BIỂU ĐỒ CHỦ ĐỀ
# ═══════════════════════════════════════════════════════════════════════════

def ve_chu_de(topics_dict: dict, output_dir: str = OUTPUT_DIR) -> str:
    """
    Vẽ biểu đồ so sánh từ khóa giữa các nhãn.
    
    Args:
        topics_dict: Dict chứa DataFrame từ khóa cho mỗi nhãn
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Đường dẫn file
    """
    if not topics_dict:
        logger.warning("⚠ Không có dữ liệu chủ đề, bỏ qua biểu đồ")
        return ""
    
    _setup_output_dir(output_dir)
    
    # Tạo subplot cho mỗi nhãn
    n_labels = len(topics_dict)
    fig, axes = plt.subplots(1, n_labels, figsize=(6 * n_labels, 7))
    
    if n_labels == 1:
        axes = [axes]
    
    colors_map = {"HATE": "#E74C3C", "OFFENSIVE": "#F39C12", "CLEAN": "#2ECC71"}
    
    for i, (label, df_topic) in enumerate(topics_dict.items()):
        if df_topic.empty:
            continue
        
        df_plot = df_topic.head(10).sort_values("count", ascending=True)
        color = colors_map.get(label, "#3498DB")
        
        bars = axes[i].barh(df_plot["word"], df_plot["count"], color=color, 
                           edgecolor="white", linewidth=0.3, alpha=0.85)
        
        for bar, val in zip(bars, df_plot["count"]):
            axes[i].text(bar.get_width() + df_plot["count"].max() * 0.01,
                        bar.get_y() + bar.get_height() / 2,
                        f"{val:,}", va="center", fontsize=9, color="#eaeaea")
        
        axes[i].set_title(f"Từ Khóa Đặc Trưng: {label}", fontsize=13, pad=10)
        axes[i].set_xlabel("Tần suất", fontsize=11)
        axes[i].set_xlim(0, df_plot["count"].max() * 1.15)
    
    fig.tight_layout()
    return _save_fig(fig, "11_chu_de_theo_nhan.png", output_dir)


# ═══════════════════════════════════════════════════════════════════════════
# HÀM CHÍNH
# ═══════════════════════════════════════════════════════════════════════════

def ve_tat_ca_bieu_do_nang_cao(results: dict, output_dir: str = OUTPUT_DIR) -> list:
    """
    Vẽ tất cả biểu đồ phân tích nâng cao.
    
    Args:
        results: Dict kết quả từ advanced_stats.chay_phan_tich_nang_cao()
        output_dir: Thư mục lưu biểu đồ
    
    Returns:
        Danh sách đường dẫn file đã tạo
    """
    logger.info("=" * 60)
    logger.info("▶ BẮT ĐẦU VẼ BIỂU ĐỒ PHÂN TÍCH NÂNG CAO")
    logger.info("=" * 60)
    
    saved = []
    
    # 1. N-gram
    if "ngram" in results:
        logger.info("[1/4] Biểu đồ N-gram...")
        saved.extend(ve_ngram(
            results["ngram"].get("bigram", pd.DataFrame()),
            results["ngram"].get("trigram", pd.DataFrame()),
            output_dir
        ))
    
    # 2. Mức độ toxic
    if "df_with_intensity" in results:
        logger.info("[2/4] Biểu đồ mức độ toxic...")
        path = ve_muc_do_toxic(results["df_with_intensity"], output_dir)
        if path:
            saved.append(path)
    
    # 3. Tương quan
    if "correlation" in results and "df_with_metrics" in results["correlation"]:
        logger.info("[3/4] Biểu đồ tương quan...")
        path = ve_tuong_quan(results["correlation"]["df_with_metrics"], output_dir)
        if path:
            saved.append(path)
    
    # 4. Chủ đề
    if "topics" in results:
        logger.info("[4/4] Biểu đồ chủ đề...")
        path = ve_chu_de(results["topics"], output_dir)
        if path:
            saved.append(path)
    
    saved = [p for p in saved if p]
    logger.info(f"✓ Đã tạo {len(saved)} biểu đồ phân tích nâng cao!")
    
    return saved
