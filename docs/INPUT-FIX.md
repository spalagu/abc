# 0.1.1：画面点击与右键修复

## 确认的旧版缺陷

旧版只注册 canvas.onclick，未处理 contextmenu，也未发送鼠标按钮字段；Host 只构造左键事件。所有画面动作统一要求目标是前台窗口，即使当前浏览器就在同一台 Host 上。用户回到浏览器操作时自然使目标失去前台。错误只显示在长页面顶部，忙碌中的点击直接静默返回。这些是输入实现问题，不能归因于 Lens 不兼容。

## 改动

开启画面操作时截获 contextmenu，单独发送 button=right；不把一次右键转换成左键加右键。关闭时保留原浏览器菜单。手机提供显式右键选择，不依赖长按识别。画面附近和底部浮动区域显示结果、拒绝原因及“请求忙碌未发送”。获取请求时捕获画面版本，不向更新后的画面盲目重放旧点击。

默认后台路径将位置命中所选应用内的 AX 控件，验证其属于所选窗口，左键用 AXPress、右键用 AXShowMenu。无相应能力时返回不支持，不自动改走另一种操作。

用户可明确选择“后台定向键鼠（实验）”。它验证所选窗口是该进程的 AXFocusedWindow，然后用 CGEventPostToPid，鼠标填写公开窗口字段。不会主动激活应用或发送全局输入。但该 API 不是带确认的窗口协议：应用可能忽略、改变焦点，系统也不返回应用执行回执。因此结果是 submitted_unconfirmed，而非成功执行承诺。前台兼容输入仍是单独选项。

右键菜单可能由独立窗口承载，单窗口捕获未必包含。这版修复本地菜单拦截与传输/路由，不承诺已经实现所有系统弹出菜单的远端显示和选择。实际 Lens/Codex 后台兼容性仍需实机验证。

## 验收

更新 Host 应用，确认页面版本为 0.1.1-demo。原来的连接密钥失效，重新从 Host 打开连接。选择窗口、取得控制权、刷新、勾选画面操作；不要点手动置前。右键画面应不再弹出浏览器菜单。文字反馈必须说明走了哪条路线、是否仅提交未确认或被拒绝。缺少 AX 能力时可在无风险窗口显式试验定向模式。

## 参考接口

- Browser contextmenu: https://developer.mozilla.org/en-US/docs/Web/API/Element/contextmenu_event
- Apple CGEvent posting: https://developer.apple.com/documentation/coregraphics/cgevent/posttopid(_:)
- Public event window field: https://developer.apple.com/documentation/coregraphics/cgeventfield/mouseeventwindowundermousepointer

参考接口的存在不是应用兼容性的证据。自动测试与人工实测范围见 TESTING.md。
