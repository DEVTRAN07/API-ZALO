# API-ZALO — kho dữ liệu dựng sẵn cho bot ZALO-BOT

Repo này **chỉ chứa dữ liệu** (ảnh/GIF preview, ảnh mẫu) và một máy chủ nhỏ
đọc chúng. Code bot nằm ở repo riêng: `ZALO-BOT`.

Tách ra khỏi repo code vì:

| | Repo code (ZALO-BOT) | Repo dữ liệu (API-ZALO) |
|---|---|---|
| Nội dung | `src/`, tests, tools | `data/*.gif`, `data/*.png`, manifest |
| Kích thước | vài MB | vài MB dữ liệu (không tính vào git của code) |
| Đổi 1 card GIF | 0 thay đổi | 1 file + manifest |
| Bot tải | `git pull` code | tải **một lần** rồi cache trên đĩa |

## Nội dung

```
data/
  manifest.json            # sha256 + size của mọi file (bot dùng để biết bản nào mới)
  gif_studio/*.gif|png     # 66 ảnh preview cho từng lệnh (tab GIF Studio)
  sample_images/*          # ảnh mẫu cho lệnh original (music, sticker, browser…)
app.py                     # máy chủ đọc dữ liệu (Flask)
```

## Cách bot dùng

Bot (repo ZALO-BOT) có module `src/utils/core/remote_data.py`:

* ưu tiên **đọc từ đĩa** — `DATA/api_cache/` là bản sao local;
* thiếu file mới tải về (kiểm tra `sha256` trong `manifest.json`);
* chỉ gọi mạng **một lần cho mỗi file**, tải trong thread nền khi bot khởi động;
* mất mạng vẫn chạy: panel rơi về render card tại chỗ.

Đổi nguồn dữ liệu (nếu không dùng GitHub raw):

```bash
# base URL khác (ví dụ server tự dựng)
export ZALOBOT_DATA_URL=http://127.0.0.1:8080/data
# hoặc ghi vào DATA/remote_data.json: {"base": "..."}
```

### Repo dữ liệu đang để PRIVATE thì sao?

`raw.githubusercontent.com` **trả 404 với repo private** (đã gặp thật: push
xong bot vẫn không tải được gì). Khi đó bot tự chuyển sang đường **git**:
clone/pull repo này bằng credential sẵn có của máy (keychain/token đã dùng
để push) — không cần token riêng, và chỉ truyền phần file đã đổi.

Nếu muốn dùng đường HTTP (nhanh hơn cho máy mới), chọn một trong hai:

* đổi repo này sang **public** — dữ liệu chỉ là ảnh preview, không có bí mật;
* hoặc cấp token đọc: `export ZALOBOT_DATA_TOKEN=<token>` (fine-grained,
  chỉ quyền *Contents: Read*).

## Đẩy dữ liệu lên đây

Chạy trong repo **ZALO-BOT** (nơi có sẵn dữ liệu đã dựng):

```bash
python tools/publish_api_data.py --check              # xem sẽ đẩy gì
python tools/publish_api_data.py --publish            # copy vào checkout API-ZALO + commit
python tools/publish_api_data.py --publish --push     # ... rồi push lên GitHub
python tools/publish_api_data.py --pull               # máy khác: kéo hết dữ liệu về
```

`--pull` đổ dữ liệu vào `DATA/api_cache/` rồi copy sang `DATA/gif_studio/`,
`DATA/sample_images/` để mọi đường dẫn cũ trong repo code vẫn chạy.

## Chạy như API

```bash
pip install -r requirements.txt
python app.py            # http://0.0.0.0:8080
```

| Endpoint | Nội dung |
|---|---|
| `GET /health` | `{"ok": true, "files": N}` |
| `GET /manifest.json` | sha256 + size mọi file |
| `GET /data/<path>` | file thật, có `ETag` + `Cache-Control: max-age=86400` |
| `GET /` | danh sách dữ liệu |

## Câu hỏi thường gặp

**Để dữ liệu trên GitHub có làm bot chậm không?**
Không, vì bot không gọi mạng khi trả lời. File được tải **một lần** khi bot
khởi động (thread nền) và sau đó là đọc từ đĩa (~vài ms). Chỉ máy mới/thiếu
file mới tốn khoảng một lượt tải.

**GIF nhiều hiệu ứng (nặng) có nên để ở đây?**
GIF bot *gửi cho người dùng* thì không đưa lên đây — chúng được dựng tại chỗ
khi trả lời rồi xoá. Chỉ những gì **dựng sẵn để xem/gửi lại nhiều lần**
(ảnh preview, ảnh mẫu) mới nằm trong repo này, vì đó là phần lặp lại và
không cần tính toán lại.

**Bí mật có bị đẩy lên đây không?**
Không. Chỉ ảnh/GIF dựng sẵn và manifest. Cookie/token/phiên Zalo nằm trong
`configs/` của repo code và bị `.gitignore` chặn.
