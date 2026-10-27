<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'
import skillMd from '@/assets/hermes-windows-install.md?raw'
import { APP_VERSION } from '@/utils/version'
import { t } from '@/locales'

const linuxInstallCommand =
  'curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash'
const windowsInstallCommand =
  'iex (irm https://hermes-agent.nousresearch.com/install.ps1)'
const reloadShellCommand = computed(
  () => `source ~/.zshrc   # ${t('home.reloadComment')}\nhermes`,
)
const hermesDocsUrl =
  'https://hermes-agent.nousresearch.com/docs/getting-started/installation#without-hermes-desktop'
const pluginInstallCommand =
  'hermes plugins install liaosiliangCodeLife/harness-mate-plat/plugin/hermes --yes-deps --enable'
const pluginInstallDocUrl =
  'https://github.com/liaosiliangCodeLife/harness-mate-plat/blob/main/plugin/hermes/INSTALL.md'
const dshPluginCloneCommand =
  'git clone --depth 1 https://github.com/liaosiliangCodeLife/harness-mate-plat.git'
const dshPluginMoveCommandMac =
  'mkdir -p ~/Documents && mv harness-mate-plat/plugin/dsh ~/Documents/harness-mate'
const dshPluginMoveCommandWin =
  'move harness-mate-plat\\plugin\\dsh %USERPROFILE%\\Documents\\harness-mate'
const dshPluginInstallCommandMac =
  'cd ~/Documents/harness-mate && chmod +x install.sh && ./install.sh'
const dshPluginInstallOnceCommandMac = './install.sh <bot_id> <bot_key>'
const dshPluginInstallCommandWin = 'powershell -ExecutionPolicy Bypass -File .\\install.ps1'
const dshPluginInstallOnceCommandWin = '.\\install.ps1 -BotId <bot_id> -BotKey <bot_key>'
const dshPluginDocUrl =
  'https://github.com/liaosiliangCodeLife/harness-mate-plat/blob/main/plugin/dsh/INSTALL.md'

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
    <div class="w-full h-full min-h-screen">
      <div
        class="flex flex-col p-6 gap-2 items-stretch justify-start overflow-scroll scrollbar-w-none h-[calc(100%-100px)] min-h-[calc(100vh-100px)]"
      >
        <div class="w-full min-w-0">
          <div class="text-[32px] font-bold text-[#165DFF] mt-[52px] mb-4">
            {{ t('home.title') }}
          </div>
          <div class="text-xs text-gray-400">Version {{ APP_VERSION }}</div>
          <div class="text-base text-gray-700">
            {{ t('home.intro') }}
          </div>

          <!-- Step 1 · 安装 DeepSeek Harness -->
          <div class="mt-8 min-w-0">
            <div class="mb-4 text-xl font-bold text-gray-900">Step 1 · 安装 DeepSeek Harness</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <ul class="list-disc space-y-1 pl-5 text-sm leading-6 text-gray-700">
                <li>官网下载 <code class="rounded bg-gray-100 px-1">dsh-latest-windows-x64.exe</code></li>
                <li>双击安装，不需要管理员权限</li>
                <li>打开后登录账号，新建会话即可开始用</li>
              </ul>

              <img
                src="/tutorial/dsh-02-flow.png"
                alt="DeepSeek Harness 安装流程总览"
                class="mt-4 w-full rounded-md border border-gray-200"
              />

              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">系统要求</div>
              <ul class="list-disc space-y-1 pl-5 text-sm leading-6 text-gray-700">
                <li>Windows 10+ x64；macOS 13+ Apple 芯片</li>
                <li>磁盘约 1.0 GB（用户数据另计）；安装包约 276 MB</li>
              </ul>

              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">下载</div>
              <p class="text-sm leading-6 text-gray-700">
                下载页：
                <a
                  class="text-blue-600 hover:underline"
                  href="https://www.deepseek.com/download/"
                  target="_blank"
                  rel="noopener noreferrer"
                >https://www.deepseek.com/download/</a>
              </p>
              <p class="mt-1 text-sm leading-6 text-gray-700">
                Windows 直链：
                <a
                  class="break-all text-blue-600 hover:underline"
                  href="https://download.deepseek.com/desktop/dsh-latest-windows-x64.exe"
                  target="_blank"
                  rel="noopener noreferrer"
                >https://download.deepseek.com/desktop/dsh-latest-windows-x64.exe</a>
              </p>
              <p class="mt-1 text-sm leading-6 text-gray-700">
                macOS 直链：
                <a
                  class="break-all text-blue-600 hover:underline"
                  href="https://download.deepseek.com/desktop/dsh-latest-macos-arm64.dmg"
                  target="_blank"
                  rel="noopener noreferrer"
                >https://download.deepseek.com/desktop/dsh-latest-macos-arm64.dmg</a>
              </p>

              <img
                src="/tutorial/dsh-01-download.png"
                alt="DeepSeek Harness 下载页"
                class="mt-4 w-full rounded-md border border-gray-200"
              />

              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">安装</div>
              <p class="text-sm leading-6 text-gray-700">
                双击安装包 → 若出现 SmartScreen，点「更多信息 → 仍要运行」→ 一路下一步。默认目录：
                <code class="rounded bg-gray-100 px-1 break-all">C:\Users\&lt;用户名&gt;\AppData\Local\Programs\DeepSeek Harness</code>
              </p>

              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">首次启动</div>
              <p class="text-sm leading-6 text-gray-700">
                登录 DeepSeek 账号。凭据保存在
                <code class="rounded bg-gray-100 px-1 break-all">C:\Users\&lt;用户名&gt;\.dsh\.credentials.yaml</code>
                ，请勿外传。
              </p>

              <img
                src="/tutorial/dsh-03-interface.png"
                alt="DeepSeek Harness 界面说明"
                class="mt-4 w-full rounded-md border border-gray-200"
              />
              <p class="mt-3 text-sm leading-6 text-gray-700">
                界面说明：左上「应用 / 编辑」是菜单；＋ 新建会话；插件与自动化任务入口；左侧是工作区与会话列表；右上可切换运行模式与查看后台任务；对话区支持「对话 / 轨迹」切换。
              </p>

              <img
                src="/tutorial/dsh-04-folders.png"
                alt="DeepSeek Harness 目录说明"
                class="mt-4 w-full rounded-md border border-gray-200"
              />
              <p class="mt-3 text-sm leading-6 text-gray-700">
                目录说明：程序目录是安装位置；用户数据在
                <code class="rounded bg-gray-100 px-1">%USERPROFILE%\.dsh</code>
                （卸载不会删除）。
              </p>

              <p class="mt-4 text-xs text-gray-500">
                更新请用应用内置自动更新；卸载在 Windows 设置 → 应用里操作。
              </p>
            </div>
          </div>

          <!-- Step 2 · 安装 Hermes -->
          <div class="mt-8 min-w-0">
            <div class="mb-4 text-xl font-bold text-gray-900">Step 2 · 安装 Hermes</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                {{ t('home.hermesIntro') }}
              </p>
              <p class="mt-2 text-xs text-gray-500">
                {{ t('home.downloadDesktop') }}
                <a
                  class="text-blue-600 hover:underline"
                  href="https://hermes-assets.nousresearch.com/Hermes-Setup.dmg?build=351e644b8373"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ t('home.macDownload') }}</a>
                ·
                <a
                  class="text-blue-600 hover:underline"
                  href="https://hermes-assets.nousresearch.com/Hermes-Setup.exe?build=351e644b8373"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ t('home.winDownload') }}</a>
              </p>
              <div class="mt-3 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ linuxInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('linux', linuxInstallCommand)"
                >
                  {{ copiedKey === 'linux' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">
                {{ t('home.windowsShell') }}
              </div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ windowsInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('windows', windowsInstallCommand)"
                >
                  {{ copiedKey === 'windows' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">
                {{ t('home.reloadHint') }}
              </div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ reloadShellCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('reload', reloadShellCommand)"
                >
                  {{ copiedKey === 'reload' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="hermesDocsUrl"
                target="_blank"
                rel="noopener noreferrer"
              >{{ t('home.hermesDocs') }}</a>

              <div class="mb-2 mt-6 text-sm font-medium text-gray-900">用 SKILL.md 安装（推荐）</div>
              <p class="text-sm leading-6 text-gray-700">
                把下面这段 SKILL.md 全文复制，保存成 SKILL.md 交给 AI 助手（Cursor / Claude / Hermes 都行），它会按里面的步骤装好 Hermes 并处理国内网络、代理端口、Windows 执行策略等坑；装了 Hermes 的用户也可以直接
                <code class="rounded bg-gray-100 px-1">hermes skills install &lt;目录&gt;</code>
                安装成技能。
              </p>
              <div class="relative mt-3 min-w-0 rounded-md bg-gray-100">
                <button
                  type="button"
                  class="absolute right-2 top-2 z-10 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('hermes-skill-md', skillMd)"
                >
                  {{ copiedKey === 'hermes-skill-md' ? t('common.copied') : t('common.copy') }}
                </button>
                <pre class="m-0 max-h-[420px] overflow-auto whitespace-pre-wrap break-all p-3 pr-16 font-mono text-xs leading-5 text-gray-800">{{ skillMd }}</pre>
              </div>
            </div>
          </div>

          <!-- Step 3 · 安装插件 -->
          <div class="mt-8 min-w-0">
            <div class="mb-4 text-xl font-bold text-gray-900">Step 3 · 安装插件（按你用的平台各装各的）</div>

            <div class="mb-3 text-lg font-medium text-gray-900">Hermes 插件</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                {{ t('home.hermesInstallCmd') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ pluginInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('plugin-install', pluginInstallCommand)"
                >
                  {{ copiedKey === 'plugin-install' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="pluginInstallDocUrl"
                target="_blank"
                rel="noopener noreferrer"
              >{{ t('home.hermesPluginDocs') }}</a>
            </div>

            <div class="mb-3 mt-6 text-lg font-medium text-gray-900">DeepSeek Harness 插件</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                {{ t('home.dshIdentity') }}
              </p>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshClone') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginCloneCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-clone', dshPluginCloneCommand)"
                >
                  {{ copiedKey === 'dsh-clone' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshMoveMac') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginMoveCommandMac }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-move-mac', dshPluginMoveCommandMac)"
                >
                  {{ copiedKey === 'dsh-move-mac' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">Windows</div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginMoveCommandWin }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-move-win', dshPluginMoveCommandWin)"
                >
                  {{ copiedKey === 'dsh-move-win' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshRun') }}
              </p>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">macOS</div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginInstallCommandMac }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-install-mac', dshPluginInstallCommandMac)"
                >
                  {{ copiedKey === 'dsh-install-mac' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">{{ t('home.oneShot') }}</p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginInstallOnceCommandMac }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-install-mac-once', dshPluginInstallOnceCommandMac)"
                >
                  {{ copiedKey === 'dsh-install-mac-once' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <div class="mb-2 mt-4 text-sm font-medium text-gray-900">Windows</div>
              <div class="flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginInstallCommandWin }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-install-win', dshPluginInstallCommandWin)"
                >
                  {{ copiedKey === 'dsh-install-win' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">{{ t('home.oneShot') }}</p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshPluginInstallOnceCommandWin }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-install-win-once', dshPluginInstallOnceCommandWin)"
                >
                  {{ copiedKey === 'dsh-install-win-once' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshFinish') }}
              </p>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="dshPluginDocUrl"
                target="_blank"
                rel="noopener noreferrer"
              >{{ t('home.dshPluginDocs') }}</a>
            </div>
          </div>

          <!-- 视频教程（最底部） -->
          <div class="mt-8">
            <div class="mb-3 text-lg font-medium text-gray-900">{{ t('home.videos') }}</div>
            <video
              :src="t('home.hermesVideoUrl')"
              controls
              playsinline
              preload="metadata"
              class="w-full rounded-lg border border-gray-200 bg-black"
            ></video>
            <p class="mt-3 text-xs text-gray-400">{{ t('home.hermesVideoCaption') }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
