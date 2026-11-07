# CourseQA Mermaid 图表使用说明

本文件夹存放 CourseQA 系统的结构化图表，均以 Mermaid 语法编写，已针对**打印输出**优化（白底黑字）。

---

## 文件列表

| 文件 | 图表类型 | Mermaid 语法 | 说明 |
|---|---|---|---|
| `er_diagram.md` | 传统 Chen 氏 ER 图 | `flowchart TB` | 矩形=实体、椭圆=属性、菱形=关系，带 1/N/M 基数 |
| `entity_diagram.md` | 系统类图（UML） | `classDiagram` | 类框含属性类型与方法签名，带关联箭头 |

---

## 图表说明

### er_diagram.md — Chen 氏 ER 图

**用途：** 展示系统数据实体之间的语义关系，适合论文"数据库设计"章节。

**形状约定：**

| 形状 | 含义 | 示例 |
|---|---|---|
| 矩形 `[ ]` | 实体 | 用户、课程 |
| 椭圆 `( )` | 属性，`★` 表示主键 | id ★、用户名 |
| 菱形 `{ }` | 联系（关系） | 创建、加入课程 |
| 连线标注 | 基数 | `"1"` `"N"` `"M"` `"0~1"` |

**包含的 8 个核心实体：** 用户、课程、问答记录、笔记、消息、群组、个人日程、公开日程

**关键关系说明：**

| 关系 | 基数 | 说明 |
|---|---|---|
| 用户 → 创建 → 课程 | 1:N | 仅教师角色 |
| 用户 → 加入课程 → 课程 | M:N | 仅学生角色，通过选课记录表实现 |
| 用户 → 提问 → 问答记录 | 0~1:N | 支持匿名提问（0~1 端） |
| 课程 → 1:1 对应 → 群组 | 1:1 | 创建课程时自动建群 |
| 用户 → 发送/接收 → 消息 | 1:N | 私信系统，同一实体担任两端角色 |

---

### entity_diagram.md — 系统类图

**用途：** 以 UML 类图展示业务对象的属性与方法，适合论文"系统设计"章节。

**包含的 17 个实体类：** User、Session、Course、CourseMember、QuestionLog、Message、ConversationPin、Note、NoteComment、Group、GroupMember、GroupMessage、GroupPin、Schedule、PublicSchedule、PublicScheduleRead、ScheduleNotification

---

## 渲染方式

### 方式一：VS Code（推荐，支持直接预览）

安装插件 [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid)，打开 `.md` 文件后按 `Ctrl+Shift+V` 预览。

### 方式二：Mermaid 在线编辑器

将代码块内容（三个反引号之间的部分）粘贴到 [Mermaid Live Editor](https://mermaid.live/)，可实时预览并导出 **SVG / PNG**。

> 导出时建议选 SVG，矢量格式打印更清晰。

### 方式三：GitHub / GitLab

推送到仓库后平台自动渲染，无需插件。

---

## 打印注意事项

两份图表均已配置：

- `%%{init}%%` 指令强制使用 `base` 主题，白色背景
- `classDef` / `themeVariables` 确保所有节点**白底、黑边、黑字**

若在某些渲染器中仍出现深色节点，请在 Mermaid Live Editor 中导出 SVG 后用浏览器打印，或导入 draw.io 进一步调整。

---

## 数据库与向量库说明

| 存储 | 位置 | 说明 |
|---|---|---|
| SQLite | `data/courseqa.db` | 所有业务表，ER 图覆盖范围 |
| ChromaDB | `data/chroma_db/` | 向量库，每门课对应集合 `course_{course_key}`，不在 ER 图范围内 |
| 文件系统 | `data/uploads/` | 上传 PDF，命名规则：`{course_key}_{原始文件名}` |
