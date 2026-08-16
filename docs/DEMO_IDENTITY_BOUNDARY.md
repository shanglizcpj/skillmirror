# SkillMirror Demo 身份与数据边界

## 当前实现

SkillMirror 当前版本用于比赛单机演示。

前端提交的 `user_id` 用于区分不同演示用户的数据，
`session_id` 用于关联一次 Challenge、测试、提示、Assessment
和 Evidence History 记录。

B 后端会在业务流程中检查部分 Session 与 User 的对应关系。

## 当前不包含的能力

当前版本尚未实现以下生产级安全能力：

- 用户名和密码登录
- OAuth、OpenID Connect 或统一身份认证
- JWT 或服务端登录 Session
- 角色与权限管理
- 完整的多租户数据隔离
- 用户自行注册及账户恢复
- 生产环境隐私数据保护流程

因此，浏览器中的 User ID 不能被视为生产级身份凭证，
演示环境中不应输入真实密码、证件号码或其他敏感个人信息。

## 生产环境升级计划

正式部署时需要增加：

1. 由服务端签发的登录 Session 或 JWT。
2. 将用户身份绑定到不可伪造的认证主体。
3. 对 Evidence、Report 和 History 接口执行资源级授权检查。
4. 禁止客户端自行指定其他用户身份。
5. 增加 HTTPS、CSRF 防护、请求限流和安全审计。
6. 按用户或租户实施数据库访问隔离。