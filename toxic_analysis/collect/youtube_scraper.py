"""
youtube_scraper.py
------------------
Thu thập bình luận từ YouTube bằng YouTube Data API v3.
Mỗi video lấy tối đa max_results bình luận.
Kết quả lưu vào data/collected/youtube_comments.csv
"""

import os
import time
import logging
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Tải API key từ file .env
load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


DEFAULT_VIDEO_IDS = [
 "Akj12zQniWw"
]


def lay_binh_luan_video(youtube_service, video_id: str, max_results: int = 500) -> list[dict]:

    binh_luan_list = []
    next_page_token = None
    
    logger.info(f"  → Đang lấy bình luận từ video: {video_id}")
    
    try:
        while len(binh_luan_list) < max_results:
            # Số lượng lấy mỗi request (tối đa 100 theo API)
            so_luong_request = min(100, max_results - len(binh_luan_list))
            
            # Hàm gọi API có nhúng cơ chế Retry Exponential Backoff (chống lỗi 429)
            @retry(
                stop=stop_after_attempt(4),
                wait=wait_exponential(multiplier=1.5, min=2, max=10),
                retry=retry_if_exception_type(HttpError),
                reraise=True
            )
            def _thuc_hien_request():
                request = youtube_service.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=so_luong_request,
                    pageToken=next_page_token,
                    textFormat="plainText",
                    order="relevance"
                )
                return request.execute()
            
            # Gọi API lấy bình luận
            response = _thuc_hien_request()
            
            # Trích xuất nội dung bình luận
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                binh_luan_list.append({
                    "video_id": video_id,
                    "text": snippet.get("textDisplay", ""),
                    "like_count": snippet.get("likeCount", 0),
                    "published_at": snippet.get("publishedAt", ""),
                    "source": "youtube"
                })
            
            # Kiểm tra trang tiếp theo
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
            
            # Tránh rate limit
            time.sleep(0.5)
            
    except HttpError as e:
        # Xử lý lỗi HTTP (quota vượt, video bị khóa comment, v.v.)
        if e.resp.status == 403:
            logger.warning(f"  ⚠ Video {video_id} bị tắt bình luận hoặc vượt quota.")
        else:
            logger.error(f"  ✗ Lỗi API với video {video_id}: {e}")
    except Exception as e:
        logger.error(f"  ✗ Lỗi không xác định với video {video_id}: {e}")
    
    logger.info(f"  ✓ Lấy được {len(binh_luan_list)} bình luận từ video {video_id}")
    return binh_luan_list


def thu_thap_youtube(
    video_ids: list[str] = None,
    max_per_video: int = 500,
    output_path: str = "data/collected/youtube_comments.csv"
) -> pd.DataFrame:
    """
    Thu thập bình luận từ nhiều video YouTube và lưu vào CSV.
    
    Args:
        video_ids: Danh sách ID video. Nếu None sẽ dùng danh sách mặc định
        max_per_video: Số bình luận tối đa mỗi video
        output_path: Đường dẫn file CSV lưu kết quả
    
    Returns:
        DataFrame chứa toàn bộ bình luận thu thập được
    """
    if not YOUTUBE_API_KEY:
        logger.error("✗ Thiếu YOUTUBE_API_KEY trong file .env!")
        return pd.DataFrame()
    
    if video_ids is None:
        video_ids = DEFAULT_VIDEO_IDS
    
    logger.info(f"▶ Bắt đầu thu thập bình luận từ {len(video_ids)} video YouTube...")
    
    try:
        # Khởi tạo YouTube API service
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    except Exception as e:
        logger.error(f"✗ Không thể khởi tạo YouTube API: {e}")
        return pd.DataFrame()
    
    tat_ca_binh_luan = []
    
    # Lấy bình luận từ từng video
    for i, video_id in enumerate(video_ids, 1):
        logger.info(f"[{i}/{len(video_ids)}] Video: https://youtube.com/watch?v={video_id}")
        binh_luan = lay_binh_luan_video(youtube, video_id, max_per_video)
        tat_ca_binh_luan.extend(binh_luan)
        
        # Nghỉ giữa các video để tránh rate limit
        if i < len(video_ids):
            time.sleep(1)
    
    # Tạo DataFrame
    df = pd.DataFrame(tat_ca_binh_luan)
    
    if df.empty:
        logger.warning("⚠ Không thu thập được bình luận nào từ YouTube!")
        return df
    
    # Loại bỏ bình luận trùng lặp
    df = df.drop_duplicates(subset=["text"])
    
    # Tạo thư mục output nếu chưa có
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Lưu kết quả
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info(f"✓ Đã lưu {len(df)} bình luận YouTube → {output_path}")
    
    return df


if __name__ == "__main__":
    df = thu_thap_youtube()
    print(f"\nTổng bình luận thu thập: {len(df)}")
    print(df.head(3))
