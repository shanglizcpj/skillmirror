import { createApp } from "vue"
import { createPinia } from "pinia"

import App from "./App.vue"
import router from "./router"

import { installGlobalErrorHandling } from "./utils/globalErrors"

import "./assets/main.css"


const app = createApp(App)

installGlobalErrorHandling(app)

app.use(createPinia())
app.use(router)

app.mount("#app")