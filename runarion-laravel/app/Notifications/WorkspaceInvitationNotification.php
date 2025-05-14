<?php

namespace App\Notifications;

use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Notifications\Messages\MailMessage;
use Illuminate\Notifications\Notification;
use Illuminate\Bus\Queueable;

class WorkspaceInvitationNotification extends Notification 
    // implements ShouldQueue
{
    // use Queueable;

    /**
     * Create a new notification instance.
     */
    public function __construct(
        protected string $workspaceName,
        protected string $acceptUrl,
        protected string $role,
        protected bool $userExists
    ) {}

    /**
     * Get the notification's channels.
     */
    public function via(mixed $notifiable): array|string
    {
        return ['mail'];
    }

    /**
     * Build the mail representation of the notification.
     */
    public function toMail(mixed $notifiable): MailMessage
    {
        $roleText = $this->role === 'admin' ? 'an admin' : 'a member';
        
        return (new MailMessage)
            ->subject("Invitation to {$this->workspaceName} workspace")
            ->line("You've been invited to be {$roleText} of the {$this->workspaceName} workspace.")
            ->lineIf(!$this->userExists, 'Since you are not registered, PLEASE REGISTER first before accepting the invitation.')
            ->action('Accept Invitation', $this->acceptUrl)
            ->line('If you did not expect to receive this invitation, you can safely ignore this email.');
    }
}
