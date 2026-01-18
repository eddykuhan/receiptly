import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';
import { LocationService } from '../../core/services/location.service';

@Component({
  selector: 'app-sign-in',
  standalone: true,
  imports: [CommonModule],
  template: `
    <!-- Splash Screen -->
    <div *ngIf="showSplash()" 
         class="fixed inset-0 flex items-center justify-center bg-gradient-to-br from-primary to-secondary z-50">
      <div class="text-center space-y-6 animate-bounce-slow">
        <div class="flex items-center justify-center mb-8">
          <div class="w-24 h-24 bg-white rounded-full flex items-center justify-center shadow-2xl">
            <span class="material-icons text-primary text-6xl">location_on</span>
          </div>
        </div>
        <h1 class="text-5xl font-bold text-white drop-shadow-lg">cheap-sy</h1>
        <p class="text-xl text-white/90">Find the Best Deals</p>
        
        <!-- Location Request Button for iOS -->
        <div *ngIf="showLocationButton()" class="mt-8 px-4">
          <button 
            (click)="requestLocationPermission()"
            [disabled]="locationService.isLoading()"
            class="btn btn-lg bg-white text-primary hover:bg-white/90 border-none shadow-xl">
            <span class="material-icons mr-2">my_location</span>
            {{ locationService.isLoading() ? 'Getting Location...' : 'Enable Location' }}
          </button>
          <p class="text-sm text-white/80 mt-4 max-w-xs mx-auto">
            Enable location to find the best deals near you
          </p>
          <p *ngIf="locationService.error()" class="text-sm text-error bg-white/20 p-2 rounded mt-2">
            {{ locationService.error() }}
          </p>
        </div>
        
        <!-- Loading indicator -->
        <div *ngIf="!showLocationButton() || locationService.isLoading()" class="flex items-center justify-center mt-8">
          <span class="loading loading-dots loading-lg text-white"></span>
        </div>
      </div>
    </div>

    <!-- Sign In Page -->
    <div *ngIf="!showSplash()" 
         class="flex items-center justify-center min-h-screen bg-gradient-to-br from-base-200 to-base-300 animate-fadeIn">
      <!-- Clerk Sign In Component -->
      <div id="clerk-sign-in"></div>
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
export class SignInComponent implements OnInit {
  showSplash = signal(true);
  showLocationButton = signal(false);
  redirectUrl = '/dashboard';

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private authService: ClerkAuthService,
    public locationService: LocationService
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      if (params['returnUrl']) {
        this.redirectUrl = params['returnUrl'];
      }
    });

    // Check if we need to show location button (for iOS or if permission not requested)
    // Show button after 1 second to let splash screen display
    setTimeout(() => {
      if (this.isIOS() && !this.locationService.wasPermissionRequested()) {
        this.showLocationButton.set(true);
      } else {
        // For non-iOS, request automatically
        this.requestLocationPermission();
      }
    }, 1000);

    // Show splash screen for 5 seconds before initializing Clerk
    setTimeout(() => {
      this.showSplash.set(false);
      // Wait for DOM to render after hiding splash
      setTimeout(() => {
        this.initializeClerkSignIn();
      }, 100);
    }, 5000);
  }

  /**
   * Detect if running on iOS
   */
  private isIOS(): boolean {
    return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
           (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  }

  /**
   * Request location permission - MUST be called from user interaction on iOS
   */
  async requestLocationPermission(): Promise<void> {
    this.showLocationButton.set(false);
    await this.locationService.requestLocation();
  }

  private async initializeClerkSignIn(): Promise<void> {
    try {
      const clerk = await this.authService.getClerk();
      if (!clerk) {
        console.error('Clerk instance not available');
        return;
      }

      // If user is already signed in, redirect to dashboard
      if (clerk.user && clerk.session) {
        console.log('User already signed in, redirecting to dashboard');
        this.router.navigate([this.redirectUrl]);
        return;
      }

      const element = document.getElementById('clerk-sign-in') as HTMLDivElement;
      if (element) {
        clerk.mountSignIn(element, {
          redirectUrl: this.redirectUrl
        });
      }
    } catch (error) {
      console.error('Error initializing Clerk sign-in:', error);
    }
  }
}
