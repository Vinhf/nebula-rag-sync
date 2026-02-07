import os
import json
from pathlib import Path
from datetime import datetime
import logging
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
# Load env (cho local dev)
load_dotenv()

# Config logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
ARTICLES_DIR = Path(__file__).parent.parent / "articles"
STATE_FILE = Path(__file__).parent.parent / "kb_state.json"
VECTOR_STORE_ID = os.getenv("OPENAI_API_KEY")        # vs_xxxx từ env hoặc hardcode tạm
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not VECTOR_STORE_ID or not OPENAI_API_KEY:
    raise ValueError("Missing VECTOR_STORE_ID or OPENAI_API_KEY in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

def load_state() -> dict:
    """Đọc trạng thái cũ: slug -> {file_id, content_hash}. Trả về {} nếu file không tồn tại hoặc rỗng."""
    if not STATE_FILE.exists():
        logger.info(f"State file not found: {STATE_FILE}. Starting fresh.")
        return {}
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                logger.warning(f"State file is empty: {STATE_FILE}. Starting fresh.")
                return {}
            return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in state file {STATE_FILE}: {e}. Starting fresh.")
        return {}
    except Exception as e:
        logger.error(f"Error reading state file {STATE_FILE}: {e}. Starting fresh.")
        return {}

def save_state(state: dict):
    """Lưu trạng thái mới"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated state saved to {STATE_FILE}")

def compute_content_hash(file_path: Path) -> str:
    """Tính SHA256 hash của file .md để detect thay đổi nội dung"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Đọc theo chunk để tránh file lớn chiếm RAM
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def upload_single_file(md_path: Path) -> str | None:
    """Upload 1 file .md lên OpenAI Files, trả về file_id"""
    try:
        with open(md_path, "rb") as f:
            file_obj = client.files.create(
                file=(md_path.name, f, "text/markdown"),
                purpose="assistants"
            )
        logger.info(f"Uploaded file: {md_path.name} → file_id={file_obj.id}")
        return file_obj.id
    except Exception as e:
        logger.error(f"Failed to upload {md_path.name}: {e}")
        return None

def attach_files_to_vector_store(file_ids: list[str]):
    """Attach nhiều file vào vector store bằng batch (hiệu quả)"""
    if not file_ids:
        return

    try:
        batch = client.beta.vector_stores.file_batches.create_and_poll(
            vector_store_id=VECTOR_STORE_ID,
            file_ids=file_ids
        )
        logger.info(f"Batch attached: status={batch.status}, "
                    f"completed={batch.file_counts.completed}, "
                    f"in_progress={batch.file_counts.in_progress}, "
                    f"failed={batch.file_counts.failed}")
    except Exception as e:
        logger.error(f"Batch attach failed: {e}")

def delete_file_from_vector_store(openai_file_id: str):
    """Xóa file cũ khỏi vector store (không xóa file gốc khỏi storage)"""
    try:
        client.beta.vector_stores.files.delete(
            vector_store_id=VECTOR_STORE_ID,
            file_id=openai_file_id
        )
        logger.info(f"Deleted old file from vector store: {openai_file_id}")
    except Exception as e:
        logger.warning(f"Failed to delete {openai_file_id} from vector store: {e}")

def upload_delta():
    """Main logic: detect & upload delta"""
    state = load_state()  # slug → {"file_id": "...", "content_hash": "..."}
    new_state = state.copy()

    md_files = list(ARTICLES_DIR.glob("*.md")) [:5]
    logger.info(f"Found {len(md_files)} .md files to process")

    to_upload_ids = []      # file_id cần attach batch
    added_count = 0
    updated_count = 0
    skipped_count = 0

    for md_path in md_files:
        slug = md_path.stem
        current_hash = compute_content_hash(md_path)

        if slug in state:
            old = state[slug]
            if old["content_hash"] == current_hash:
                skipped_count += 1
                logger.debug(f"Skipped (unchanged): {slug}")
                continue

            # Content thay đổi → xóa cũ, upload mới
            logger.info(f"Updated content detected: {slug}")
            delete_file_from_vector_store(old["file_id"])
            updated_count += 1
        else:
            added_count += 1

        # Upload file mới
        new_file_id = upload_single_file(md_path)
        if new_file_id:
            to_upload_ids.append(new_file_id)
            new_state[slug] = {
                "file_id": new_file_id,
                "content_hash": current_hash,
                "last_updated": datetime.utcnow().isoformat() + "Z",
                "md_filename": md_path.name
            }

    # Attach batch một lần (hiệu quả hơn attach từng cái)
    attach_files_to_vector_store(to_upload_ids)

    # Cập nhật state
    save_state(new_state)

    # Summary log
    logger.info("─" * 50)
    logger.info(f"Upload delta summary:")
    logger.info(f"  Added   : {added_count}")
    logger.info(f"  Updated : {updated_count}")
    logger.info(f"  Skipped : {skipped_count}")
    logger.info(f"  Total processed: {added_count + updated_count + skipped_count}")
    logger.info("─" * 50)

if __name__ == "__main__":
    logger.info("Starting delta upload to OpenAI Vector Store...")
    upload_delta()
    logger.info("Delta upload completed.")