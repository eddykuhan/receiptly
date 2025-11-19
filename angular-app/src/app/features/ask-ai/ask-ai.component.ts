import { Component } from '@angular/core';
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
export class AskAiComponent {
  messages: Message[] = [
    {
      text: "Hello! I'm your Cheapsy AI assistant. I can help you analyze your spending, find receipts, and answer questions about your purchases. How can I help you today?",
      isUser: false,
      timestamp: new Date()
    }
  ];

  userInput = '';
  isTyping = false;

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

    // Simulate AI response (replace with actual AI service call)
    setTimeout(() => {
      this.messages.push({
        text: this.getAiResponse(userQuestion),
        isUser: false,
        timestamp: new Date()
      });
      this.isTyping = false;
    }, 1000);
  }

  private getAiResponse(question: string): string {
    // Placeholder responses - integrate with actual AI service
    const lowerQuestion = question.toLowerCase();

    if (lowerQuestion.includes('spending') || lowerQuestion.includes('spent')) {
      return "Based on your receipts, you've spent RM 234.50 this month. Your top categories are groceries (RM 120.30) and dining (RM 89.20).";
    } else if (lowerQuestion.includes('receipt')) {
      return "I found 12 receipts in your history. Would you like me to filter by date, store, or amount?";
    } else if (lowerQuestion.includes('save') || lowerQuestion.includes('budget')) {
      return "To optimize your budget, consider reducing dining expenses. You're spending 38% more than average in this category.";
    } else {
      return "I'm here to help with receipt management, spending analysis, and budget insights. Could you please provide more details about what you'd like to know?";
    }
  }

  handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  }
}
