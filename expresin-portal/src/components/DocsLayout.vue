<script setup>
/**
 * 文档三栏骨架（升级方案 §6.1）。
 *
 * 取代 ApiDocsView 自建的 240/1fr/360 三栏，复用工作台的骨架语言与
 * token 化栏宽；窄屏先把「示例」折叠到内容下方，再把导航转为顶部横条，
 * 不再直接 display:none 丢失内容。
 */
defineProps({
  /** 页内导航的无障碍标签 */
  navLabel: { type: String, default: '文档导航' },
})
</script>

<template>
  <div class="docs">
    <nav class="docs-nav" :aria-label="navLabel">
      <slot name="nav" />
    </nav>
    <main class="docs-main">
      <slot />
    </main>
    <aside class="docs-aside" aria-label="示例">
      <slot name="aside" />
    </aside>
  </div>
</template>

<style scoped>
.docs {
  display: grid;
  grid-template-columns:
    minmax(200px, var(--docs-nav-w, 232px))
    minmax(0, 1fr)
    minmax(0, var(--docs-aside-w, 340px));
  min-height: 0;
  height: 100%;
}
.docs-nav {
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  border-right: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}
.docs-main {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-6) var(--space-6) var(--space-8);
}
.docs-aside {
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  border-left: 1px solid var(--border-subtle);
  background: var(--bg-secondary);
}

@media (max-width: 1280px) {
  .docs {
    grid-template-columns: minmax(180px, var(--docs-nav-w, 220px)) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
  }
  .docs-nav {
    grid-row: 1 / span 2;
  }
  .docs-main {
    grid-column: 2;
    grid-row: 1;
  }
  /* 示例不再隐藏：窄屏收到正文下方，保留可读，不丢内容 */
  .docs-aside {
    grid-column: 2;
    grid-row: 2;
    max-height: 32vh;
    border-left: none;
    border-top: 1px solid var(--border-subtle);
  }
}
@media (max-width: 768px) {
  .docs {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto auto auto;
    overflow-y: auto;
  }
  .docs-nav {
    grid-column: 1;
    grid-row: 1;
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
  }
  .docs-main {
    grid-column: 1;
    grid-row: 2;
    overflow: visible;
    padding: var(--space-5) var(--space-4) var(--space-8);
  }
  .docs-aside {
    grid-column: 1;
    grid-row: 3;
    max-height: none;
    border-top: 1px solid var(--border-subtle);
  }
}
</style>
