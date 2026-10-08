<script setup lang="ts">
import { onUnmounted, ref } from 'vue'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'

const linuxInstallCommand =
  'curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash'
const windowsInstallCommand =
  'iex (irm https://hermes-agent.nousresearch.com/install.ps1)'
const reloadShellCommand = `source ~/.zshrc   # 用 bash 的话改成 source ~/.bashrc
hermes`
const hermesDocsUrl =
  'https://hermes-agent.nousresearch.com/docs/getting-started/installation#without-hermes-desktop'
const pluginInstallCommand =
  'hermes plugins install liaosiliangCodeLife/harness-mate-plat/plugin --yes-deps --enable'
const pluginEnvCommand = `cat >> ~/.hermes/.env <<'EOF'
HARNESS_MATE_BOT_ID=<bot_id>
HARNESS_MATE_BOT_KEY=<bot_key>
EOF`
const pluginRestartCommand = 'hermes gateway restart'
const pluginInstallDocUrl =
  'https://github.com/liaosiliangCodeLife/harness-mate-plat/blob/main/plugin/INSTALL.md'

const copiedKey = ref('')
let copyResetTimer: ReturnType<typeof setTimeout> | null = null

/*
 * @Author Leon-liao
 * @Function: copyCommand(key: string, text: string)
 * @Description //把对应代码块中的安装命令写入剪贴板，并让按钮短暂显示「已复制」
 * @Date :2026/10/07 20:11:30
 * @Param: key: string，当前代码块标识，用于切换按钮文案；text: string，要复制的完整命令文本
 * @return：复制成功后更新按钮文案，约 1.5 秒后恢复为「复制」；失败时不改文案
 */
const copyCommand = async (key: string, text: string) => {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    return
  }
  copiedKey.value = key
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
  }
  copyResetTimer = setTimeout(() => {
    copiedKey.value = ''
    copyResetTimer = null
  }, 1500)
}

onUnmounted(() => {
  if (copyResetTimer) {
    clearTimeout(copyResetTimer)
  }
})
</script>

<template>
  <div
    class="w-full h-full min-h-screen bg-gray-100 bg-cover bg-no-repeat bg-center"
    :style="{ backgroundImage: `url(${AssistantAgentBackground})` }"
  >
    <!-- 中间页面信息 -->
    <div class="w-[600px] h-full min-h-screen mx-auto">
      <div
        class="flex flex-col p-6 gap-2 items-center justify-start overflow-scroll scrollbar-w-none h-[calc(100%-100px)] min-h-[calc(100vh-100px)]"
      >
        <div class="w-full min-w-0">
          <div class="text-[32px] font-bold text-[#165DFF] mt-[52px] mb-4">
            Harness Mate 端到端智能体平台
          </div>
          <div class="text-base text-gray-700">
            从智能体创建、会话接入到运行打通，Harness Mate 把端到端的一整套能力放在一个平台里：创建并管理智能体，接入自己的设备与会话，通过统一网关让消息与文件在平台与智能体之间点对点流转，再用开放接口把 AI 能力接进你现有的业务系统。
          </div>
          <div class="mt-8 min-w-0">
            <div class="mb-3 text-lg font-medium text-gray-900">Step One: 安装 Hermes</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                Harness Mate 上的智能体需要在你自己的机器上运行 Hermes Agent。不需要桌面应用，用一条命令即可安装（Linux / macOS / WSL2）：
              </p>
              <p class="mt-2 text-xs text-gray-500">
                也可以直接下载 Hermes 桌面版：
                <a
                  class="text-blue-600 hover:underline"
                  href="https://hermes-assets.nousresearch.com/Hermes-Setup.dmg?build=351e644b8373"
                  target="_blank"
                  rel="noopener noreferrer"
                >macOS 12+ 下载</a>
                ·
                <a
                  class="text-blue-600 hover:underline"
                  href="https://hermes-assets.nousresearch.com/Hermes-Setup.exe?build=351e644b8373"
                  target="_blank"
                  rel="noopener noreferrer"
                >Windows 10/11 下载</a>
              </p>
              <div class="mt-3 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ linuxInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('linux', linuxInstallCommand)"
                >
                  {{ copiedKey === 'linux' ? '已复制' : '复制' }}
                </button>
              </div>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">
                Windows（PowerShell）
              </div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ windowsInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('windows', windowsInstallCommand)"
                >
                  {{ copiedKey === 'windows' ? '已复制' : '复制' }}
                </button>
              </div>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">
                安装完成后，重载 shell 再启动
              </div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ reloadShellCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('reload', reloadShellCommand)"
                >
                  {{ copiedKey === 'reload' ? '已复制' : '复制' }}
                </button>
              </div>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="hermesDocsUrl"
                target="_blank"
                rel="noopener noreferrer"
              >安装说明来自 Hermes 官方文档 →</a>
            </div>
          </div>
          <div class="mt-8 min-w-0">
            <div class="mb-3 text-lg font-medium text-gray-900">Step Two: 安装 Plugin</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                1) 先拿身份：平台 → 个人空间 → 智能体右侧「⋯」→「配对 Hermes」，复制弹窗里的 bot_id 与 bot_key。
              </p>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                2) 装插件（一条命令，插件在仓库 plugin/ 子目录）：
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ pluginInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('plugin-install', pluginInstallCommand)"
                >
                  {{ copiedKey === 'plugin-install' ? '已复制' : '复制' }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                3) 写入身份到 ~/.hermes/.env（把 &lt;bot_id&gt;、&lt;bot_key&gt; 换成第 1 步复制的值）。bot_id 与 bot_key 请在「个人空间 → 智能体 → 配对 Hermes」弹窗中复制：
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ pluginEnvCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('plugin-env', pluginEnvCommand)"
                >
                  {{ copiedKey === 'plugin-env' ? '已复制' : '复制' }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                4) 确认网关地址：打开 ~/.hermes/plugins/HarnessMate/adapter.py 第 62 行 WS_GATEWAY_WS_URL，应为平台自己的网关地址（形如 wss://&lt;平台域名&gt;:&lt;端口&gt;/ws）。
              </p>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                5) 重启并验证：hermes gateway restart；日志出现「harness_mate 已连接 WS 网关」即成功，回平台进智能体发一条消息能收到回复即端到端打通。
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ pluginRestartCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('plugin-restart', pluginRestartCommand)"
                >
                  {{ copiedKey === 'plugin-restart' ? '已复制' : '复制' }}
                </button>
              </div>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="pluginInstallDocUrl"
                target="_blank"
                rel="noopener noreferrer"
              >安装说明见仓库 plugin/INSTALL.md →</a>
            </div>
          </div>
          <div class="mt-8">
            <div class="mb-3 text-lg font-medium text-gray-900">使用教程</div>
            <div
              class="flex h-32 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50"
            >
              <span class="text-xs text-gray-400">内容待补充</span>
            </div>
          </div>
          <div class="mt-6">
            <div class="mb-3 text-lg font-medium text-gray-900">操作视频</div>
            <div
              class="flex h-32 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50"
            >
              <span class="text-xs text-gray-400">内容待补充</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
