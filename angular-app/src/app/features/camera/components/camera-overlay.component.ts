import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-camera-overlay',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="absolute inset-0 pointer-events-none z-10 flex flex-col items-center justify-center">
      <!-- Dark overlay with transparent center -->
      <div class="absolute inset-0 bg-black/50 mask-image"></div>
      
      <!-- Guide Rectangle -->
      <div class="relative w-[85%] aspect-[3/5] max-w-md border-2 border-white/80 rounded-lg shadow-[0_0_0_9999px_rgba(0,0,0,0.5)]">
        <!-- Corner Markers -->
        <div class="absolute -top-1 -left-1 w-8 h-8 border-t-4 border-l-4 border-sky-400 rounded-tl-lg shadow-sm"></div>
        <div class="absolute -top-1 -right-1 w-8 h-8 border-t-4 border-r-4 border-sky-400 rounded-tr-lg shadow-sm"></div>
        <div class="absolute -bottom-1 -left-1 w-8 h-8 border-b-4 border-l-4 border-sky-400 rounded-bl-lg shadow-sm"></div>
        <div class="absolute -bottom-1 -right-1 w-8 h-8 border-b-4 border-r-4 border-sky-400 rounded-br-lg shadow-sm"></div>

        <!-- Center Line (for alignment) -->
        <div class="absolute top-1/2 left-0 w-full h-px bg-sky-400/30 transform -translate-y-1/2"></div>
        
        <!-- Scanning Animation -->
        @if (isScanning) {
          <div class="absolute top-0 left-0 w-full h-1 bg-sky-400/80 shadow-[0_0_15px_rgba(56,189,248,0.8)] animate-scan"></div>
        }
      </div>

      <!-- Instructions -->
      <div class="absolute bottom-32 left-0 w-full text-center px-4 pointer-events-auto">
        <div class="inline-block bg-black/60 backdrop-blur-md text-white px-4 py-2 rounded-full text-sm font-medium mb-4">
          {{ instructionText }}
        </div>
      </div>

      <!-- Controls (passed through from parent) -->
      <div class="absolute bottom-8 left-0 w-full flex justify-center items-center gap-8 pointer-events-auto">
        <ng-content></ng-content>
      </div>
    </div>
  `,
  styles: [`
    .animate-scan {
      animation: scan 2s linear infinite;
    }
    @keyframes scan {
      0% { top: 0%; opacity: 0; }
      10% { opacity: 1; }
      90% { opacity: 1; }
      100% { top: 100%; opacity: 0; }
    }
  `]
})
export class CameraOverlayComponent {
  @Input() isScanning = false;
  @Input() instructionText = 'Align receipt within the frame';
}
