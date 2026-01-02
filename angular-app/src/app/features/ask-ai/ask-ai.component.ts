import { Component, ViewChild, ElementRef, AfterViewChecked, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService } from '../../core/services/chat.service';

interface Message {
  text: string;
  isUser: boolean;
  timestamp: Date;
}

@Component({
  selector: 'app-ask-ai',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule
  ],
  templateUrl: './ask-ai.component.html',
  styleUrl: './ask-ai.component.scss'
})
export class AskAiComponent implements AfterViewChecked {
  @ViewChild('chatContainer') private chatContainer?: ElementRef;

  private readonly chatService = inject(ChatService);
  private readonly cdr = inject(ChangeDetectorRef);

  messages: Message[] = [];
  userInput = '';
  isTyping = false;
  private shouldScroll = false;

  ngAfterViewChecked() {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  sendMessage() {
    if (!this.userInput.trim()) return;

    // Add user message
    this.messages.push({
      text: this.userInput,
      isUser: true,
      timestamp: new Date()
    });

    const userQuestion = this.userInput;
    this.userInput = '';
    this.isTyping = true;
    this.shouldScroll = true;

    // Call real AI service
    this.chatService.askQuestion(userQuestion).subscribe({
      next: (response) => {
        console.log('Received response:', response);
        console.log('Messages before push:', this.messages.length);
        console.log('isTyping before:', this.isTyping);
        
        this.messages.push({
          text: response.answer,
          isUser: false,
          timestamp: new Date(response.timestamp)
        });
        this.isTyping = false;
        this.shouldScroll = true;
        
        console.log('Messages after push:', this.messages.length);
        console.log('isTyping after:', this.isTyping);
        console.log('Last message:', this.messages[this.messages.length - 1]);
        
        // Force change detection
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Chat error:', error);
        this.messages.push({
          text: error.message || 'Sorry, I encountered an error. Please try again.',
          isUser: false,
          timestamp: new Date()
        });
        this.isTyping = false;
        this.shouldScroll = true;
        this.cdr.detectChanges();
      }
    });
  }

  clearChat() {
    this.messages = [];
    this.userInput = '';
    this.isTyping = false;
  }

  private scrollToBottom() {
    try {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop = this.chatContainer.nativeElement.scrollHeight;
      }
    } catch (err) {
      console.error('Scroll error:', err);
    }
  }

  handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      this.sendMessage();
    }
  }

  quickQuestion(question: string) {
    this.userInput = question;
    this.sendMessage();
  }
}
