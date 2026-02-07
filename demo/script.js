// script.js
let articles = []; // sẽ load tất cả .md

// Load tất cả articles (giả sử bạn chạy local server hoặc dùng fetch với file list)
async function loadArticles() {
  // Cách 1: Nếu bạn liệt kê thủ công hoặc dùng script generate list
  // Cách 2: Dùng fetch với file .md (cần local server như live-server)
  // Để đơn giản: giả sử bạn có file manifest.json chứa list slug + url + title
  // Hoặc load từng file (chậm nếu 401 file → chỉ load khi cần)

  // Ví dụ đơn giản: hardcode 1-2 file để test, sau mở rộng
  // Thực tế: dùng Promise.all để load nhiều file

  const slugs = ["how-to-add-a-youtube-video", "add-1-or-multiple-assets-to-many-playlists-at-the-same-time"]; // thêm slug thật của bạn
  for (let slug of slugs) {
    try {
      const resp = await fetch(`../articles/${slug}.md`);
      const text = await resp.text();
      articles.push({ slug, content: text });
    } catch (e) {
      console.error("Load error:", slug);
    }
  }
  console.log(`Loaded ${articles.length} articles`);
}

function searchArticles(query) {
  query = query.toLowerCase();
  let results = [];

  for (let art of articles) {
    if (art.content.toLowerCase().includes(query)) {
      // Extract first Article URL from front-matter
      const urlMatch = art.content.match(/Article URL:\s*(https?:\/\/[^\n]+)/i);
      const url = urlMatch ? urlMatch[1].trim() : `https://support.optisigns.com/.../${art.slug}`;

      // Extract title
      const titleMatch = art.content.match(/^# (.*)$/m);
      const title = titleMatch ? titleMatch[1] : art.slug.replace(/-/g, ' ');

      results.push({ title, url, snippet: art.content.substring(0, 300) + '...' });
      if (results.length >= 3) break; // max 3 citations
    }
  }
  return results;
}

function formatResponse(results, query) {
  if (results.length === 0) {
    return "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong tài liệu. Vui lòng thử câu hỏi khác!";
  }

  let answer = `Đây là hướng dẫn cho câu hỏi "${query}":\n\n`;

  // Giả lập trả lời ngắn (thực tế bạn có thể hardcode hoặc dùng rule-based)
  answer += "- Truy cập dashboard OptiSigns.\n";
  answer += "- Chọn playlist hoặc screen.\n";
  answer += "- Nhấn Add Content → chọn YouTube.\n";
  answer += "- Dán link video và lưu.\n\n";

  answer += "Chi tiết tham khảo:\n";
  results.forEach((r, i) => {
    answer += `- **Article ${i+1}:** ${r.title}\n`;
    answer += `  **Article URL:** ${r.url}\n\n`;
  });

  return answer;
}

function addMessage(text, isUser = false) {
  const container = document.getElementById("chat-container");
  const msg = document.createElement("div");
  msg.className = `message ${isUser ? 'user' : 'bot'}`;
  msg.innerHTML = text.replace(/\n/g, '<br>');
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

async function sendMessage() {
  const input = document.getElementById("userInput");
  const query = input.value.trim();
  if (!query) return;

  addMessage(query, true);
  input.value = "";

  // Tìm kết quả
  const results = searchArticles(query);
  const response = formatResponse(results, query);
  addMessage(response);
}

// Init
loadArticles().then(() => {
  addMessage("Xin chào! Tôi là OptiBot mini (demo local). Hỏi tôi về OptiSigns nhé! Ví dụ: How do I add a YouTube video?");
});