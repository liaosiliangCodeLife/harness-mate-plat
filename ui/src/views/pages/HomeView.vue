<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import AssistantAgentBackground from '@/assets/images/assistant-agent-background.png'
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
const pluginEnvCommand = `cat >> ~/.hermes/.env <<'EOF'
HARNESS_MATE_BOT_ID=<bot_id>
HARNESS_MATE_BOT_KEY=<bot_key>
HARNESS_MATE_DM_POLICY=open
HARNESS_MATE_ALLOW_ALL_DEVICES=1
EOF`
const pluginRestartCommand = 'hermes gateway restart'
const pluginInstallDocUrl =
  'https://github.com/liaosiliangCodeLife/harness-mate-plat/blob/main/plugin/hermes/INSTALL.md'
const dshSiteUrl = 'https://www.deepseek.com/harness'
const dshGithubUrl = 'https://github.com/deepseek-ai/deepseek-harness'
const dshInstallCommand = 'npm install -g @deepseek-ai/dsh'
const dshNpxCommand = 'npx @deepseek-ai/dsh web'
const dshWebCommand = 'dsh web'
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
    <div class="w-[600px] h-full min-h-screen mx-auto">
      <div
        class="flex flex-col p-6 gap-2 items-center justify-start overflow-scroll scrollbar-w-none h-[calc(100%-100px)] min-h-[calc(100vh-100px)]"
      >
        <div class="w-full min-w-0">
          <div class="text-[32px] font-bold text-[#165DFF] mt-[52px] mb-4">
            {{ t('home.title') }}
          </div>
          <div class="text-xs text-gray-400">Version {{ APP_VERSION }}</div>
          <div class="text-base text-gray-700">
            {{ t('home.intro') }}
          </div>
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
          <a-tabs class="mt-8" default-active-key="hermes">
            <a-tab-pane key="hermes" :title="t('home.hermesTab')">
          <div class="mt-8 min-w-0">
            <div class="mb-3 text-lg font-medium text-gray-900">{{ t('home.installHermes') }}</div>
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
            </div>
          </div>
          <div class="mt-8 min-w-0">
            <div class="mb-3 text-lg font-medium text-gray-900">{{ t('home.installPlugin') }}</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                {{ t('home.hermesIdentity') }}
              </p>
              <p class="mt-4 text-sm leading-6 text-gray-700">
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
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.hermesEnv') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ pluginEnvCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('plugin-env', pluginEnvCommand)"
                >
                  {{ copiedKey === 'plugin-env' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.hermesGateway') }}
              </p>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.hermesVerify') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ pluginRestartCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('plugin-restart', pluginRestartCommand)"
                >
                  {{ copiedKey === 'plugin-restart' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="pluginInstallDocUrl"
                target="_blank"
                rel="noopener noreferrer"
              >{{ t('home.hermesPluginDocs') }}</a>
            </div>
          </div>
            </a-tab-pane>
            <a-tab-pane key="deepseek" :title="t('home.deepseekTab')">
          <div class="mt-8 min-w-0">
            <div class="mb-3 text-lg font-medium text-gray-900">{{ t('home.installDeepseek') }}</div>
            <div class="min-w-0 rounded-lg border border-gray-300 bg-white p-4">
              <p class="text-sm leading-6 text-gray-700">
                {{ t('home.deepseekIntro') }}
              </p>
              <p class="mt-2 text-xs text-gray-500">
                <a
                  class="text-blue-600 hover:underline"
                  :href="dshSiteUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ t('home.officialSite') }}{{ dshSiteUrl }}</a>
                ·
                <a
                  class="text-blue-600 hover:underline"
                  :href="dshGithubUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                >{{ t('home.githubLabel') }}{{ dshGithubUrl }}</a>
              </p>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshInstall') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshInstallCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-install', dshInstallCommand)"
                >
                  {{ copiedKey === 'dsh-install' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshNpx') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshNpxCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-npx', dshNpxCommand)"
                >
                  {{ copiedKey === 'dsh-npx' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshWeb') }}
              </p>
              <div class="mt-2 flex min-w-0 items-start rounded-md bg-gray-100">
                <pre class="m-0 min-w-0 flex-1 overflow-x-auto whitespace-pre-wrap break-all p-3 font-mono text-xs leading-5 text-gray-800">{{ dshWebCommand }}</pre>
                <button
                  type="button"
                  class="m-2 shrink-0 rounded border border-gray-300 bg-white px-2 py-0.5 text-xs text-gray-600 hover:text-gray-900"
                  @click="copyCommand('dsh-web', dshWebCommand)"
                >
                  {{ copiedKey === 'dsh-web' ? t('common.copied') : t('common.copy') }}
                </button>
              </div>
              <p class="mt-4 text-sm leading-6 text-gray-700">
                {{ t('home.dshDesktop') }}
              </p>
              <a
                class="mt-4 inline-block text-xs text-gray-500 hover:text-gray-700"
                :href="dshGithubUrl"
                target="_blank"
                rel="noopener noreferrer"
              >{{ t('home.dshDocs') }}</a>
            </div>
          </div>
          <div class="mt-8 min-w-0">
            <div class="mb-3 text-lg font-medium text-gray-900">{{ t('home.installDshPlugin') }}</div>
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
            </a-tab-pane>
          </a-tabs>
          <div class="mt-8">
            <div class="mb-3 text-lg font-medium text-gray-900">{{ t('home.guide') }}</div>
            <div
              class="flex h-32 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50"
            >
              <span class="text-xs text-gray-400">{{ t('home.comingSoon') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped></style>
