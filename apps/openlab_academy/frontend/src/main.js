import { createApp } from 'vue'
import App from './App.vue'
import { creerRouteur } from './routeur'
import './style.css'

createApp(App).use(creerRouteur()).mount('#espace')
