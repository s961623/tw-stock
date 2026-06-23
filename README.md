# 台股查詢（公開網頁版）

輸入股票代號 → 顯示最新收盤價、本益比、殖利率、股價淨值比、每股淨值、毛利率、實收資本額、外資持股%。
資料每天自動更新一次，公開網址手機電腦都能用，**完全免費、不用自己的伺服器**。

運作方式：GitHub Actions 每天收盤後自動抓證交所／櫃買開放資料，存成 `data/stocks.json`；
網頁讀同網域的 JSON，所以不會被瀏覽器的跨網域（CORS）限制擋住。

---

## 一次性設定步驟（約 10 分鐘）

### 1. 準備 GitHub 帳號
沒有的話到 https://github.com 免費註冊。

### 2. 建立新的 repository
- 右上角「+」→ **New repository**。
- Repository name 隨意，例如 `tw-stock`。
- 選 **Public**（公開，Pages 才免費）。
- 按 **Create repository**。

### 3. 上傳這個資料夾的所有檔案
- 在新 repo 頁面點 **uploading an existing file**（或 Add file → Upload files）。
- 把 `taiwan-stock-web` 資料夾裡的東西**全部**拖進去，包含：
  - `index.html`
  - `README.md`
  - `data/`（資料夾）
  - `scripts/`（資料夾）
  - `.github/`（資料夾，**很重要，別漏掉**；這是自動更新的設定）
- 按 **Commit changes**。

> 若拖曳時看不到 `.github` 資料夾（系統把開頭是點的資料夾藏起來），改用「Add file → Create new file」，在檔名欄輸入
> `.github/workflows/update-data.yml`，再把該檔內容貼進去存檔。

### 4. 打開「讀寫權限」（讓自動更新能寫回資料）
- repo 上方 **Settings** → 左側 **Actions** → **General**。
- 捲到最下 **Workflow permissions**，選 **Read and write permissions** → **Save**。

### 5. 開啟網頁（GitHub Pages）
- **Settings** → 左側 **Pages**。
- Source 選 **Deploy from a branch**；Branch 選 **main**、資料夾 **/ (root)** → **Save**。
- 等一兩分鐘，這頁上方會出現你的網址，長得像：
  `https://你的帳號.github.io/tw-stock/`

### 6. 跑第一次資料更新
- 上方 **Actions** 分頁 →（若看到提示）點 **I understand my workflows, enable them**。
- 左側點 **更新台股資料** → 右邊 **Run workflow** → 綠色 **Run workflow**。
- 等約 1 分鐘跑完（出現綠色勾），它會自動把全部約 2000 檔寫進 `data/`。

### 7. 完成
打開第 5 步的網址，輸入代號（例如 `3149`）就能查。把網址傳給別人也能用。

---

## 之後

- **每個工作日台北時間約 14:00 會自動更新一次**，你什麼都不用做。
- 想立刻更新：到 Actions → 更新台股資料 → Run workflow。
- 想改外觀或欄位：改 `index.html`；想改抓的資料：改 `scripts/fetch_data.py`。

## 限制

- 投信%、自營商%、董監持股、400/1000張大戶持股 **沒有免費官方即時 API**，所以顯示「未取得」。
- 資料是「每日一次」的快照（收盤價、季報、殖利率本就是日更），非逐秒即時。
- GitHub 排程任務若 repo 連續 60 天沒有任何更動可能被自動停用；偶爾手動 Run 一次即可。
- 僅供研究參考，非投資建議。
