import { createRouter, createWebHistory } from 'vue-router'
import DetectionView from '../views/DetectionView.vue'
import ReconstructionView from '../views/ReconstructionView.vue'
import Page2 from '../views/Page2.vue'
import Page3 from '../views/Page3.vue'
import Page4 from '../views/Page4.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'detection', component: DetectionView },
    { path: '/reconstruction', name: 'reconstruction', component: ReconstructionView },
    { path: '/page2', name: 'page2', component: Page2 },
    { path: '/page3', name: 'page3', component: Page3 },
    { path: '/page4', name: 'page4', component: Page4 },
  ],
})
