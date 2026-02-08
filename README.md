# FeishuScript 集成系统用户手册

本手册将指导您如何配置和使用 FeishuScript 集成系统，实现百度网盘文件和 Bilibili 直播录像自动同步到飞书云文档。

## 1. 快速开始

### 1.1 环境准备
请确保您已经运行了 `install_env.bat` (Windows) 来安装必要的依赖环境。

### 1.2 配置文件
系统使用一个统一的配置文件 `config.yaml` 来管理所有设置。

1.  打开项目目录下的 `config.yaml` 文件。
2.  根据文件中的注释，填写以下关键信息：
    *   **Feishu (飞书)**: 填写 App ID, App Secret 和目标文件夹 Token。
    *   **Baidu (百度)**: 填写您的 BDUSS 和 STOKEN（从浏览器 Cookies 获取）。
    *   **Tasks (任务)**: 添加您想要监控的百度分享链接和提取码。
    *   **Bilibili (B站)**: 配置 webhook 地址（包含在默认配置中）。

### 1.3 应用配置
每次修改 `config.yaml` 后，**必须**运行以下命令来应用配置：

```bash
python apply_config.py
```

此脚本会将您的配置自动分发到 `baidu-autosave` 和集成服务中。

### 1.4 启动服务
配置完成后，运行以下命令启动集成服务：

```bash
python run_integration.py
```

---

## 2. 详细配置说明

### 2.1 飞书配置 (Feishu)
*   `app_id` & `app_secret`: 在 [飞书开放平台](https://open.feishu.cn/) 创建“企业自建应用”，启用“云文档”相关权限，并获取凭证。
*   `folder_token`: 打开您想要保存文件的飞书文件夹，URL 中 `folder/` 后面的一串字符即为 Token。

### 2.2 百度网盘 (Baidu)
*   `bduss`: 百度账号的核心凭证。请在登录百度网盘网页版后，按 F12 打开开发者工具，在 Application -> Cookies 中找到 `BDUSS` 的值。
*   `tasks`: 一个列表，每项包含：
    *   `link`: 分享链接
    *   `pwd`: 提取码（如果有）
    *   `save_to`: 想要保存到百度网盘内的路径（也是临时下载路径的子目录）

### 2.3 B站动态监控 (Bilibili)
*   **配置 Up 主**:
    无需使用第三方软件。直接在 `config.yaml` 的 `bilibili -> users` 列表中填入您关注的 Up 主 **UID**。
    *   **如何获取 UID**: 打开 Up 主的主页，URL 中 `space.bilibili.com/` 后面的数字即为 UID。
    *   **检查频率**: 默认为 300 秒（5分钟）检查一次，可修改 `check_interval`。

*   **工作原理**:
    系统会在后台每隔设定时间轮询一次。一旦发现新发布的动态（支持文字、图文、视频、转发），会自动将其内容抓取并生成 Markdown 文件，然后上传到飞书。
    *   **本地归档**: 所有下载的动态和图片都会保存在项目根目录下的 `downloaded_dynamics` 文件夹中，按 `[日期] 作者_ID` 格式命名。

*   **充电/专属动态支持**:
    如果您需要获取“充电会员专属”或“仅粉丝可见”的动态，请必须在 `config.yaml` 中配置您的 Cookies：
    *   `sessdata`: 关键凭证，从浏览器 `Application -> Cookies` 中获取。
    *   `bili_jct`: (CSRF Token) 同上。
    *   `buvid3`: 设备标识，同上。

---

## 3. 常见问题

**Q: 为什么百度下载失败？**
A: 请检查 `bduss` 是否过期。如果网页版退出登录，`bduss` 会失效，需要重新获取。

**Q: C++ 报错是什么原因？**
A: 本项目已通过 `setup_libs.py` 移除了对 C++ 环境的依赖。如果您看到相关错误，请重新运行 `install_env.bat`。

**Q: 修改了配置没生效？**
A: 修改 `config.yaml` 后务必运行 `python apply_config.py`。

---

如有其他问题，请查阅项目日志或联系开发者。
