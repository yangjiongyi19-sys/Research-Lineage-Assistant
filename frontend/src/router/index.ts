import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/researches',
      name: 'research-list',
      component: () => import('../views/ResearchListView.vue')
    },
    {
      path: '/research/:id',
      name: 'research-detail',
      component: () => import('../views/ResearchDetailView.vue')
    },
    {
      path: '/report/:id',
      name: 'report',
      component: () => import('../views/ReportView.vue')
    },
    {
      path: '/wiki',
      name: 'wiki',
      component: () => import('../views/WikiView.vue')
    }
  ]
})

export default router
