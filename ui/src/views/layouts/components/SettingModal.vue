<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAccountStore } from '@/stores/account'
import {
  useGetCurrentUser,
  useUpdateAvatar,
  useUpdateName,
  useUpdatePassword,
} from '@/hooks/use-account'
import { useUploadImage } from '@/hooks/use-upload-file'
import { setLocale, t, type AppLocale } from '@/locales'

// 1.定义自定义组件所需数据
const props = defineProps({
  visible: { type: Boolean, required: true },
})
const emits = defineEmits(['update:visible'])
const updateName = ref(false)
const updatePassword = ref(false)
const section = ref<'account' | 'language'>('account')
const { locale } = useI18n()
const accountStore = useAccountStore()
const { current_user, loadCurrentUser } = useGetCurrentUser()
const { handleUpdateAvatar } = useUpdateAvatar()
const { handleUpdateName } = useUpdateName()
const { handleUpdatePassword } = useUpdatePassword()
const { image_url, handleUploadImage } = useUploadImage()
const accountForm = ref({
  fileList: [{ uid: '1', name: t('layout.avatar'), url: accountStore.account.avatar }],
  name: accountStore.account.name,
  avatar: accountStore.account.avatar,
  password: '',
  email: accountStore.account.email,
})

// 2.更新当前账号信息
const updateAccount = async () => {
  await loadCurrentUser()
  accountStore.update(current_user.value)
}

// 3.关闭模态窗处理器
const handleCancel = () => emits('update:visible', false)

// 4.监听模态窗关闭事件
watch(
  () => props.visible,
  (newValue) => {
    if (!newValue) {
      // 如果为关闭模态窗则重置表单，并关闭所有输入框
      updatePassword.value = false
      updateName.value = false
      section.value = 'account'
    }

    // 无论是开启还是关闭模态窗，均赋初始值，可以确保首次加载的时候数据正确展示
    accountForm.value = {
      fileList: [{ uid: '1', name: t('layout.avatar'), url: accountStore.account.avatar }],
      name: accountStore.account.name,
      avatar: accountStore.account.avatar,
      password: '',
      email: accountStore.account.email,
    }
  },
)

watch(locale, () => {
  accountForm.value.fileList = accountForm.value.fileList.map((file) => ({
    ...file,
    name: t('layout.avatar'),
  }))
})

const navClass = (key: 'account' | 'language') => {
  const active = section.value === key
  return [
    'cursor-pointer rounded-lg h-8 leading-8 px-4',
    active
      ? 'bg-gray-100 text-gray-900'
      : 'text-gray-700 hover:bg-gray-200 hover:text-gray-900',
  ]
}

const changeLocale = (value: string | number | boolean) => {
  if (value === 'zh-CN' || value === 'en-US') {
    setLocale(value as AppLocale)
  }
}
</script>

<template>
  <a-modal :visible="visible" hide-title :footer="false" :width="1000" @cancel="handleCancel">
    <!-- 关闭按钮 -->
    <a-button
      type="text"
      class="!text-gray-700 absolute right-5 top-5"
      size="small"
      @click="handleCancel"
    >
      <template #icon>
        <icon-close />
      </template>
    </a-button>
    <!-- 内容容器 -->
    <div class="flex min-h-[500px]">
      <!-- 左侧导航 -->
      <div class="w-[200px] border-r pr-5">
        <!-- 导航版标题 -->
        <div class="text-xl font-bold text-gray-900 mb-5">{{ t('layout.settings') }}</div>
        <!-- 导航列表 -->
        <div class="flex flex-col gap-2">
          <div :class="navClass('account')" @click="section = 'account'">
            {{ t('layout.accountSettings') }}
          </div>
          <div :class="navClass('language')" @click="section = 'language'">
            {{ t('layout.language') }}
          </div>
        </div>
      </div>
      <!-- 右侧内容 -->
      <div v-if="section === 'language'" class="flex-1 px-8">
        <div class="text-xl font-bold text-gray-700 mb-5">{{ t('layout.language') }}</div>
        <p class="mb-4 text-sm text-gray-500">{{ t('layout.languageHint') }}</p>
        <a-radio-group direction="vertical" :model-value="locale" @change="changeLocale">
          <a-radio value="zh-CN">{{ t('layout.chinese') }}</a-radio>
          <a-radio value="en-US">{{ t('layout.english') }}</a-radio>
        </a-radio-group>
      </div>
      <div v-else class="flex-1 px-8">
        <!-- 右侧标题 -->
        <div class="text-xl font-bold text-gray-700 mb-5">{{ t('layout.accountSettings') }}</div>
        <!-- 账号表单 -->
        <a-form :model="{}" layout="vertical">
          <a-form-item field="avatar">
            <template #label>
              <div class="flex items-center gap-1">
                {{ t('layout.avatar') }}
                <div class="text-red-700">*</div>
              </div>
            </template>
            <a-upload
              v-model:file-list="accountForm.fileList"
              list-type="picture-card"
              :limit="1"
              image-preview
              :custom-request="
                (option) => {
                  const uploadTask = async () => {
                    // 1.提取数据并发起请求获取响应内容
                    const { fileItem, onSuccess } = option
                    await handleUploadImage(fileItem.file as File)
                    accountForm.avatar = image_url
                    onSuccess(image_url)

                    // 2.更新账号头像
                    await handleUpdateAvatar(String(accountForm.avatar))

                    // 3.更新账号信息
                    await updateAccount()
                  }

                  uploadTask()

                  return {}
                }
              "
            />
          </a-form-item>
          <a-form-item field="name">
            <template #label>
              <div class="flex items-center gap-1">
                {{ t('layout.nickname') }}
                <div class="text-red-700">*</div>
              </div>
            </template>
            <div v-if="updateName" class="flex items-center gap-2 w-full">
              <!-- 左侧输入框 -->
              <a-input
                v-model="accountForm.name"
                :placeholder="t('layout.nicknamePlaceholder')"
                :default-value="accountStore.account.name"
              />
              <!-- 取消&保存 -->
              <div class="flex items-center gap-1">
                <a-button
                  class="rounded-lg"
                  @click="
                    () => {
                      updateName = false
                      accountForm.name = accountStore.account.name
                    }
                  "
                >
                  {{ t('common.cancel') }}
                </a-button>
                <a-button
                  type="primary"
                  class="rounded-lg"
                  @click="
                    async () => {
                      // 发起请求更新账号名称
                      await handleUpdateName(accountForm.name)

                      // 成功更新则重新获取账号数据并隐藏输入框
                      await updateAccount()
                      updateName = false
                    }
                  "
                >
                  {{ t('common.save') }}
                </a-button>
              </div>
            </div>
            <div v-else class="flex items-center gap-1">
              <div class="">{{ accountStore.account.name }}</div>
              <a-button size="mini" type="text" class="!text-gray-700" @click="updateName = true">
                <template #icon>
                  <icon-edit />
                </template>
              </a-button>
            </div>
          </a-form-item>
          <a-form-item field="password">
            <template #label>
              <div class="flex items-center gap-1">
                {{ t('layout.password') }}
                <div class="text-red-700">*</div>
              </div>
            </template>
            <div v-if="updatePassword" class="flex items-center gap-2 w-full">
              <!-- 左侧输入框 -->
              <a-input-password v-model="accountForm.password" :placeholder="t('layout.passwordPlaceholder')" />
              <!-- 取消&保存 -->
              <div class="flex items-center gap-1">
                <a-button
                  class="rounded-lg"
                  @click="
                    () => {
                      updatePassword = false
                      accountForm.password = ''
                    }
                  "
                >
                  {{ t('common.cancel') }}
                </a-button>
                <a-button
                  type="primary"
                  class="rounded-lg"
                  @click="
                    async () => {
                      // 发起请求更新账号密码
                      await handleUpdatePassword(accountForm.password)

                      // 隐藏输入框并将输入框值清空
                      accountForm.password = ''
                      updatePassword = false
                    }
                  "
                >
                  {{ t('common.save') }}
                </a-button>
              </div>
            </div>
            <div v-else class="flex items-center gap-1">
              <div class="">******</div>
              <a-button
                size="mini"
                type="text"
                class="!text-gray-700"
                @click="updatePassword = true"
              >
                <template #icon>
                  <icon-edit />
                </template>
              </a-button>
            </div>
          </a-form-item>
          <a-form-item field="email" :label="t('layout.boundEmail')">
            <a-input readonly v-model="accountForm.email" />
          </a-form-item>
        </a-form>
      </div>
    </div>
  </a-modal>
</template>

<style scoped></style>
