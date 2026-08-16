<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from 'vue'

import * as monaco from 'monaco-editor'

import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

self.MonacoEnvironment = {
  getWorker() {
    return new editorWorker()
  }
}

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },

  language: {
    type: String,
    default: 'python'
  },

  readOnly: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:modelValue',
  'change',
  'run',
  'submit'
])

const editorContainer = ref(null)

let editorInstance = null
let changeListener = null
let resizeObserver = null

onMounted(async () => {
  await nextTick()

  editorInstance = monaco.editor.create(
    editorContainer.value,
    {
      value: props.modelValue,
      language: props.language,
      theme: 'vs-dark',
      readOnly: props.readOnly,

      automaticLayout: true,
      fontSize: 14,
      lineHeight: 23,
      fontFamily:
        'Consolas, "Cascadia Code", "Courier New", monospace',

      lineNumbers: 'on',
      lineNumbersMinChars: 3,
      minimap: {
        enabled: false
      },

      scrollBeyondLastLine: false,
      wordWrap: 'on',
      tabSize: 4,
      insertSpaces: true,

      automaticClosingBrackets: 'always',
      automaticClosingQuotes: 'always',

      renderLineHighlight: 'all',
      cursorBlinking: 'smooth',
      cursorSmoothCaretAnimation: 'on',
      smoothScrolling: true,

      padding: {
        top: 18,
        bottom: 18
      },

      suggestOnTriggerCharacters: true,
      quickSuggestions: true,
      folding: true,
      glyphMargin: false,
      roundedSelection: true
    }
  )

  changeListener =
    editorInstance.onDidChangeModelContent(() => {
      const value = editorInstance.getValue()

      emit('update:modelValue', value)
      emit('change', value)
    })

  editorInstance.addCommand(
    monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter,
    () => {
      emit('run')
    }
  )

  editorInstance.addCommand(
    monaco.KeyMod.CtrlCmd |
      monaco.KeyMod.Shift |
      monaco.KeyCode.Enter,
    () => {
      emit('submit')
    }
  )

  resizeObserver = new ResizeObserver(() => {
    editorInstance?.layout()
  })

  resizeObserver.observe(editorContainer.value)
})

watch(
  () => props.modelValue,
  (newValue) => {
    if (
      editorInstance &&
      editorInstance.getValue() !== newValue
    ) {
      editorInstance.setValue(newValue)
    }
  }
)

watch(
  () => props.readOnly,
  (newValue) => {
    editorInstance?.updateOptions({
      readOnly: newValue
    })
  }
)

onBeforeUnmount(() => {
  changeListener?.dispose()
  resizeObserver?.disconnect()
  editorInstance?.dispose()
})
</script>

<template>
  <div
    ref="editorContainer"
    class="monaco-code-editor"
  ></div>
</template>

<style scoped>
.monaco-code-editor {
  width: 100%;
  height: 100%;
  min-height: 430px;
  overflow: hidden;
}
</style>