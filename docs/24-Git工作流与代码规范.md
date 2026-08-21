# 24 - Git 工作流与代码规范

> 状态：待评审  
> 最近更新：2026-01-01  
> 所属文档库：[README](../README.md)

## 1. 分支策略

个人项目建议简化：

```text
main            # 稳定可发布分支
├── feature/xxx # 功能分支，从 main 切出
└── fix/xxx     # 修复分支
```

- 禁止直接向 `main` 提交未验证代码。
- 功能完成后合并回 `main`，保持小而聚焦的提交。

## 2. 提交信息规范

使用约定式提交：

```text
feat: 添加视频生成任务接口
fix: 修复任务状态轮询超时问题
docs: 补充 Provider 适配层设计
refactor: 重构成本计算模块
test: 增加任务状态机单元测试
chore: 更新依赖
```

- 全部使用中文描述。
- 一次提交只做一件事。
- 提交前必须运行 linter。

## 3. 代码规范

### 3.1 Python

- 使用 Ruff 作为 linter / formatter。
- 类型注解：所有函数参数和返回值必须标注类型。
- 命名：
  - 变量 / 函数：`snake_case`
  - 类：`PascalCase`
  - 常量：`UPPER_SNAKE_CASE`
- 禁止单字母变量名（循环计数器 `i`、`j` 除外）。
- 注释使用中文，代码标识符使用英文。

### 3.2 前端（React 阶段）

- 使用 ESLint + Prettier。
- 组件：`PascalCase`
- 变量 / 函数：`camelCase`
- 样式类名：`kebab-case` 或 CSS Modules。

## 4. 提交前检查清单

- [ ] 运行 linter 无错误。
- [ ] 相关测试通过。
- [ ] 无 `print` 调试残留。
- [ ] 无硬编码密钥。
- [ ] 未误提交 `.env`、密钥、本地数据库文件。
- [ ] 文档已同步（如涉及 API / 数据模型）。

## 5. 合并 / 发布流程

```text
feature/xxx
  → 本地测试通过
  → 合并到 main
  → 打 tag（如 v0.1.0）
  → 部署
```

## 6. 常用 Git 命令建议

```bash
# 新建功能分支
git checkout -b feature/add-video-task

# 查看即将提交的内容
git status
git diff --cached

# 提交
git commit -m "feat: 添加视频生成任务接口"

# 合并
git checkout main
git merge feature/add-video-task
```
