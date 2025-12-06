import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';

@Component({
  selector: 'app-sign-in',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div class="w-full max-w-md">
        <div class="bg-white rounded-lg shadow-lg p-8">
          <h1 class="text-3xl font-bold text-center text-gray-900 mb-8">Sign In</h1>
          <div id="clerk-sign-in"></div>
          <p class="text-center text-gray-600 mt-6">
            Don't have an account?
            <a href="/sign-up" class="text-indigo-600 hover:text-indigo-700 font-semibold">
              Sign up
            </a>
          </p>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class SignInComponent implements OnInit {
  redirectUrl = '/dashboard';

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private authService: ClerkAuthService
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      if (params['returnUrl']) {
        this.redirectUrl = params['returnUrl'];
      }
    });

    // Initialize Clerk sign-in component
    this.initializeClerkSignIn();
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
