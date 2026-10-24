@extends('layouts.app')
@section('title', 'Ingresar')

@section('content')
    <div class="mx-auto mt-10 max-w-sm rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 class="text-xl font-semibold text-marca-950">Ingresar al panel</h1>
        <p class="mt-1 text-sm text-slate-500">Administra qué recibe cada suscriptor.</p>
        <form method="POST" action="{{ url('/login') }}" class="mt-5 space-y-4">
            @csrf
            <div>
                <label for="email" class="mb-1 block text-sm font-medium">Correo</label>
                <input id="email" name="email" type="email" value="{{ old('email') }}" required autofocus autocomplete="username"
                       class="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100">
                @error('email') <p class="mt-1 text-sm text-red-700">{{ $message }}</p> @enderror
            </div>
            <div>
                <label for="password" class="mb-1 block text-sm font-medium">Contraseña</label>
                <input id="password" name="password" type="password" required autocomplete="current-password"
                       class="w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm focus:border-marca-600 focus:outline-none focus:ring-4 focus:ring-marca-100">
            </div>
            <label class="flex items-center gap-2 text-sm text-slate-600"><input type="checkbox" name="remember" class="rounded"> Mantener la sesión</label>
            <button class="w-full rounded-xl bg-marca-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-marca-800">Ingresar</button>
        </form>
    </div>
@endsection
