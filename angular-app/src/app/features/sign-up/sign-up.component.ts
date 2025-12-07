import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';

@Component({
  selector: 'app-sign-up',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- Splash Screen -->
    <div *ngIf="showSplash()" 
         class="fixed inset-0 flex items-center justify-center bg-gradient-to-br from-primary to-secondary z-50">
      <div class="text-center space-y-6 animate-bounce-slow">
        <div class="flex items-center justify-center mb-8">
          <div class="w-24 h-24 bg-white rounded-full flex items-center justify-center shadow-2xl">
            <span class="material-icons text-primary text-6xl">receipt_long</span>
          </div>
        </div>
        <h1 class="text-5xl font-bold text-white drop-shadow-lg">Cheapsy</h1>
        <p class="text-xl text-white/90">Find the Best Deals</p>
        <div class="flex items-center justify-center mt-8">
          <span class="loading loading-dots loading-lg text-white"></span>
        </div>
      </div>
    </div>

    <!-- Sign Up Page -->
    <div *ngIf="!showSplash()" 
         class="flex items-center justify-center min-h-screen bg-gradient-to-br from-base-200 to-base-300 animate-fadeIn">
      <!-- Clerk Sign Up Component -->
      <div id="clerk-sign-up"></div>
      
      <!-- Sign In Link -->
      <p class="text-center text-base-content/70 mt-6 absolute bottom-8">
        Already have an account?
        <a href="/sign-in" class="text-primary hover:text-primary-focus font-semibold ml-1">
          Sign in
        </a>
      </p>
    </div>
  `,
  styles: [`
    @keyframes fadeOut {
      from { opacity: 1; }
      to { opacity: 0; }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes bounceSlow {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-20px); }
    }

    .animate-fadeOut {
      animation: fadeOut 0.5s ease-out forwards;
    }

    .animate-fadeIn {
      animation: fadeIn 0.6s ease-out forwards;
    }

    .animate-bounce-slow {
      animation: bounceSlow 2s ease-in-out infinite;
    }
  `]
})
export class SignUpComponent implements OnInit {
  showSplash = signal(true);

  constructor(private authService: ClerkAuthService) {}

  ngOnInit(): void {
    // Show splash screen for 5 seconds before initializing Clerk
    setTimeout(() => {
      this.showSplash.set(false);
      // Wait for DOM to render after hiding splash
      setTimeout(() => {
        this.initializeClerkSignUp();
      }, 100);
    }, 5000);
  }

  private async initializeClerkSignUp(): Promise<void> {
    try {
      const clerk = await this.authService.getClerk();
      if (!clerk) {
        console.error('Clerk instance not available');
        return;
      }

      const element = document.getElementById('clerk-sign-up') as HTMLDivElement;
      if (element) {
        clerk.mountSignUp(element, {
          redirectUrl: '/dashboard'
        });
      }
    } catch (error) {
      console.error('Error initializing Clerk sign-up:', error);
    }
  }
}
