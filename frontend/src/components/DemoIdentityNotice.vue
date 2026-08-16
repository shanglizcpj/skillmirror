<template>
  <aside
    class="demo-identity-notice"
    role="note"
    aria-label="Demo identity notice"
  >
    <span class="notice-label">DEMO IDENTITY</span>

    <p>
      <strong>比赛演示身份机制：</strong>
      User ID 和 Session ID 仅用于区分演示用户及其评估记录，
      当前版本不代表生产级登录认证、权限控制或多租户数据隔离。
      请勿输入真实敏感个人信息。
    </p>
  </aside>
</template>

<style scoped>
.demo-identity-notice {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin: 18px 0 0;
  padding: 14px 18px;
  color: #7a4b00;
  background: #fff8e6;
  border: 1px solid #f3d38a;
  border-radius: 14px;
  line-height: 1.6;
}

.notice-label {
  flex-shrink: 0;
  padding: 3px 9px;
  color: #8a5500;
  background: #ffe7a8;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.demo-identity-notice p {
  margin: 0;
}

@media (max-width: 700px) {
  .demo-identity-notice {
    flex-direction: column;
    gap: 8px;
  }
}
</style>