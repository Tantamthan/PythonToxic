"""
facebook_scraper.py
-------------------
Standalone Facebook group comment crawler.

Run this file when you want to crawl Facebook. main.py only reads the CSV
created here and sends unlabeled rows to Gemini.
"""

import argparse
import csv
import logging
import os
import sys
from pathlib import Path
from time import sleep

import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
DATA_DIR = BASE_DIR / "data" / "collected"

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = DATA_DIR / "facebook_comments.csv"
MAX_LAN_KHONG_CO_COMMENT_MOI = 5

BLACKLIST = [
    "Thêm bạn bè", "bạn chung", "Theo dõi", "người theo dõi",
    "Xem thêm", "See more", "Like", "Reply", "Thích", "Trả lời",
    "Chia sẻ", "Share", "Comment", "Bình luận", "Yêu thích",
    "Haha", "Wow", "Buồn", "Phẫn nộ",
]


def init_driver(chromedriver_path: str = "", browser_binary: str = ""):
    options = Options()
    if browser_binary:
        options.binary_location = browser_binary

    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option(
        "prefs",
        {"profile.default_content_setting_values.notifications": 2},
    )

    if chromedriver_path:
        service = Service(executable_path=chromedriver_path)
        return webdriver.Chrome(service=service, options=options)

    return webdriver.Chrome(options=options)


def login_facebook(driver, cookie: str) -> bool:
    if not cookie:
        logger.error("Missing FACEBOOK_COOKIE. Add it to .env or pass --cookie.")
        return False

    try:
        driver.get("https://www.facebook.com/")
        sleep(2)

        for item in cookie.split(";"):
            item = item.strip()
            if "=" not in item:
                continue
            name, value = item.split("=", 1)
            try:
                driver.add_cookie({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".facebook.com",
                })
            except Exception:
                pass

        driver.refresh()
        sleep(3)
        if "login" not in driver.current_url:
            logger.info("Facebook login OK")
            return True

        logger.error("Facebook cookie is expired or invalid.")
        return False
    except Exception as exc:
        logger.error(f"Facebook login failed: {exc}")
        return False


def is_valid_comment(text: str) -> bool:
    if not text or len(text.strip()) < 5:
        return False

    lower_text = text.lower()
    if any(item.lower() in lower_text for item in BLACKLIST):
        return False

    return not text.replace(" ", "").isdigit()


def get_post_ids(driver, group_id: str, amount: int) -> list[str]:
    logger.info(f"Collecting post IDs from Facebook group: {group_id}")
    driver.get(f"https://www.facebook.com/groups/{group_id}")
    sleep(4)

    post_ids = []
    scroll_count = 0

    while len(post_ids) < amount:
        links = driver.find_elements(
            By.XPATH,
            '//a[contains(@href, "/posts/") and contains(@href, "/groups/")]',
        )
        for link in links:
            try:
                href = link.get_attribute("href") or ""
                if "/posts/" not in href:
                    continue

                post_id = href.split("/posts/")[1].split("/")[0].split("?")[0]
                if post_id.isdigit() and post_id not in post_ids:
                    post_ids.append(post_id)
                    logger.info(f"  Post ID: {post_id}")
                    if len(post_ids) >= amount:
                        break
            except Exception:
                pass

        logger.info(f"  Collected posts: {len(post_ids)}/{amount}")
        if len(post_ids) >= amount:
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        sleep(3)
        scroll_count += 1
        if scroll_count > 20:
            logger.warning("Stopped after 20 scrolls without enough posts.")
            break

    return post_ids


def get_comments(driver, post_id: str, group_id: str, max_comments: int) -> list[dict]:
    logger.info(f"Collecting comments from post: {post_id}")
    post_url = f"https://www.facebook.com/groups/{group_id}/posts/{post_id}/"
    driver.get(post_url)
    sleep(3)

    rows = []
    seen_texts = set()
    no_new_count = 0

    for _ in range(50):
        before_count = len(rows)

        try:
            more_buttons = driver.find_elements(
                By.XPATH,
                '//span[contains(text(),"Xem thêm bình luận") or contains(text(),"View more comments")]',
            )
            if more_buttons:
                driver.execute_script("arguments[0].click();", more_buttons[0])
                sleep(2)
        except Exception:
            pass

        try:
            comment_blocks = driver.find_elements(
                By.XPATH,
                '//div[@role="article"]//div[contains(@style,"text-align") or @dir="auto"]',
            )
            if not comment_blocks:
                comment_blocks = driver.find_elements(
                    By.XPATH,
                    '//ul//li//div[@dir="auto" and string-length(text())>5]',
                )

            for block in comment_blocks:
                text = block.text.strip()
                if not is_valid_comment(text) or text in seen_texts:
                    continue

                seen_texts.add(text)
                rows.append({
                    "comment_id": f"facebook_{group_id}_{post_id}_{len(rows) + 1}",
                    "facebook_group_id": group_id,
                    "post_id": post_id,
                    "post_url": post_url,
                    "text": text,
                    "author": "",
                    "published_at": "",
                    "source": "facebook",
                    "split": "collected",
                })
                logger.info(f"  Comment: {text[:80]}")

                if len(rows) >= max_comments:
                    break
        except Exception as exc:
            logger.warning(f"  Comment XPath failed: {exc}")

        if len(rows) >= max_comments:
            break

        new_count = len(rows) - before_count
        if new_count:
            no_new_count = 0
            logger.info(f"  Collected comments: {len(rows)}")
        else:
            no_new_count += 1

        if no_new_count >= MAX_LAN_KHONG_CO_COMMENT_MOI:
            logger.info("  No new comments after several attempts; moving on.")
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        sleep(2)

    logger.info(f"Post {post_id}: {len(rows)} comments")
    return rows


def save_comments(rows: list[dict], output_path: Path, append: bool = False) -> pd.DataFrame:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)

    if append and output_path.exists():
        old_df = pd.read_csv(output_path, encoding="utf-8-sig")
        df = pd.concat([old_df, df], ignore_index=True)

    if not df.empty:
        df = df.drop_duplicates(subset=["source", "post_id", "text"], keep="last")

    df.to_csv(output_path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    logger.info(f"Saved {len(df)} Facebook comments -> {output_path}")
    return df


def thu_thap_facebook(
    group_id: str,
    cookie: str,
    so_luong_post: int = 3,
    so_luong_comment_moi_post: int = 10,
    output_path: str = str(DEFAULT_OUTPUT),
    chromedriver_path: str = "",
    browser_binary: str = "",
    append: bool = False,
) -> pd.DataFrame:
    driver = init_driver(chromedriver_path=chromedriver_path, browser_binary=browser_binary)
    try:
        if not login_facebook(driver, cookie):
            return pd.DataFrame()

        post_ids = get_post_ids(driver, group_id, so_luong_post)
        all_rows = []
        for post_id in post_ids:
            all_rows.extend(
                get_comments(
                    driver=driver,
                    post_id=post_id,
                    group_id=group_id,
                    max_comments=so_luong_comment_moi_post,
                )
            )

        return save_comments(all_rows, Path(output_path), append=append)
    finally:
        driver.quit()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Crawl Facebook group comments into data/collected/facebook_comments.csv"
    )
    parser.add_argument("--group-id", default=os.getenv("FACEBOOK_GROUP_ID", ""))
    parser.add_argument("--cookie", default=os.getenv("FACEBOOK_COOKIE", ""))
    parser.add_argument("--posts", type=int, default=int(os.getenv("FACEBOOK_POST_LIMIT", "3")))
    parser.add_argument(
        "--comments-per-post",
        type=int,
        default=int(os.getenv("FACEBOOK_COMMENT_LIMIT", "10")),
    )
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--chromedriver", default=os.getenv("FACEBOOK_CHROMEDRIVER_PATH", ""))
    parser.add_argument("--browser-binary", default=os.getenv("FACEBOOK_BROWSER_BINARY", ""))
    parser.add_argument("--append", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.group_id:
        raise SystemExit("Missing --group-id or FACEBOOK_GROUP_ID in .env")

    df_result = thu_thap_facebook(
        group_id=args.group_id,
        cookie=args.cookie,
        so_luong_post=args.posts,
        so_luong_comment_moi_post=args.comments_per_post,
        output_path=args.output,
        chromedriver_path=args.chromedriver,
        browser_binary=args.browser_binary,
        append=args.append,
    )
    print(f"\nTotal Facebook comments collected: {len(df_result)}")
