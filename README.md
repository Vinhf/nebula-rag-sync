# KB Sync & RAG Demo

Dự án thực hiện take-home test OptiSigns:  
- Scrape ≥30 bài từ support.optisigns.com → Markdown sạch.  
- Upload delta lên OpenAI Vector Store qua API.  
- Daily job tự động.  
- Chatbot demo với citation "Article URL:".

## Tại sao không dùng OpenAI Playground UI (yêu cầu 2)

Yêu cầu bắt buộc **API upload** (không drag-drop UI) → đã làm đúng bằng `uploader.py`.  
Không dùng Playground để tạo Assistant vì tài khoản OpenAI chưa có billing/credit đủ để unlock full access.  
Thay thế bằng **local RAG demo** (Chroma + Gemini 1.5 Flash free tier) với prompt và citation giống hệt:  
- Tone helpful, factual, concise.  
- Max 5 bullet points.  
- Cite ≤3 "Article URL:".  
Screenshot demo local đính kèm.

## Tại sao không dùng DigitalOcean Platform (yêu cầu 3)

DigitalOcean App Platform **tốn phí** (~$5–12/tháng cho container job, không có free tier cho Scheduled Job).  
Thay thế bằng **GitHub Actions** (miễn phí 2000 phút/tháng):  
- Workflow `.github/workflows/daily-sync.yml`: chạy `python main.py` daily (cron `0 3 * * *`).  
- Secrets: OPENAI_API_KEY.  
- Log đầy đủ (added/updated/skipped) → link Actions public.

## Triển khai

1. **Scrape & clean**  
   - `scraper.py`: Lấy 30 bài (max_articles=30 để test nhanh).  
   - Lưu .md + .meta.json (html_url từ Zendesk).

2. **Upload delta**  
   - `uploader.py`: Upload file mới/cập nhật lên OpenAI Vector Store.

3. **Daily job**  
   - `main.py`: Gọi scrape + upload.  
   - GitHub Actions: Cron daily, log public.

4. **Chatbot demo**  
   - `app.py`: Streamlit + Chroma + Gemini 2.5 Flash lite.
   - Citation lấy từ .meta.json.  
   - Deploy miễn phí trên Render.com.  
   - Link live: [https://optibot-chat-demo.onrender.com](https://optibot-chat-demo.onrender.com)  
   - Screenshot: [demo-chatbot.png](screenshots/demo-chatbot.png)

Giải pháp **miễn phí hoàn toàn**, vẫn đáp ứng yêu cầu cốt lõi (API upload, daily job, log, citation URL), thay thế Playground và DigitalOcean bằng công cụ free tương đương.

Cảm ơn reviewer đã xem bài test!