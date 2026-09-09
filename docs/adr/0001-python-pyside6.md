# 用 Python + PySide6(Qt) 实现，而不是 C#/WPF、Electron 或 Rust/Tauri

本应用的核心难点是把第三方窗口真实嵌入到主窗口内并参与自适应布局。Qt 对此有内建支持：`QWindow.fromWinId()` + `createWindowContainer()` 可把外部 HWND 变成普通界面控件直接塞进布局，同时 Qt 自带 Splitter（可拖分隔条）等布局积木，无需手写 Win32 消息循环。Electron/Tauri 需要自写 C++ 原生插件才能做窗口嵌入，与本需求正面冲突；C#/WPF 能做但需要额外安装 .NET SDK 且代码更繁琐。用户机器已有 Python 3.14 + 可正常安装的 PySide6（已验证），且这是纯自用工具，无需打包分发，故选 Python + PySide6。

## Considered Options

- C# + WPF：可行，正统 Windows 路线，但开发成本更高且无额外收益
- Electron：界面易写，但窗口嵌入必须自写 C++ 原生模块，否决
- Rust + Tauri：外部窗口嵌入生态不成熟，学习曲线陡，否决
