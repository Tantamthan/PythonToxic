"""
reddit_scraper.py
-----------------
Thu thập bình luận từ Reddit bằng Public JSON API.
KHÔNG CẦN API KEY — chỉ cần gửi HTTP request đến reddit.com/.json

Tập trung vào các subreddit tiếng Việt để phân tích toxic.
Kết quả lưu vào data/collected/reddit_comments.csv
"""

import os
import re
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timezone

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ─── CẤU HÌNH ───────────────────────────────────────────────────────────────
# User-Agent bắt buộc phải có để Reddit không chặn
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) toxic-analysis-bot/1.0"
}

# Danh sách subreddit tiếng Việt mặc định
DEFAULT_SUBREDDITS = [
    "Vietnam",              # Cộng đồng Việt Nam chính (song ngữ)
    "VietNam",              # Subreddit Việt Nam phụ
    "TroChuyenLinhTinh",    # Trò chuyện linh tinh (tiếng Việt thuần)
]

# Thời gian chờ giữa các request (giây) — tránh bị rate limit
DELAY_GIAY = 2

VIETNAMESE_DIACRITIC_RE = re.compile(
    r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩ"
    r"òóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
    re.IGNORECASE,
)

VIETNAMESE_HINT_WORDS = {
    "anh", "em", "ban", "bạn", "minh", "mình", "toi", "tôi", "tao", "may", "mày",
    "nguoi", "người", "viet", "việt", "nam", "vn", "vietnam", "khong", "không",
    "ko", "k", "duoc", "được", "dc", "đc", "la", "là", "co", "có", "cua", "của",
    "cho", "voi", "với", "trong", "ngoai", "ngoài", "nhung", "nhưng", "neu", "nếu",
    "thi", "thì", "ma", "mà", "do", "đó", "day", "đây", "nay", "này", "kia",
    "cai", "cái", "con", "thang", "thằng", "dua", "đứa", "lam", "làm", "noi",
    "nói", "biet", "biết", "thay", "thấy", "nghi", "nghĩ", "roi", "rồi", "qua",
    "quá", "rat", "rất", "hon", "hơn", "nua", "nữa", "di", "đi", "ve", "về",
    "len", "lên", "xuong", "xuống", "dung", "đúng", "sai", "nhieu", "nhiều",
    "it", "ít", "gi", "gì", "sao", "ai", "dau", "đâu", "nao", "nào", "nhe",
    "nhé", "nha", "luon", "luôn", "cung", "cũng", "van", "vẫn", "phai", "phải",
}


def la_binh_luan_tieng_viet(text: str) -> bool:
    """Nhận diện nhanh bình luận tiếng Việt, hỗ trợ cả một phần văn bản không dấu."""
    if not isinstance(text, str):
        return False

    text = text.strip().lower()
    if not text:
        return False

    tokens = re.findall(r"[a-zA-ZÀ-ỹĐđ]+", text)
    if not tokens:
        return False

    hit_count = sum(1 for token in tokens if token in VIETNAMESE_HINT_WORDS)
    has_diacritic = bool(VIETNAMESE_DIACRITIC_RE.search(text))

    if has_diacritic and hit_count >= 1:
        return True
    if has_diacritic and len(tokens) <= 4:
        return True
    if hit_count >= 2:
        return True
    if hit_count >= 1 and hit_count / len(tokens) >= 0.25:
        return True

    return False


def lay_bai_viet_subreddit(
    subreddit_name: str,
    sort_by: str = "hot",
    limit: int = 25,
    time_filter: str = "month"
) -> list[dict]:
    """
    Lấy danh sách bài viết từ subreddit bằng JSON API.
    
    Args:
        subreddit_name: Tên subreddit (không có r/)
        sort_by: hot/new/top/controversial
        limit: Số bài viết tối đa (max 100)
        time_filter: Bộ lọc thời gian cho top/controversial
    
    Returns:
        Danh sách dict chứa thông tin bài viết
    """
    limit = min(limit, 100)  # Reddit giới hạn 100/request
    
    url = f"https://www.reddit.com/r/{subreddit_name}/{sort_by}.json"
    params = {"limit": limit, "raw_json": 1}
    
    if sort_by in ("top", "controversial"):
        params["t"] = time_filter
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if response.status_code == 429:
            logger.warning(f"  ⚠ Rate limit! Đợi 10 giây...")
            time.sleep(10)
            response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"  ✗ HTTP {response.status_code} khi lấy r/{subreddit_name}")
            return []
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        return [post["data"] for post in posts if post.get("kind") == "t3"]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"  ✗ Lỗi kết nối r/{subreddit_name}: {e}")
        return []


def lay_binh_luan_bai_viet(
    subreddit_name: str,
    post_id: str,
    max_comments: int = 100,
    only_vietnamese: bool = True
) -> list[dict]:
    """
    Lấy bình luận từ một bài viết bằng JSON API.
    
    Args:
        subreddit_name: Tên subreddit
        post_id: ID bài viết (t3_xxxxx → xxxxx)
        max_comments: Số bình luận tối đa
        only_vietnamese: Chỉ giữ bình luận có vẻ là tiếng Việt
    
    Returns:
        Danh sách dict chứa bình luận
    """
    url = f"https://www.reddit.com/r/{subreddit_name}/comments/{post_id}.json"
    params = {"limit": max_comments, "raw_json": 1, "sort": "top"}
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        
        # Response là array: [post_data, comments_data]
        if not isinstance(data, list) or len(data) < 2:
            return []
        
        comments_data = data[1].get("data", {}).get("children", [])
        binh_luan_list = []
        skipped_non_vi = 0
        
        def parse_comments(comments, depth=0):
            """Đệ quy lấy tất cả bình luận (kể cả reply)"""
            nonlocal skipped_non_vi
            for comment in comments:
                if comment.get("kind") != "t1":
                    continue
                    
                c = comment.get("data", {})
                body = c.get("body", "")
                
                # Bỏ qua comment bị xóa
                if body in ("[deleted]", "[removed]", ""):
                    continue
                
                # Bỏ qua bot
                author = c.get("author", "")
                if author.lower() in ("automoderator", "botdefense", "[deleted]"):
                    continue

                if only_vietnamese and not la_binh_luan_tieng_viet(body):
                    skipped_non_vi += 1
                    continue
                
                # Chuyển đổi thời gian
                created_utc = c.get("created_utc", 0)
                published_at = datetime.fromtimestamp(
                    created_utc, tz=timezone.utc
                ).isoformat() if created_utc else None
                
                binh_luan_list.append({
                    "comment_id": c.get("id", ""),
                    "subreddit": subreddit_name,
                    "post_id": post_id,
                    "text": body,
                    "author": author,
                    "score": c.get("score", 0),
                    "published_at": published_at,
                    "source": "reddit"
                })
                
                if len(binh_luan_list) >= max_comments:
                    return
                
                # Đệ quy vào replies
                replies = c.get("replies", "")
                if isinstance(replies, dict):
                    reply_children = replies.get("data", {}).get("children", [])
                    parse_comments(reply_children, depth + 1)
        
        parse_comments(comments_data)
        if skipped_non_vi:
            logger.debug(f"    Bỏ qua {skipped_non_vi} bình luận không giống tiếng Việt ở bài {post_id}")
        return binh_luan_list
        
    except Exception as e:
        logger.debug(f"    Lỗi lấy comment bài {post_id}: {e}")
        return []


def thu_thap_reddit(
    subreddits: list[str] = None,
    sort_by: str = "hot",
    max_posts_per_sub: int = 25,
    max_comments_per_post: int = 100,
    time_filter: str = "month",
    output_path: str = "data/collected/reddit_comments.csv",
    only_vietnamese: bool = True
) -> pd.DataFrame:
    """
    Thu thập bình luận từ nhiều subreddit tiếng Việt — KHÔNG CẦN API KEY.
    
    Args:
        subreddits: Danh sách tên subreddit. Nếu None sẽ dùng mặc định
        sort_by: hot/new/top/controversial
        max_posts_per_sub: Số bài viết tối đa mỗi subreddit (max 100)
        max_comments_per_post: Số bình luận tối đa mỗi bài
        time_filter: Bộ lọc thời gian cho top/controversial
        output_path: Đường dẫn file CSV lưu kết quả
        only_vietnamese: Chỉ giữ bình luận có vẻ là tiếng Việt
    
    Returns:
        DataFrame chứa toàn bộ bình luận thu thập được
    """
    if subreddits is None:
        subreddits = DEFAULT_SUBREDDITS
    
    logger.info(f"▶ Bắt đầu thu thập bình luận từ {len(subreddits)} subreddit Reddit...")
    logger.info(f"  Phương thức: Public JSON API (KHÔNG CẦN API KEY)")
    logger.info(f"  Sắp xếp: {sort_by} | Max bài/sub: {max_posts_per_sub} | "
                f"Max comment/bài: {max_comments_per_post}")
    logger.info(f"  Lọc tiếng Việt: {'Bật' if only_vietnamese else 'Tắt'}")
    
    tat_ca_binh_luan = []
    
    for i, sub_name in enumerate(subreddits, 1):
        logger.info(f"[{i}/{len(subreddits)}] Subreddit: r/{sub_name}")
        
        # Lấy danh sách bài viết
        posts = lay_bai_viet_subreddit(
            subreddit_name=sub_name,
            sort_by=sort_by,
            limit=max_posts_per_sub,
            time_filter=time_filter
        )
        
        if not posts:
            logger.warning(f"  ⚠ Không lấy được bài viết từ r/{sub_name}")
            time.sleep(DELAY_GIAY)
            continue
        
        logger.info(f"  → Tìm thấy {len(posts)} bài viết, đang lấy bình luận...")
        
        so_binh_luan_sub = 0
        for j, post in enumerate(posts):
            post_id = post.get("id", "")
            post_title = post.get("title", "")[:80]
            num_comments = post.get("num_comments", 0)
            
            # Bỏ qua bài không có bình luận
            if num_comments == 0:
                continue
            
            # Lấy bình luận
            comments = lay_binh_luan_bai_viet(
                subreddit_name=sub_name,
                post_id=post_id,
                max_comments=max_comments_per_post,
                only_vietnamese=only_vietnamese
            )
            
            # Thêm post_title vào mỗi comment
            for c in comments:
                c["post_title"] = post_title
            
            tat_ca_binh_luan.extend(comments)
            so_binh_luan_sub += len(comments)
            
            # Nghỉ giữa các request
            time.sleep(DELAY_GIAY)
        
        logger.info(f"  ✓ r/{sub_name}: {len(posts)} bài → {so_binh_luan_sub} bình luận")
        
        # Nghỉ giữa các subreddit
        if i < len(subreddits):
            time.sleep(DELAY_GIAY)
    
    # Tạo DataFrame
    df = pd.DataFrame(tat_ca_binh_luan)
    
    if df.empty:
        logger.warning("⚠ Không thu thập được bình luận nào từ Reddit!")
        return df
    
    # Loại bỏ trùng lặp, ưu tiên ID bình luận từ Reddit nếu có.
    has_comment_id = (
        "comment_id" in df.columns
        and df["comment_id"].fillna("").astype(str).str.strip().ne("").any()
    )
    dedup_cols = ["comment_id"] if has_comment_id else ["subreddit", "post_id", "text"]
    df = df.drop_duplicates(subset=dedup_cols)
    
    # Loại bỏ bình luận quá ngắn
    df = df[df["text"].str.len() >= 5]
    
    # Tạo thư mục output
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Lưu kết quả
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"✓ Đã lưu {len(df)} bình luận Reddit → {output_path}")
    
    # Thống kê theo subreddit
    if "subreddit" in df.columns:
        for sub, count in df["subreddit"].value_counts().items():
            logger.info(f"  r/{sub}: {count} bình luận")
    
    return df


if __name__ == "__main__":
    print("=" * 60)
    print("TEST: Thu thập bình luận Reddit (Public JSON API)")
    print("=" * 60)
    
    df = thu_thap_reddit(
        sort_by="hot",
        max_posts_per_sub=5,
        max_comments_per_post=20
    )
    if not df.empty:
        print(f"\nTổng bình luận thu thập: {len(df)}")
        print(df[["subreddit", "text", "score"]].head(5))
    else:
        print("\nKhông thu thập được bình luận nào.")
