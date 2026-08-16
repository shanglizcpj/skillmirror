# SkillMirror｜技镜

> Evidence-Driven Programming Skill Assessment  
> 不只判断最终答案，还通过可验证证据理解学习者如何解决问题。

## 1. 项目简介

SkillMirror 是一个面向大学编程学习者的证据驱动能力评估系统。

传统编程测评通常只判断最终答案是否正确。SkillMirror 会观察学习者在挑战过程中的代码修改、程序运行、测试结果、提示使用和提交行为，并将这些行为转化为可信 Evidence，最终更新学习者的 Skill Score 和 Confidence。

核心闭环：

```text
Challenge
→ Coding
→ Run
→ Test
→ Hint
→ Submit
→ Assessment
→ Evidence
→ Skill Update
→ Next Challenge
```

当前版本以 Python 为第一编程语言，优先实现固定 Challenge 的完整稳定闭环。

## 2. 核心功能

- Skill Mirror 能力数字孪生
- 自适应 Challenge 推荐
- Monaco Python 在线代码编辑器
- Docker Python Sandbox
- 公开测试与隐藏测试
- 渐进式 Hint
- Action Logging
- Evidence Materialization
- Skill Score 更新
- Confidence 更新
- Evidence History
- Assessment Report
- Demo用户快速切换
- 异常提示和全局错误处理
- Docker Compose 部署

## 3. 核心能力模型

当前 Skill Tree 包含：

- Coding
- Debugging
- Testing
- Problem Solving
- Code Reading

SkillMirror 同时展示：

- Score：学习者当前能力水平
- Confidence：系统对该能力判断的确定程度
- Evidence Count：支撑能力判断的证据数量
- History：能力随挑战发生的变化过程

## 4. 系统架构

```text
Browser
   │
   ▼
Vue 3 + Vite / Nginx
   │
   ▼
B FastAPI Backend
   ├── User Session
   ├── Action Logger
   ├── Test Runner
   ├── Evidence History
   ├── SQLite Database
   └── Agent Orchestrator
          │
          ▼
      A Agent Service
      ├── Examiner
      ├── Challenge Generator
      ├── Coach
      ├── Evaluator
      ├── Evidence Engine
      └── Skill Engine

B Test Runner
   │
   ▼
Docker Python Sandbox
```

## 5. A/B职责边界

### 成员A：SkillMirror Brain

负责：

- Skill Tree
- Evidence Rules
- Skill Score
- Confidence Engine
- Examiner Agent
- Challenge Generator
- Coach Agent
- Evaluator Agent
- Adaptive Strategy
- Agent Tests
- Agent Architecture

### 成员B：SkillMirror System

负责：

- Vue Web UI
- Monaco Code Editor
- FastAPI系统后端
- SQLite数据库
- 用户身份与Session
- Action Logger
- Python Sandbox
- Test Runner
- Agent Orchestrator
- Evidence History持久化
- Skill Visualization
- Evidence Timeline
- Docker部署
- 系统测试
- Demo联调

## 6. 项目目录

```text
skillmirror/
├── frontend/
│   ├── src/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── .env.example
│
├── backend/
│   ├── app/
│   ├── data/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── requirements.lock.txt
│   └── .env.example
│
├── sandbox/
│   ├── Dockerfile
│   └── runner.py
│
├── SkillMirror_A_Final_v2.1/
│   ├── API_CONTRACT_A.md
│   ├── README.md
│   ├── agents/
│   ├── skill_engine/
│   └── docs/
│
├── scripts/
│   ├── verify-deployment.ps1
│   ├── check-final-delivery.ps1
│   └── run-final-tests.ps1
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

## 7. 环境要求

推荐环境：

- Windows 10/11
- Python 3.12
- Node.js 22
- npm
- Docker Desktop
- Docker Compose
- PowerShell
- 现代浏览器

推荐确认：

```powershell
python --version
node --version
npm --version
docker --version
docker compose version
```

## 8. 环境变量

### 8.1 B后端

复制：

```powershell
Copy-Item backend\.env.example backend\.env
```

`backend\.env`：

```dotenv
SKILLMIRROR_A_BASE_URL=http://127.0.0.1:8000
SKILLMIRROR_INTERNAL_TOKEN=replace-with-shared-token
SKILLMIRROR_B_PROVENANCE_SECRET=replace-with-shared-secret
SKILLMIRROR_ENABLE_FAILURE_TESTS=0
```

要求：

- Internal Token 至少32字节。
- B Provenance Secret 至少32字节。
- A、B必须使用完全相同的共享值。
- 正常运行时 Failure Tests 必须为0。
- `.env` 不得提交到Git。
- 不得在截图、日志、README或压缩包中公开真实值。

### 8.2 A服务

A服务需要：

```text
SKILLMIRROR_INTERNAL_TOKEN
SKILLMIRROR_B_PROVENANCE_SECRET
SKILLMIRROR_A_EVIDENCE_SECRET
```

其中：

```text
SKILLMIRROR_A_EVIDENCE_SECRET
```

只能由A持有，B端不得配置、保存或读取。

## 9. 本地开发启动

需要三个终端。

### 9.1 启动A服务

```powershell
cd D:\skillmirror\SkillMirror_A_Final_v2.1
.\.venv\Scripts\Activate.ps1

python -m uvicorn api.app:app `
    --reload `
    --host 127.0.0.1 `
    --port 8000
```

检查：

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

### 9.2 启动B后端

```powershell
cd D:\skillmirror\backend
.\.venv\Scripts\Activate.ps1

python -m uvicorn app.main:app `
    --reload `
    --host 127.0.0.1 `
    --port 8001
```

检查：

```text
http://127.0.0.1:8001/health
http://127.0.0.1:8001/docs
```

### 9.3 启动前端

```powershell
cd D:\skillmirror\frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

打开：

```text
http://127.0.0.1:5173
```

## 10. Docker部署

A服务当前单独运行在宿主机，B后端和前端由 Docker Compose 启动。

### 10.1 构建镜像

```powershell
cd D:\skillmirror

docker build `
    -t skillmirror-python-sandbox:latest `
    .\sandbox

docker build `
    -t skillmirror-backend:latest `
    .\backend

docker build `
    -t skillmirror-frontend:latest `
    .\frontend
```

检查：

```powershell
docker images
```

必须存在：

```text
skillmirror-python-sandbox:latest
skillmirror-backend:latest
skillmirror-frontend:latest
```

### 10.2 Docker模式启动A服务

Docker中的B后端通过 `host.docker.internal` 访问A，因此A必须监听所有本机网络接口：

```powershell
cd D:\skillmirror\SkillMirror_A_Final_v2.1
.\.venv\Scripts\Activate.ps1

python -m uvicorn api.app:app `
    --host 0.0.0.0 `
    --port 8000
```

### 10.3 启动B服务

```powershell
cd D:\skillmirror
docker compose up -d
```

检查：

```powershell
docker compose ps
```

访问：

```text
Frontend:  http://127.0.0.1:8080
B Health:  http://127.0.0.1:8001/health
B OpenAPI: http://127.0.0.1:8001/docs
A Health:  http://127.0.0.1:8000/health
```

### 10.4 查看日志

```powershell
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
```

实时查看：

```powershell
docker compose logs -f backend
```

### 10.5 停止服务

```powershell
docker compose stop
```

重新启动：

```powershell
docker compose start
```

删除容器但保留本地数据：

```powershell
docker compose down
```

## 11. Docker Sandbox

用户代码不会直接通过服务器的 `exec()` 执行。

Test Runner 通过隔离的 Docker Sandbox 执行代码，并限制：

- 执行时间
- CPU
- 内存
- 网络
- 文件访问
- 容器生命周期

Sandbox镜像：

```text
skillmirror-python-sandbox:latest
```

B后端容器通过 Docker Socket 调用宿主机 Docker Engine。

检查：

```powershell
docker compose exec backend docker version
docker compose exec backend docker images
```

## 12. 数据库

数据库类型：

```text
SQLite
```

默认路径：

```text
backend\data\skillmirror_orchestrator.db
```

Docker容器路径：

```text
/app/data/skillmirror_orchestrator.db
```

主要持久化内容：

- Challenge Session
- Server Challenge
- Learner Challenge
- Action Logs
- Test Results
- Assessment Results
- Trusted Evidence History
- Skill Mirror
- Next Examiner Decision

数据库文件属于运行数据，不应提交到公开仓库。

## 13. Demo用户

系统提供三个演示用户：

### User A · Beginner

```text
U-DEMO-BEGINNER-01
```

特点：

- 初级学习者
- 证据较少
- Confidence较低
- 优先进行基础诊断Challenge

### User B · Intermediate

```text
U-DEMO-INTERMEDIATE-01
```

特点：

- 中级学习者
- 具有一定历史证据
- 需要验证Testing等能力

### User C · Advanced

```text
U-DEMO-ADVANCED-01
```

特点：

- 较强学习者
- Skill Score较高
- 适合验证型或更高难度Challenge

## 14. Demo操作流程

推荐比赛演示顺序：

1. 打开 Home。
2. 展示 Skill Mirror。
3. 进入 Challenge。
4. 选择 Demo用户。
5. 点击 Start Challenge。
6. 查看Challenge目标。
7. 修改Python代码。
8. 点击 Run Tests。
9. 查看公开测试与隐藏测试结果。
10. 请求渐进式Hint。
11. 修复代码并通过全部测试。
12. 点击 Submit Assessment。
13. 查看 Assessment Complete。
14. 展示 Score 和 Confidence 更新。
15. 打开 Evidence 页面。
16. 打开 Report 页面。
17. 展示 Evidence Timeline。
18. 返回 Challenge并开始下一项挑战。

## 15. API文档

A服务：

```text
http://127.0.0.1:8000/docs
```

B服务：

```text
http://127.0.0.1:8001/docs
```

A/B正式接口契约：

```text
SkillMirror_A_Final_v2.1\API_CONTRACT_A.md
```

联调过程中不得自行猜测A侧字段，应以正式契约为准。

## 16. 异常处理

系统已覆盖：

- A服务离线
- B后端离线
- Token或Secret不一致
- Python执行超时
- 无限循环
- SyntaxError
- Runtime Error
- 只读文件系统
- Sandbox不可用
- Test Runner失败
- Challenge生成失败
- A返回非JSON
- A返回错误Schema
- 数据库异常
- 前端未处理异常

异常情况下，前端应显示可理解的错误提示，而不是白屏或直接泄露内部堆栈。

## 17. 测试

### 最终交付检查

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\check-final-delivery.ps1
```

### 部署检查

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\verify-deployment.ps1
```

### 最终系统测试

```powershell
powershell -ExecutionPolicy Bypass `
    -File .\scripts\run-final-tests.ps1
```

通过标志：

```text
B15.1 DELIVERY CHECK PASSED
B14 DEPLOYMENT PASSED
B15.2 AUTOMATED TESTS PASSED
```

## 18. 安全边界

- 浏览器只能获得 Learner Challenge。
- 隐藏测试不得返回浏览器。
- 参考答案不得返回浏览器。
- Server Challenge只能保存在B后端。
- A Evidence Secret只能由A保存。
- B只保存共享Internal Token和B Provenance Secret。
- 用户代码只能在Sandbox中执行。
- Sandbox默认禁用网络。
- `.env`、数据库、日志和真实密钥不得打入参赛压缩包。
- 错误响应不得泄露Token、Secret或完整内部堆栈。

## 19. 当前版本范围

当前版本重点：

- Python
- 固定Challenge
- 完整Evidence闭环
- 确定性测试与评分
- 可复现Demo
- Docker部署

暂未包含：

- 多语言代码执行
- 大规模动态题库
- 教师管理后台
- 社交系统
- 排行榜
- 手机App
- 生产级多租户权限
- 完全依赖在线LLM的动态出题

这些内容作为 Future Work。

## 20. 验收标准

项目最终验收必须真实完成：

```text
Start Challenge
→ Coding
→ Run
→ Test
→ Hint
→ Submit
→ Assessment Complete
→ Evidence
→ Skill Update
→ Next Challenge
```

中间不得人工修改数据库，不得向浏览器泄露隐藏测试或参考答案。

## 21. 项目状态

当前版本：

```text
SkillMirror Prototype v0.2.0
```

当前状态：

```text
Fixed Challenge End-to-End Demo Available
Docker Deployment Available
Evidence-Driven Assessment Available
```

## 22. License与使用说明

Copyright © 2026 SkillMirror Team. All rights reserved.

本仓库当前作为比赛评审、项目展示和团队协作原型公开，不代表本项目已采用开源许可证。

除相关法律法规或第三方许可证另有规定外，未经 SkillMirror 项目团队事先书面许可，不得复制、修改、分发、再许可或将本项目用于商业用途。

项目使用的第三方框架、依赖库、模型及其他外部资源仍分别遵循其各自的许可证和使用条款。

This competition prototype is provided for evaluation and demonstration purposes. No permission is granted for redistribution or commercial use without prior written permission from the SkillMirror project team.