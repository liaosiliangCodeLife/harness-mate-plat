import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/github-dark.css'
import 'github-markdown-css'

// 代码块走 highlight.js，风格与现有代码高亮一致
const highlightCode = (code: string, language: string): string => {
  try {
    const languageName = language && hljs.getLanguage(language) ? language : ''
    const highlighted = languageName
      ? hljs.highlight(code, { language: languageName }).value
      : hljs.highlightAuto(code).value
    const className = languageName ? `hljs language-${languageName}` : 'hljs'
    return `<pre class="hljs"><code class="${className}">${highlighted}</code></pre>`
  } catch {
    return ''
  }
}

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: highlightCode,
})

// 把消息正文渲染成 markdown HTML
export const renderMarkdown = (content: string): string => {
  return markdown.render(content || '')
}
