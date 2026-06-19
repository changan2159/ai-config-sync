# Linux Headless Notes

在 Linux 服务器上，Playwright 使用自带 `chromium` 做无界面回归是默认推荐方案。

## 为什么优先这样做

- 浏览器版本和 Playwright 驱动配套，兼容性更稳定。
- 不依赖系统自带 `chromium` 版本，跨机器差异更少。
- `headless` 模式不需要桌面环境。

## 常见问题

### 1. 浏览器二进制不存在

优先执行：

```bash
npx playwright install chromium
```

不要先切到系统 `chromium` 规避，除非用户明确要求。

如果宿主机是比 Playwright 当前正式识别范围更新的 Ubuntu 版本，例如 `Ubuntu 26.04`，可以先设置：

```bash
PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64
```

这仍然是 Playwright 自带浏览器，只是让下载器复用最近的官方 Linux fallback build。

### 2. Linux 缺少共享库

表现通常是 Playwright 启动浏览器时报缺包、缺 `.so`、或者直接退出。

先看 Playwright 的报错提示。必要时可执行：

```bash
npx playwright install --with-deps chromium
```

如果当前环境不允许自动装系统依赖，就按报错补齐宿主机依赖包。

### 3. 容器或受限环境沙箱报错

优先先确认是不是容器安全策略或权限限制导致。只有确实需要时，才考虑 `--no-sandbox` 这类降级方案。

不要把 `--no-sandbox` 设成默认值。

## 推荐汇报方式

回归结束后，至少汇报：

1. 使用的前端目录
2. 使用的命令
3. 是否先执行了 `npx playwright install chromium`
4. 通过/失败的阶段
5. 如果失败，失败点是脚本逻辑、浏览器依赖，还是环境权限
