<?php

namespace App\Http\Controllers;

use Illuminate\Contracts\Auth\MustVerifyEmail;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\Redirect;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rules\Password;
use Inertia\Inertia;
use Inertia\Response;

class ProfileController extends Controller
{
    /**
     * Display the user's profile form.
     */
    public function edit(Request $request): Response
    {
        return Inertia::render('Profile/Edit', [
            'mustVerifyEmail' => $request->user() instanceof MustVerifyEmail,
            'status' => session('status'),
        ]);
    }

    /**
     * Update the user's profile information.
     */
    public function update(Request $request): RedirectResponse
    {
        $passwordFilled = $request->filled('password');

        $validationRules = [
            'name' => ['required', 'string', 'max:255'],
            'email' => [
                'required',
                'string',
                'lowercase',
                'email',
                'max:255',
                'unique:users,email,' . $request->user()->id,
            ],
            'settings' => 'array',
            'settings.notifications' => 'array',
            'settings.notifications.*' => 'boolean',
            'photo' => 'nullable|image|max:2048',
        ];
        if ($passwordFilled) {
            $validationRules['current_password'] = ['required', 'current_password'];
            $validationRules['password'] = ['required', Password::defaults()];
        }

        $validated = $request->validate($validationRules);

        if ($passwordFilled) {
            $validated['password'] = Hash::make($validated['password']);
        }
        if ($request->user()->isDirty('email')) {
            $validated['email_verified_at'] = null;
        }
        if ($request->hasFile('photo')) {
            $prevAvatarUrl = DB::table('users')
                ->where('id', $request->user()->id)
                ->value('avatar_url');
            if ($prevAvatarUrl) {
                $prevAvatarUrl = substr($prevAvatarUrl, strlen('/storage/'));
                Storage::disk('public')->delete($prevAvatarUrl);
            }
            $validated['avatar_url'] = '/storage/' . Storage::disk('public')
                ->putFile('user_photos', $request->file('photo'));
        }
        unset($validated['current_password']);
        unset($validated['photo']);

        DB::table('users')
            ->where('id', $request->user()->id)
            ->update($validated);

        return Redirect::route('profile.edit');
    }

    /**
     * Delete the user's account.
     */
    public function destroy(Request $request): RedirectResponse
    {
        $request->validate([
            'password' => ['required', 'current_password'],
        ]);

        $user = $request->user();

        Auth::logout();

        $user->delete();

        $request->session()->invalidate();
        $request->session()->regenerateToken();

        return Redirect::to('/');
    }
}
