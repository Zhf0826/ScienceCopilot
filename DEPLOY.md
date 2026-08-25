# ScienceCopilot 部署指南（公网 Web 应用）

本指南帮助你在**免费云平台**上将 ScienceCopilot 部署为任何人都能用浏览器直接访问的公网应用，无需访客安装 Python 或下载代码。

> 默认行为：项目**未配置 API Key 时自动进入「演示模式」**（RAG 检索与安全检查均为真实运行，仅最终作答用本地模板合成）。因此部署后**无需任何密钥，任何人打开网址即可使用**。

---

## 一、已生成的部署文件（无需再写）

| 文件 | 作用 |
|---|---|
| `requirements.txt` | 声明零第三方依赖（仅标准库），满足云平台构建约定 |
| `config.py` | `HOST` 默认 `0.0.0.0`、`PORT` 读取环境变量，可被外部访问 |
| `render.yaml` | Render 一键部署配置（**首推方案**） |
| `runtime.txt` | 指定 Python 版本（Render 构建用） |
| `.gitignore` | 排除 `.env`、`.workbuddy/`、`backup/`、`research/`、缓存等 |

---

## 二、首推方案：Render（免费、无需信用卡）

Render 免费 Web Service 无需绑卡，最适合本项目。部署后地址形如：
`https://sciencecopilot-xxx.onrender.com`

### 前置条件
代码已推送到 GitHub 仓库：
- 仓库地址：`https://github.com/Zhf0826/ScienceCopilot`
- 当前最新提交：`71d8715`（教师测试版 UI）

### 步骤 1：在 Render 创建 Web Service
1. 打开 https://render.com → 注册/登录（可用 GitHub 账号授权）。
2. 右上角 **New +** → **Web Service** → 选择 GitHub 仓库 `ScienceCopilot`。
3. 部署方式选 **"Use the render.yaml in this repo"**（仓库里已提供，自动填好构建/启动命令与端口）。
   - 若手动填写：`Runtime = Python`，`Build Command` 留空，`Start Command = python app.py`，`Instance Type = Free`。
4. 点击 **Create Web Service**。

### 步骤 2：获取公网 URL
部署约 1–2 分钟。完成后 Render 会给出形如 `https://sciencecopilot.onrender.com` 的 URL。

> 免费实例在**无流量约 15 分钟后会自动休眠**，首次访问需等待约 30–50 秒冷启动，属正常现象。

### 步骤 3：验证部署
```powershell
$base = "https://你的地址.onrender.com"
curl "$base/api/status"
curl -X POST "$base/api/inquiry" -H "Content-Type: application/json" `
  -d '{"grade":"四年级","topic":"水的蒸发","goal":"理解蒸发","duration":"40分钟","materials":"普通教室材料"}'
```

---

## 三、备选方案：Railway（免费额度，需绑卡验证）

1. https://railway.app → 用 GitHub 登录 → **New Project** → **Deploy from GitHub repo**。
2. 选 `ScienceCopilot` 仓库 → 变量可不填（默认演示模式）。
3. 在 Settings 确认 **Start Command = `python app.py`**，Railway 自动注入 `PORT`。
4. 生成一个 `*.up.railway.app` 域名，点击即可访问。

> Railway 目前新账号需绑定信用卡完成验证（不扣费）才能部署；若不想绑卡，优先用 Render。

---

## 四、部署后自检清单

- [ ] **首页能打开**：访问根地址 `/`，应显示教师欢迎页（ScienceCopilot Landing Page）。
- [ ] **工作台能打开**：访问 `/app.html`，应显示 AI 实验室工作台。
- [ ] **API 正常**：`POST /api/inquiry`、`/api/audit`、`/api/companion`、`/api/diagnose` 返回 SSE 流，`done` 事件包含完整结果。
- [ ] **静态文件正常**：`/styles.css`、`/app.js`、`/landing.js`、`/app.html` 均可加载。
- [ ] **演示模式运行**：`GET /api/status` 返回 `"demo": true`，未配置密钥时也能完整使用。

---

## 五、注意事项

- **自定义域名（可选）**：Render / Railway 付费档支持绑定自己的域名；免费档用平台子域名即可。
- **接入真实模型（可选）**：在平台的环境变量中添加 `DEEPSEEK_API_KEY`（或 `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`），重启后自动切换为真实 LLM 生成。
- **安全**：仓库已 `.gitignore` `.env`，**切勿把真实密钥提交进 Git**。密钥只放在云平台的环境变量里。
- **休眠**：免费实例会休眠，演示足够；若要常驻，升级付费档或设置定时唤醒。

---

## 六、常见问题

**Q：部署后首页打不开 / 健康检查失败？**
A：确认 `Start Command` 为 `python app.py`，且 `config.py` 的 `HOST=0.0.0.0`（已默认）。Render 健康检查访问 `/`，本应用已返回 200。

**Q：提示 Python 版本不支持？**
A：把 `runtime.txt` 改为平台支持的版本（如 `python-3.11`），本项目兼容 3.9+。

**Q：想换子域名？**
A：在 Render 服务的 Settings → Rename 修改 `name`，或改 `render.yaml` 的 `name` 后重新部署。

**Q：访客提交的内容会被保存吗？**
A：不会。当前为无状态服务，请求处理完即丢弃，没有任何数据库或持久化。
