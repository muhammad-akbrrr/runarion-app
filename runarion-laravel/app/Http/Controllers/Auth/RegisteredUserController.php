<?php

namespace App\Http\Controllers\Auth;

use App\Http\Controllers\Controller;
use App\Models\User;
use App\Models\Workspace;
use App\Models\WorkspaceMember;
use Illuminate\Auth\Events\Registered;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;
use Illuminate\Validation\Rules;
use Inertia\Inertia;
use Inertia\Response;

class RegisteredUserController extends Controller
{
    /**
     * Display the registration view.
     */
    public function create(): Response
    {
        return Inertia::render('Auth/Register');
    }

    /**
     * Handle an incoming registration request.
     *
     * @throws \Illuminate\Validation\ValidationException
     */
    public function store(Request $request): RedirectResponse
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|string|lowercase|email|max:255|unique:'.User::class,
            'password' => ['required', 'confirmed', Rules\Password::defaults()],
        ]);
        $name = $request->name;
        $avatarUrl = 'https://ui-avatars.com/api/?' . http_build_query([
            'name' => $name,
            'background' => 'random',
        ]);

        $user = User::create([
            'name' => $name,
            'email' => $request->email,
            'password' => Hash::make($request->password),
            'avatar_url' => $avatarUrl,
        ]);

        event(new Registered($user));

        Auth::login($user);

        $workspaceName = explode(' ', $user->name)[0] . "'s Workspace";
        $workspaceSlug = Str::slug($workspaceName);
        $imageUrl = 'https://ui-avatars.com/api/?' . http_build_query([
            'name' => $workspaceName,
            'background' => 'random',
        ]);
        $workspace = Workspace::create([
            'name' => $workspaceName,
            'slug' => $workspaceSlug,
            'cover_image_url' => $imageUrl,
        ]);

        WorkspaceMember::create([
            'workspace_id' => $workspace->id,
            'user_id' => $user->id,
            'role' => 'owner',
        ]);

        return redirect(route('dashboard', absolute: false));
    }
}
