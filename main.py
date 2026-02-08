# src/main.py
"""
Entry point cho daily job: scrape → detect delta → upload lên OpenAI Vector Store
Chạy 1 lần rồi exit 0 (cho Docker / scheduled job)
"""

import logging
import sys
from pathlib import Path
from datetime import datetime


from src.scraper import scrape_all_articles
from src.uploader import upload_delta


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("main.log")
    ]
)
logger = logging.getLogger(__name__)

def main():
    start_time = datetime.utcnow()
    logger.info("=== BẮT ĐẦU DAILY SYNC OPTISIGNS KB ===")
    logger.info(f"Thời gian bắt đầu: {start_time.isoformat()}Z")

    exit_code = 0

    try:
    
        logger.info("Bước 1: Scrape articles từ Zendesk API...")
        scraped_count = scrape_all_articles(max_pages=30)  
        logger.info(f"Scrape hoàn tất: {scraped_count} articles được xử lý")

     
        logger.info("Bước 2: Upload delta lên OpenAI Vector Store...")
        upload_delta() 

        logger.info("=== DAILY SYNC HOÀN TẤT THÀNH CÔNG ===")

    except Exception as e:
        logger.error(f"LỖI TRONG QUÁ TRÌNH SYNC: {str(e)}", exc_info=True)
        exit_code = 1

    finally:
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"Thời gian hoàn thành: {end_time.isoformat()}Z")
        logger.info(f"Tổng thời gian chạy: {duration:.2f} giây")
        logger.info(f"Exit code: {exit_code}")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()