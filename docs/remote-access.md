# 远程仓库访问说明

本地工作区 `/workspace/qt` 目前没有配置 `git remote`。可以通过下列命令检查并添加远程：

```bash
git -C /workspace/qt remote -v
git -C /workspace/qt remote add origin https://github.com/jsshwqz/qt
git -C /workspace/qt fetch origin
```

直接访问远程仓库可使用：

```bash
git ls-remote https://github.com/jsshwqz/qt
```
