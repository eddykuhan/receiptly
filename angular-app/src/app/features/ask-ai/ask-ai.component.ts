import { Component, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

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

    // Simulate AI response (replace with actual AI service call)
    setTimeout(() => {
      this.messages.push({
        text: this.getAiResponse(userQuestion),
        isUser: false,
        timestamp: new Date()
      });
      this.isTyping = false;
      this.shouldScroll = true;
    }, 1000);
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

  private getAiResponse(question: string): string {
    // Mock AI responses based on keywords
    const q = question.toLowerCase();

    if (q.includes('spend') || q.includes('spent')) {
      return "Based on your receipts, you've spent RM 1,245.50 this month across 23 transactions. Your top categories are groceries (RM 680), dining (RM 320), and household items (RM 245).";
    } else if (q.includes('cheapest') || q.includes('price')) {
      return "Looking at your receipt history, Mydin USJ typically has the lowest prices for groceries. For milk specifically, they're about 15% cheaper than other stores in your area.";
    } else if (q.includes('recent') || q.includes('last')) {
      return "Your 5 most recent receipts are: 1) Tesco Ampang (RM 85.20, today), 2) Giant Wangsa Maju (RM 42.50, yesterday), 3) Aeon Mid Valley (RM 156.80, 2 days ago), 4) Mydin USJ (RM 38.90, 3 days ago), 5) Lotus Cheras (RM 67.30, 4 days ago).";
    } else if (q.includes('save') || q.includes('saving')) {
      return "Great question! By using the Price Map feature, you could save approximately RM 120/month by shopping at the cheapest stores for your regular items. I recommend buying milk and bread at Mydin, and fresh produce at Giant.";
    } else if (q.includes('receipt') && q.includes('how many')) {
      return "You've uploaded 125 receipts so far! You're doing great - just 25 more to unlock your Touch 'n Go voucher reward. Keep it up! 🎉";
    } else {
      return "I understand you're asking about: '" + question + "'. While I'm a demo AI, in production I would analyze your receipt data to provide personalized insights. Try asking about your spending, price comparisons, or recent purchases!";
    }
  }
}
