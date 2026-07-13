import { createRouter, createWebHistory } from 'vue-router'
import OverviewView from '../views/OverviewView.vue'

const router = createRouter({
  history: createWebHistory('/app'),
  routes: [
    {
      path: '/',
      redirect: '/overview'
    },
    {
      path: '/overview',
      name: 'overview',
      component: OverviewView
    }
  ]
})

export default router
