import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ClerkAuthService } from '../../core/services/clerk-auth.service';

@Component({
  selector: 'app-sign-up',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div class="w-full max-w-md">
        <div class="bg-white rounded-lg shadow-lg p-8">
          <h1 class="text-3xl font-bold text-center text-gray-900 mb-8">Create Account</h1>
          <div id="clerk-sign-up"></div>
          <p class="text-center text-gray-600 mt-6">
            Already have an account?
            <a href="/sign-in" class="text-indigo-600 hover:text-indigo-700 font-semibold">
              Sign in
            </a>
          </p>
        </div>
      </div>
    </div>
  `,
  styles: []
})
export class SignUpComponent implements OnInit {
  constructor(private authService: ClerkAuthService) {}

  ngOnInit(): void {
    // Initialize Clerk sign-up component
    this.initializeClerkSignUp();
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
