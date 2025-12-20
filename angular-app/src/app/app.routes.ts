import { Routes } from '@angular/router';
import { AuthGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full'
  },
  {
    path: 'sign-in',
    loadComponent: () => import('./features/sign-in/sign-in.component').then(m => m.SignInComponent)
  },
  {
    path: 'sign-up',
    loadComponent: () => import('./features/sign-up/sign-up.component').then(m => m.SignUpComponent)
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'history',
    loadComponent: () => import('./features/history/history.component').then(m => m.HistoryComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'ask-ai',
    loadComponent: () => import('./features/ask-ai/ask-ai.component').then(m => m.AskAiComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'price-map',
    loadComponent: () => import('./features/price-map/price-map.component').then(m => m.PriceMapComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'rewards',
    loadComponent: () => import('./features/rewards/rewards.component').then(m => m.RewardsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'profile',
    loadComponent: () => import('./features/profile/profile.component').then(m => m.ProfileComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'purchased-items',
    loadComponent: () => import('./features/purchased-items/purchased-items.component').then(m => m.PurchasedItemsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'camera',
    loadComponent: () => import('./features/camera/camera.component').then(m => m.CameraComponent),
    canActivate: [AuthGuard]
  },
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];

